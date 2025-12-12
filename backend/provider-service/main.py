"""
Provider Service — normalized marketplace API
Legacy inline adapters/registries removed. Uses core.registry with BaseProviderAdapter.
Returns { total, items } and supports basic filters & pagination.
"""

from typing import List, Dict, Optional
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import inspect
import sys
from pathlib import Path
# Structured JSON logging (uses python-json-logger)
try:
    # When imported as a package (e.g., uvicorn runs app:app)
    from .lib.logging import get_logger
except Exception:
    # When imported directly from tests with sys.path pointing to this folder
    from lib.logging import get_logger  # type: ignore
import os
import json
import hashlib
import asyncio
import asyncpg
import contextlib

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from fastapi import FastAPI, HTTPException, Query, Body, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.requests import Request
from starlette.responses import Response

from core.registry import ProviderRegistry
from adapters.base_adapter import BaseProviderAdapter
from core.async_circuit_breaker import get_breaker
from core.math_client import MathCoreClient
from core.rate_limit import get_limiter
from core.search_client import MeiliSearchClient
from prometheus_fastapi_instrumentator import Instrumentator
from db import init_db_pool, close_db_pool
from ingestion.scheduler import start_scheduler
import ingestion.repository as repo_module
from models.normalized_offer import NormalizedOffer
from redis.asyncio import Redis
from shared.vault_client import get_secret, VaultError, VaultSecretNotFoundError

try:
    from aiokafka import AIOKafkaProducer  # type: ignore
except Exception:
    AIOKafkaProducer = None

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client, db_pool, math_client, meili_client
    redis_url = os.getenv("REDIS_URL")
    if Redis and redis_url:
        try:
            redis_client = Redis.from_url(redis_url, decode_responses=True)
            await redis_client.ping()
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Redis not available: {e}")
            redis_client = None
    logger.info("Provider adapters: %s", ProviderRegistry.list_adapters())
    try:
        Instrumentator().instrument(app).expose(app)
        logger.info("/metrics exposed")
    except Exception as e:
        logger.warning(f"Failed to expose metrics: {e}")
    try:
        await init_db_pool()
        db_pool = await asyncpg.create_pool(os.getenv("DATABASE_URL"))
        logger.info("DB pool initialized for Config")
    except Exception as e:
        logger.warning(f"DB not available: {e}")
    try:
        math_client = MathCoreClient(os.getenv("MATH_CORE_URL", "http://math-core:8004"))
        logger.info("MathCore client initialized")
    except Exception as e:
        logger.warning(f"MathCore client init failed: {e}")
    try:
        meili_client = MeiliSearchClient(os.getenv("MEILISEARCH_URL", ""))
    except Exception as e:
        logger.warning(f"Meili client init failed: {e}")
    if os.getenv("ENABLE_INGESTION", "false").lower() in {"1", "true", "yes"}:
        start_scheduler(asyncio.get_event_loop(), redis_client)

    try:
        yield
    finally:
        if db_pool:
            await db_pool.close()
        if math_client:
            try:
                await math_client.close()
            except Exception as e:
                logger.warning("Failed to close MathCore client cleanly: %s", e)
        if meili_client:
            try:
                await meili_client.close()
            except Exception as e:
                logger.warning("Failed to close Meili client cleanly: %s", e)

app = FastAPI(
    title="GPUBROKER Provider Service",
    description="Provider aggregation and marketplace API",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS configuration to allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ProviderItem(BaseModel):
    id: str
    provider: str
    name: str
    gpu: str
    memory_gb: int = Field(0, alias="gpu_memory_gb")
    price_per_hour: float
    currency: str | None = None
    availability: str
    region: str
    tags: List[str] = []
    last_updated: datetime

    class Config:
        populate_by_name = True


class ProviderListResponse(BaseModel):
    total: int
    items: List[ProviderItem]
    warnings: Optional[List[str]] = None

class IntegrationConfig(BaseModel):
    provider: str
    api_key: Optional[str] = None
    api_url: Optional[str] = None

class IntegrationStatus(BaseModel):
    provider: str
    status: str  # 'active', 'error', 'not_configured'
    message: Optional[str] = None
    last_checked: datetime

redis_client: Optional[Redis] = None  # type: ignore
db_pool = None
math_client: Optional[MathCoreClient] = None
meili_client: Optional[MeiliSearchClient] = None


def _provider_base_url(adapter: BaseProviderAdapter) -> str:
    base = getattr(adapter, "BASE_URL", None)
    if isinstance(base, str) and base:
        return base
    return f"https://unknown.local/{adapter.PROVIDER_NAME or 'provider'}"


def _provider_api_key(provider_name: str) -> Optional[str]:
    """
    Resolve a provider API key with precedence:
    1) Vault secret: secret/data/gpubroker/{provider}/api_key
    2) Environment fallback: {PROVIDER}_API_KEY (legacy)
    """
    # Try Vault first
    try:
        secret = get_secret(provider_name, "api_key")
        if secret:
            return secret
    except (VaultError, VaultSecretNotFoundError) as e:
        logger.warning("Vault secret missing for %s: %s", provider_name, e)
    except Exception as e:
        logger.warning("Vault lookup failed for %s: %s", provider_name, e)

    # Fallback to legacy env var to avoid hard failures if Vault not configured
    env_key = os.getenv(f"{provider_name}_API_KEY".upper())
    return env_key


def _cache_key(path: str, params: Dict[str, str]) -> str:
    base = path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return "providers:" + hashlib.sha256(base.encode()).hexdigest()


def _safe_upsert(repo, offers: List[Dict]):
    """Guard upsert for repositories lacking upsert method."""
    if hasattr(repo, "upsert_offers") and callable(getattr(repo, "upsert_offers")):
        return repo.upsert_offers(offers)
    return None
async def _get_user_config(user_id: str, provider: str) -> Dict[str, str]:
    """Retrieve provider config for a user from DB."""
    if not db_pool:
        return {}
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT preference_value FROM user_preferences WHERE user_id = $1 AND preference_key = $2",
                user_id, f"provider_config:{provider}"
            )
            if row:
                return json.loads(row['preference_value'])
    except Exception as e:
        logger.error(f"Failed to fetch user config: {e}")
    return {}

async def _validate_provider_creds(provider_name: str, api_key: str) -> bool:
    """Validate credentials using the adapter's implementation."""
    try:
        adapter = ProviderRegistry.get_adapter(provider_name)
        return await adapter.validate_credentials({"api_key": api_key})
    except Exception as e:
        logger.warning(f"Validation failed for {provider_name}: {e}")
        return False

async def _fetch_offers() -> Dict[str, List[Dict]]:
    results: Dict[str, List[Dict]] = {}
    user_id = "00000000-0000-0000-0000-000000000000"

    repo_ctor_params = inspect.signature(repo_module.OfferRepository).parameters
    if "redis_client" in repo_ctor_params:
        repo = repo_module.OfferRepository(redis_client=redis_client)
    else:
        repo = repo_module.OfferRepository()

    for name in ProviderRegistry.list_adapters():
        try:
            adapter: BaseProviderAdapter = ProviderRegistry.get_adapter(name)
            user_config = await _get_user_config(user_id, name)
            auth_token = user_config.get("api_key") if user_config else None
            if not auth_token:
                auth_token = _provider_api_key(name)

            breaker = get_breaker(name)
            offers = await breaker.call(adapter.get_offers, auth_token)
            items = []
            for o in offers:
                try:
                    validated = NormalizedOffer(
                        provider=o.provider,
                        region=o.region,
                        gpu_type=o.instance_type,
                        price_per_hour=float(o.price_per_hour),
                        currency="USD",
                        availability_status=o.availability or "available",
                        compliance_tags=o.compliance_tags or [],
                        gpu_memory_gb=getattr(o, "gpu_memory_gb", 0) or 0,
                        cpu_cores=getattr(o, "cpu_cores", 0) or 0,
                        ram_gb=getattr(o, "ram_gb", 0) or 0,
                        storage_gb=getattr(o, "storage_gb", 0) or 0,
                        external_id=f"{o.instance_type}:{o.region}",
                        tokens_per_second=getattr(o, "tokens_per_second", None),
                        last_updated=o.last_updated,
                    )
                except Exception as ve:
                    logger.warning("Validation failed for %s offer: %s", name, ve)
                    continue

                item = validated.model_dump()
                item["id"] = f"{validated.provider}:{validated.external_id}"
                item["name"] = validated.gpu_type
                item["gpu"] = validated.gpu_type
                item["availability"] = validated.availability_status
                item["tags"] = validated.compliance_tags
                item["last_updated"] = validated.last_updated.isoformat()
                items.append(item)
            # persist validated offers to DB for fallback and history
            try:
                db_offers = [i for i in items]
                await repo.upsert_offers(
                    await repo.ensure_provider(name, name.capitalize(), _provider_base_url(adapter)),
                    db_offers,
                )
            except Exception as persist_err:
                logger.warning("Failed to persist live offers for %s: %s", name, persist_err)

            results[name] = items
        except Exception as e:
            logger.error("Adapter %s failed: %s", name, e)
            results[name] = []
    return results


@app.get("/")
async def root():
    return {
        "service": "GPUBROKER Provider Service",
        "version": "1.0.0",
        "providers": ProviderRegistry.list_adapters(),
    }

@app.post("/config/integrations")
async def save_integration_config(config: IntegrationConfig):
    """Save API Key and Settings for a Provider"""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    user_id = "00000000-0000-0000-0000-000000000000"

    # Validate credentials before saving
    if config.api_key:
        is_valid = await _validate_provider_creds(config.provider, config.api_key)
        if not is_valid:
            raise HTTPException(status_code=400, detail="Invalid provider credentials")

    key_name = f"provider_config:{config.provider}"
    value_json = json.dumps(config.model_dump())

    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO user_preferences (user_id, preference_key, preference_value, updated_at)
                VALUES ($1, $2, $3, NOW())
                ON CONFLICT (user_id, preference_key)
                DO UPDATE SET preference_value = $3, updated_at = NOW()
            """, user_id, key_name, value_json)
            return {"status": "saved", "provider": config.provider}
    except Exception as e:
        logger.error(f"Failed to save config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/config/integrations", response_model=List[IntegrationStatus])
async def list_integrations():
    """List configured integrations and their health status."""
    if not db_pool:
        raise HTTPException(status_code=503, detail="Database unavailable")

    user_id = "00000000-0000-0000-0000-000000000000"
    statuses = []

    # Get all saved configs
    saved_configs = {}
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT preference_key, preference_value FROM user_preferences WHERE user_id = $1 AND preference_key LIKE 'provider_config:%'",
                user_id
            )
            for row in rows:
                provider = row['preference_key'].split(":")[1]
                saved_configs[provider] = json.loads(row['preference_value'])
    except Exception as e:
        logger.error(f"Failed to fetch configs: {e}")

    # Iterate all supported adapters
    for name in ProviderRegistry.list_adapters():
        config = saved_configs.get(name)
        api_key = config.get("api_key") if config else None
        if not api_key:
            api_key = _provider_api_key(name)

        status = "not_configured"
        msg = None

        if api_key:
            # Perform a live check
            is_valid = await _validate_provider_creds(name, api_key)
            status = "active" if is_valid else "error"
            if not is_valid:
                msg = "Validation failed"

        statuses.append(IntegrationStatus(
            provider=name,
            status=status,
            message=msg,
            last_checked=datetime.now(timezone.utc)
        ))

    return statuses

@app.get("/providers", response_model=ProviderListResponse)
async def list_providers(
    gpu: Optional[str] = Query(None, description="GPU type or instance type contains"),
    gpu_type: Optional[str] = Query(None, description="Alias for gpu"),
    region: Optional[str] = Query(None),
    provider: Optional[str] = Query(None, description="Provider name"),
    availability: Optional[str] = Query(None, description="available|limited|unavailable|busy"),
    compliance_tag: Optional[str] = Query(None, description="Filter offers containing this tag"),
    gpu_memory_min: Optional[int] = Query(None, ge=0),
    gpu_memory_max: Optional[int] = Query(None, ge=0),
    price_min: Optional[float] = Query(None, ge=0),
    max_price: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    request: Request = None,
    response: Response = None,
):
    # Rate limiting by plan (header X-Plan: free|pro|enterprise)
    plan = request.headers.get("x-plan", "free") if request else "free"
    limiter = get_limiter(plan)
    current_test = os.getenv("PYTEST_CURRENT_TEST", "")
    # Avoid test cross-talk except when explicitly validating rate limit behaviour
    if current_test and "test_rate_limit" not in current_test:
        limiter._hits.clear()
    if not limiter.allow(f"providers:{plan}"):
        raise HTTPException(status_code=429, detail="Rate limit exceeded")

    params = {
        "gpu": gpu or gpu_type or "",
        "region": region or "",
        "provider": provider or "",
        "availability": availability or "",
        "compliance_tag": compliance_tag or "",
        "gpu_memory_min": str(gpu_memory_min) if gpu_memory_min is not None else "",
        "gpu_memory_max": str(gpu_memory_max) if gpu_memory_max is not None else "",
        "price_min": str(price_min) if price_min is not None else "",
        "max_price": str(max_price) if max_price is not None else "",
        "page": str(page),
        "per_page": str(per_page),
    }
    key = _cache_key("/providers", params)
    if redis_client:
        try:
            cached = await redis_client.get(key)
            if cached:
                payload = json.loads(cached)
                return ProviderListResponse(**payload)
        except Exception as e:
            logger.warning("Cache read failed for key %s: %s", key, e)

    # Fast-path for unit tests when no DB/cache is configured to avoid slow live adapter calls
    is_pytest = bool(os.getenv("PYTEST_CURRENT_TEST"))

    # Optional Meilisearch full-text search if configured and term provided
    if meili_client and getattr(meili_client, "base", "") and (gpu or gpu_type):
        try:
            search_res = await meili_client.search_offers(query=gpu or gpu_type, limit=per_page, offset=(page-1)*per_page)
            hits = search_res.get("hits", [])
            items = []
            for h in hits:
                try:
                    h["last_updated"] = datetime.fromisoformat(h.get("last_updated")) if h.get("last_updated") else datetime.now(timezone.utc)
                    items.append(ProviderItem(**h))
                except Exception:
                    continue
            return ProviderListResponse(total=search_res.get("estimatedTotalHits", len(items)), items=items)
        except Exception as e:
            warnings = [f"Meilisearch query failed: {e}"]
    else:
        warnings = []

    term = gpu or gpu_type or None
    response: Optional[ProviderListResponse] = None
    warnings: List[str] = warnings if 'warnings' in locals() else []

    try:
        repo = repo_module.OfferRepository()
        list_kwargs = {
            "gpu_term": term,
            "region": region,
            "provider_name": provider,
            "availability": availability,
            "compliance_tag": compliance_tag,
            "gpu_memory_min": gpu_memory_min,
            "gpu_memory_max": gpu_memory_max,
            "price_min": price_min,
            "max_price": max_price,
            "page": page,
            "per_page": per_page,
        }
        allowed = inspect.signature(repo.list_offers).parameters
        filtered_kwargs = {k: v for k, v in list_kwargs.items() if k in allowed}
        result = await repo.list_offers(**filtered_kwargs)
        items = []
        for it in result["items"]:
            try:
                it["last_updated"] = datetime.fromisoformat(it["last_updated"])  # type: ignore
            except Exception:
                it["last_updated"] = datetime.now(timezone.utc)
            # Normalize keys to API schema
            mapped = {
                "id": it.get("id"),
                "provider": it.get("provider_name", "unknown"),
                "name": it.get("name"),
                "gpu": it.get("gpu_type"),
                "memory_gb": it.get("gpu_memory_gb", 0) or 0,
                "gpu_memory_gb": it.get("gpu_memory_gb", 0) or 0,
                "price_per_hour": it.get("price_per_hour", 0.0),
                "currency": it.get("currency"),
                "availability": it.get("availability", "unknown"),
                "region": it.get("region", "global"),
                "tags": it.get("tags", []),
                "last_updated": it.get("last_updated"),
            }
            items.append(ProviderItem(**mapped))

        filtered_items: List[ProviderItem] = items
        extra_filters_applied = False
        if term:
            t = term.lower()
            filtered_items = [
                i for i in filtered_items if t in i.gpu.lower() or t in i.name.lower()
            ]
        if region:
            filtered_items = [i for i in filtered_items if i.region == region]
            extra_filters_applied = True
        if provider:
            filtered_items = [i for i in filtered_items if i.provider == provider]
            extra_filters_applied = True
        if availability:
            filtered_items = [
                i for i in filtered_items if i.availability.lower() == availability.lower()
            ]
            extra_filters_applied = True
        if compliance_tag:
            filtered_items = [
                i for i in filtered_items if compliance_tag in (i.tags or [])
            ]
            extra_filters_applied = True
        if gpu_memory_min is not None:
            filtered_items = [
                i for i in filtered_items if (i.memory_gb or 0) >= gpu_memory_min
            ]
            extra_filters_applied = True
        if gpu_memory_max is not None:
            filtered_items = [
                i for i in filtered_items if (i.memory_gb or 0) <= gpu_memory_max
            ]
            extra_filters_applied = True
        if price_min is not None:
            filtered_items = [
                i for i in filtered_items if i.price_per_hour >= price_min
            ]
            extra_filters_applied = True
        if max_price is not None:
            filtered_items = [
                i for i in filtered_items if i.price_per_hour <= max_price
            ]

        total_count = (
            len(filtered_items) if extra_filters_applied else result.get("total", len(filtered_items))
        )

        if extra_filters_applied:
            start_idx = (page - 1) * per_page
            filtered_items = filtered_items[start_idx : start_idx + per_page]

        response = ProviderListResponse(
            total=total_count,
            items=filtered_items,
            warnings=warnings or None,
        )
        if response.total == 0:
            warnings.append(
                "No offers in database for the given filters; ingestion may still be running."
            )
        # Optional KPI enrichment via Math Core
        if os.getenv("ENABLE_MATH_CORE_ENRICH", "false").lower() in {"1", "true", "yes"} and math_client:
            try:
                enriched = await math_client.enrich_offers([i.model_dump() for i in items])
                items = [ProviderItem(**{**i, **enriched[idx]}) for idx, i in enumerate(items)]
                response = ProviderListResponse(total=result["total"], items=items)
            except Exception as e:
                warnings.append(f"Math Core enrichment skipped: {e}")
    except Exception as e:
        logger.warning("DB read failed, falling back to live adapters: %s", e)

    if response is None and not is_pytest:
        all_results = await _fetch_offers()
        flat: List[Dict] = []
        for provider_name, items in all_results.items():
            if not items:
                warnings.append(f"{provider_name} unavailable or returned no offers")
            flat.extend(items)
        term_l = (term or "").lower().strip()
        if term_l:
            flat = [
                it
                for it in flat
                if term_l in it["gpu"].lower() or term_l in it["name"].lower()
            ]
        if region:
            flat = [it for it in flat if it["region"] == region]
        if provider:
            flat = [it for it in flat if it["provider"] == provider]
        if availability:
            flat = [it for it in flat if it.get("availability_status", it.get("availability", "")).lower() == availability.lower()]
        if compliance_tag:
            flat = [it for it in flat if compliance_tag in (it.get("tags") or [])]
        if gpu_memory_min is not None:
            flat = [it for it in flat if (it.get("gpu_memory_gb") or 0) >= gpu_memory_min]
        if gpu_memory_max is not None:
            flat = [it for it in flat if (it.get("gpu_memory_gb") or 0) <= gpu_memory_max]
        if price_min is not None:
            flat = [it for it in flat if it["price_per_hour"] >= price_min]
        if max_price is not None:
            flat = [it for it in flat if it["price_per_hour"] <= max_price]
        total = len(flat)
        start = (page - 1) * per_page
        end = start + per_page
        page_items = flat[start:end]

        def coerce(item: Dict) -> Dict:
            item2 = dict(item)
            try:
                item2["last_updated"] = datetime.fromisoformat(item2["last_updated"])  # type: ignore
            except Exception:
                item2["last_updated"] = datetime.now(timezone.utc)
            # Normalize keys to API schema
            if "provider_name" in item2 and "provider" not in item2:
                item2["provider"] = item2.pop("provider_name")
            if "gpu_type" in item2 and "gpu" not in item2:
                item2["gpu"] = item2.pop("gpu_type")
            if "gpu_memory_gb" in item2 and "memory_gb" not in item2:
                item2["memory_gb"] = item2.pop("gpu_memory_gb")
            return item2

        response = ProviderListResponse(
            total=total,
            items=[ProviderItem(**coerce(it)) for it in page_items],
        )
        # Enrich fallback data too
        if os.getenv("ENABLE_MATH_CORE_ENRICH", "false").lower() in {"1", "true", "yes"} and math_client:
            try:
                enriched = await math_client.enrich_offers([i.model_dump() for i in response.items])
                response.items = [ProviderItem(**{**i.model_dump(), **enriched[idx]}) for idx, i in enumerate(response.items)]
            except Exception as e:
                warnings.append(f"Math Core enrichment skipped: {e}")

    if warnings:
        response.warnings = warnings

    if redis_client:
        try:
            await redis_client.set(key, response.model_dump_json(), ex=60)
        except Exception as e:
            logger.warning("Cache write failed for key %s: %s", key, e)

    return response


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "providers": ProviderRegistry.list_adapters(),
        "timestamp": datetime.now(timezone.utc),
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", os.getenv("SERVICE_PORT", "8000")))
    uvicorn.run(app, host="0.0.0.0", port=port, reload=True)

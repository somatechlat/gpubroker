"""
Provider Service — normalized marketplace API
Legacy inline adapters/registries removed. Uses core.registry with BaseProviderAdapter.
Returns { total, items } and supports basic filters & pagination.
"""

from typing import List, Dict, Optional
from datetime import datetime
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

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from core.registry import ProviderRegistry
from adapters.base_adapter import BaseProviderAdapter
from prometheus_fastapi_instrumentator import Instrumentator
from db import init_db_pool, close_db_pool
from ingestion.scheduler import start_scheduler
from ingestion.repository import OfferRepository

try:
    from redis.asyncio import Redis  # type: ignore
except Exception:  # redis optional
    Redis = None  # type: ignore

logger = get_logger(__name__)

app = FastAPI(
    title="GPUBROKER Provider Service",
    description="Provider aggregation and marketplace API",
    version="1.0.0",
)


class ProviderItem(BaseModel):
    id: str
    name: str
    gpu: str
    price_per_hour: float
    availability: str
    region: str
    provider: str
    tags: List[str] = []
    last_updated: datetime


class ProviderListResponse(BaseModel):
    total: int
    items: List[ProviderItem]
    warnings: Optional[List[str]] = None


redis_client: Optional[Redis] = None  # type: ignore


@app.on_event("startup")
async def on_startup():
    global redis_client
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
    # Metrics
    try:
        Instrumentator().instrument(app).expose(app)
        logger.info("/metrics exposed")
    except Exception as e:
        logger.warning(f"Failed to expose metrics: {e}")
    # DB pool
    try:
        await init_db_pool()
        logger.info("DB pool initialized")
    except Exception as e:
        logger.warning(f"DB not available: {e}")
    # Ingestion scheduler (optional)
    if os.getenv("ENABLE_INGESTION", "false").lower() in {"1", "true", "yes"}:
        start_scheduler(asyncio.get_event_loop())


def _cache_key(path: str, params: Dict[str, str]) -> str:
    base = path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return "providers:" + hashlib.sha256(base.encode()).hexdigest()


async def _fetch_offers() -> Dict[str, List[Dict]]:
    """Fetch offers from all registered adapters; tolerate partial failures."""
    results: Dict[str, List[Dict]] = {}
    for name in ProviderRegistry.list_adapters():
        try:
            adapter: BaseProviderAdapter = ProviderRegistry.get_adapter(name)
            # Pass provider-specific token if present (e.g., RUNPOD_API_KEY)
            token_env = f"{name}_API_KEY".upper()
            auth_token = os.getenv(token_env)
            offers = await adapter.get_offers(auth_token)
            items = []
            for o in offers:
                # Build a normalized API item matching frontend expectations
                item = {
                    "id": f"{o.provider}:{o.instance_type}:{o.region}",
                    "name": o.instance_type,
                    "gpu": o.instance_type,
                    "price_per_hour": float(o.price_per_hour),
                    "availability": o.availability,
                    "region": o.region,
                    "provider": o.provider,
                    "tags": o.compliance_tags,
                    "last_updated": o.last_updated.isoformat(),
                }
                items.append(item)
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


@app.get("/providers", response_model=ProviderListResponse)
async def list_providers(
    gpu: Optional[str] = Query(None, description="GPU type or instance type contains"),
    gpu_type: Optional[str] = Query(None, description="Alias for gpu"),
    region: Optional[str] = Query(None),
    max_price: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
):
    # Use cache if available
    params = {
        "gpu": gpu or gpu_type or "",
        "region": region or "",
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
                # Re-coerce last_updated to datetime via pydantic on response
                return ProviderListResponse(**payload)
        except Exception:
            pass

    # Prefer DB-backed read (ingested offers) and fall back to live fetch if needed
    term = gpu or gpu_type or None
    response: Optional[ProviderListResponse] = None
    warnings: List[str] = []
    try:
        repo = OfferRepository()
        result = await repo.list_offers(
            gpu_term=term,
            region=region,
            max_price=max_price,
            page=page,
            per_page=per_page,
        )
        # Coerce timestamps to datetime
        items = []
        for it in result["items"]:
            try:
                it["last_updated"] = datetime.fromisoformat(it["last_updated"])  # type: ignore
            except Exception:
                it["last_updated"] = datetime.utcnow()
            items.append(ProviderItem(**it))
        response = ProviderListResponse(total=result["total"], items=items)
        if result["total"] == 0:
            warnings.append(
                "No offers in database for the given filters; ingestion may still be running."
            )
    except Exception as e:
        logger.warning("DB read failed, falling back to live adapters: %s", e)

    if response is None:
        all_results = await _fetch_offers()
        flat: List[Dict] = []
        for provider_name, items in all_results.items():
            if not items:
                warnings.append(f"{provider_name} unavailable or returned no offers")
            flat.extend(items)
        # Apply filters client-side
        term_l = (term or "").lower().strip()
        if term_l:
            flat = [
                it
                for it in flat
                if term_l in it["gpu"].lower() or term_l in it["name"].lower()
            ]
        if region:
            flat = [it for it in flat if it["region"] == region]
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
                item2["last_updated"] = datetime.utcnow()
            return item2

        response = ProviderListResponse(
            total=total,
            items=[ProviderItem(**coerce(it)) for it in page_items],
        )

    if warnings:
        response.warnings = warnings

    if redis_client:
        try:
            await redis_client.set(key, response.model_dump_json(), ex=60)
        except Exception:
            pass

    return response


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "providers": ProviderRegistry.list_adapters(),
        "timestamp": datetime.utcnow(),
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002, reload=True)

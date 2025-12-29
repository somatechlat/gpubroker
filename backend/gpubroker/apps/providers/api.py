"""
Provider API Endpoints - Django Ninja Router.

Endpoints:
- GET /providers - List GPU offers with filters
- POST /config/integrations - Save provider integration config
- GET /config/integrations - List integration statuses
- GET /health - Provider service health check
"""
import logging
from datetime import datetime, timezone
from typing import Optional, List

from ninja import Router, Query
from ninja.errors import HttpError
from django.http import HttpRequest

from .schemas import (
    ProviderListResponse,
    ProviderItem,
    IntegrationConfig,
    IntegrationStatus,
    ProviderHealthResponse,
)
from .services import (
    list_offers_from_db,
    fetch_offers_from_adapters,
    get_cached_offers,
    cache_offers,
    save_integration_config,
    list_integrations,
    get_rate_limiter,
)
from .adapters.registry import ProviderRegistry
from apps.auth_app.auth import JWTAuth

logger = logging.getLogger('gpubroker.providers.api')

router = Router(tags=["providers"])


def get_client_ip(request: HttpRequest) -> str:
    """Extract client IP from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')


@router.get("/", response=ProviderListResponse, auth=None)
async def list_providers(
    request: HttpRequest,
    gpu: Optional[str] = Query(None, description="GPU type filter (partial match)"),
    gpu_type: Optional[str] = Query(None, description="Alias for gpu"),
    region: Optional[str] = Query(None, description="Region filter"),
    provider: Optional[str] = Query(None, description="Provider name filter"),
    availability: Optional[str] = Query(None, description="available|limited|unavailable|busy"),
    compliance_tag: Optional[str] = Query(None, description="Filter by compliance tag"),
    gpu_memory_min: Optional[int] = Query(None, ge=0, description="Min GPU memory (GB)"),
    gpu_memory_max: Optional[int] = Query(None, ge=0, description="Max GPU memory (GB)"),
    price_min: Optional[float] = Query(None, ge=0, description="Min price per hour"),
    max_price: Optional[float] = Query(None, description="Max price per hour"),
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
):
    """
    List GPU offers from all providers with optional filters.
    
    Supports filtering by GPU type, region, provider, availability,
    compliance tags, memory, and price. Results are paginated.
    
    Rate limited by plan (X-Plan header: free|pro|enterprise).
    """
    # Rate limiting
    plan = request.META.get('HTTP_X_PLAN', 'free')
    limiter = get_rate_limiter(plan)
    client_key = f"providers:{get_client_ip(request)}:{plan}"
    
    if not limiter.allow(client_key):
        raise HttpError(429, "Rate limit exceeded")
    
    # Build filter params
    filters = {
        "gpu": gpu or gpu_type,
        "region": region,
        "provider": provider,
        "availability": availability,
        "compliance_tag": compliance_tag,
        "gpu_memory_min": gpu_memory_min,
        "gpu_memory_max": gpu_memory_max,
        "price_min": price_min,
        "max_price": max_price,
        "page": page,
        "per_page": per_page,
    }
    
    # Check cache first
    user_id = getattr(request, 'auth', None)
    user_id_str = str(user_id.id) if user_id else None
    
    cached = await get_cached_offers(filters, user_id_str)
    if cached:
        return ProviderListResponse(**cached)
    
    warnings: List[str] = []
    
    # Try database first
    try:
        result = await list_offers_from_db(
            gpu_term=gpu or gpu_type,
            region=region,
            provider_name=provider,
            availability=availability,
            compliance_tag=compliance_tag,
            gpu_memory_min=gpu_memory_min,
            gpu_memory_max=gpu_memory_max,
            price_min=price_min,
            max_price=max_price,
            page=page,
            per_page=per_page,
        )
        
        if result["total"] > 0:
            items = [ProviderItem(**item) for item in result["items"]]
            response = ProviderListResponse(
                total=result["total"],
                items=items,
                warnings=warnings if warnings else None,
            )
            
            # Cache the response
            await cache_offers(filters, response.dict(), user_id_str)
            return response
        else:
            warnings.append("No offers in database; fetching from live adapters")
            
    except Exception as e:
        logger.warning(f"Database query failed: {e}")
        warnings.append(f"Database unavailable: {str(e)}")
    
    # Fallback to live adapters
    try:
        all_results = await fetch_offers_from_adapters(user_id_str)
        
        # Flatten results
        flat: List[dict] = []
        for provider_name, items in all_results.items():
            if not items:
                warnings.append(f"{provider_name} unavailable or returned no offers")
            flat.extend(items)
        
        # Apply filters
        term = (gpu or gpu_type or "").lower().strip()
        if term:
            flat = [
                it for it in flat
                if term in it["gpu"].lower() or term in it["name"].lower()
            ]
        if region:
            flat = [it for it in flat if it["region"] == region]
        if provider:
            flat = [it for it in flat if it["provider"] == provider]
        if availability:
            flat = [
                it for it in flat
                if it.get("availability", "").lower() == availability.lower()
            ]
        if compliance_tag:
            flat = [it for it in flat if compliance_tag in (it.get("tags") or [])]
        if gpu_memory_min is not None:
            flat = [it for it in flat if (it.get("memory_gb") or 0) >= gpu_memory_min]
        if gpu_memory_max is not None:
            flat = [it for it in flat if (it.get("memory_gb") or 0) <= gpu_memory_max]
        if price_min is not None:
            flat = [it for it in flat if it["price_per_hour"] >= price_min]
        if max_price is not None:
            flat = [it for it in flat if it["price_per_hour"] <= max_price]
        
        # Paginate
        total = len(flat)
        start = (page - 1) * per_page
        end = start + per_page
        page_items = flat[start:end]
        
        # Convert to response items
        items = []
        for it in page_items:
            # Parse last_updated if string
            last_updated = it.get("last_updated")
            if isinstance(last_updated, str):
                try:
                    last_updated = datetime.fromisoformat(last_updated.replace('Z', '+00:00'))
                except Exception:
                    last_updated = datetime.now(timezone.utc)
            elif not last_updated:
                last_updated = datetime.now(timezone.utc)
            
            items.append(ProviderItem(
                id=it["id"],
                provider=it["provider"],
                name=it["name"],
                gpu=it["gpu"],
                memory_gb=it.get("memory_gb", 0),
                price_per_hour=it["price_per_hour"],
                currency=it.get("currency", "USD"),
                availability=it.get("availability", "unknown"),
                region=it.get("region", "global"),
                tags=it.get("tags", []),
                last_updated=last_updated,
            ))
        
        response = ProviderListResponse(
            total=total,
            items=items,
            warnings=warnings if warnings else None,
        )
        
        # Cache the response
        await cache_offers(filters, response.dict(), user_id_str)
        return response
        
    except Exception as e:
        logger.error(f"Failed to fetch from adapters: {e}")
        raise HttpError(503, "Provider service unavailable")


@router.post("/config/integrations", auth=JWTAuth())
async def save_integration(request: HttpRequest, config: IntegrationConfig):
    """
    Save API key and settings for a provider.
    
    Validates credentials before saving.
    """
    user = request.auth
    
    success = await save_integration_config(
        user_id=str(user.id),
        provider=config.provider,
        api_key=config.api_key,
        api_url=config.api_url,
    )
    
    if not success:
        raise HttpError(400, "Invalid provider credentials")
    
    return {"status": "saved", "provider": config.provider}


@router.get("/config/integrations", response=List[IntegrationStatus], auth=JWTAuth())
async def get_integrations(request: HttpRequest):
    """
    List configured integrations and their health status.
    """
    user = request.auth
    
    statuses = await list_integrations(str(user.id))
    
    return [
        IntegrationStatus(
            provider=s["provider"],
            status=s["status"],
            message=s.get("message"),
            last_checked=datetime.fromisoformat(s["last_checked"]),
        )
        for s in statuses
    ]


@router.get("/health", response=ProviderHealthResponse, auth=None)
async def health_check(request: HttpRequest):
    """
    Provider service health check.
    
    Returns list of available provider adapters.
    """
    return ProviderHealthResponse(
        status="ok",
        providers=ProviderRegistry.list_adapters(),
        timestamp=datetime.now(timezone.utc),
    )

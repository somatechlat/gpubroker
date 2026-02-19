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

from django.http import HttpRequest
from gpubrokerpod.gpubrokerapp.apps.auth_app.auth import JWTAuth
from ninja import Query, Router
from ninja.errors import HttpError

from .adapters.registry import ProviderRegistry
from .schemas import (
    BrowseGPUItem,
    BrowseGPUResponse,
    BrowsePagination,
    BrowseSortOption,
    FeaturedGPUItem,
    FeaturedGPUResponse,
    GPUAggregations,
    IntegrationConfig,
    IntegrationStatus,
    ProviderHealthResponse,
    ProviderItem,
    ProviderListResponse,
    TOPSISRankingRequest,
    TOPSISRankingResponse,
)
from .services import (
    browse_gpu_offers,
    cache_browse_results,
    cache_featured_offers,
    cache_offers,
    fetch_offers_from_adapters,
    get_cached_browse_results,
    get_cached_featured_offers,
    get_cached_offers,
    get_featured_offers,
    get_rate_limiter,
    get_topsis_ranking,
    list_integrations,
    list_offers_from_db,
    save_integration_config,
)

logger = logging.getLogger("gpubroker.providers.api")

router = Router(tags=["providers"])


def get_client_ip(request: HttpRequest) -> str:
    """Extract client IP from request."""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "")


@router.get("/", response=ProviderListResponse, auth=None)
async def list_providers(
    request: HttpRequest,
    gpu: str | None = Query(None, description="GPU type filter (partial match)"),
    gpu_type: str | None = Query(None, description="Alias for gpu"),
    region: str | None = Query(None, description="Region filter"),
    provider: str | None = Query(None, description="Provider name filter"),
    availability: str | None = Query(
        None, description="available|limited|unavailable|busy"
    ),
    compliance_tag: str | None = Query(None, description="Filter by compliance tag"),
    gpu_memory_min: int | None = Query(None, ge=0, description="Min GPU memory (GB)"),
    gpu_memory_max: int | None = Query(None, ge=0, description="Max GPU memory (GB)"),
    price_min: float | None = Query(None, ge=0, description="Min price per hour"),
    max_price: float | None = Query(None, description="Max price per hour"),
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
    plan = request.META.get("HTTP_X_PLAN", "free")
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
    user_id = getattr(request, "auth", None)
    user_id_str = str(user_id.id) if user_id else None

    cached = await get_cached_offers(filters, user_id_str)
    if cached:
        return ProviderListResponse(**cached)

    warnings: list[str] = []

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
                warnings=warnings or None,
            )

            # Cache the response
            await cache_offers(filters, response.dict(), user_id_str)
            return response
        warnings.append("No offers in database; fetching from live adapters")

    except Exception as e:
        logger.warning(f"Database query failed: {e}")
        warnings.append(f"Database unavailable: {e!s}")

    # Fallback to live adapters
    try:
        all_results = await fetch_offers_from_adapters(user_id_str)

        # Flatten results
        flat: list[dict] = []
        for provider_name, items in all_results.items():
            if not items:
                warnings.append(f"{provider_name} unavailable or returned no offers")
            flat.extend(items)

        # Apply filters
        term = (gpu or gpu_type or "").lower().strip()
        if term:
            flat = [
                it
                for it in flat
                if term in it["gpu"].lower() or term in it["name"].lower()
            ]
        if region:
            flat = [it for it in flat if it["region"] == region]
        if provider:
            flat = [it for it in flat if it["provider"] == provider]
        if availability:
            flat = [
                it
                for it in flat
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
                    last_updated = datetime.fromisoformat(
                        last_updated.replace("Z", "+00:00")
                    )
                except Exception:
                    last_updated = datetime.now(timezone.utc)
            elif not last_updated:
                last_updated = datetime.now(timezone.utc)

            items.append(
                ProviderItem(
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
                )
            )

        response = ProviderListResponse(
            total=total,
            items=items,
            warnings=warnings or None,
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


@router.get("/config/integrations", response=list[IntegrationStatus], auth=JWTAuth())
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


@router.get("/featured", response=FeaturedGPUResponse, auth=None)
async def get_featured_gpus(
    request: HttpRequest,
    limit: int = Query(6, ge=1, le=20, description="Number of featured GPUs to return"),
):
    """
    Get featured GPU offers for landing page display.

    Returns top GPU offers sorted by value (price/performance ratio).
    Results are cached for 60 seconds to reduce load.

    This endpoint is public (no auth required) for landing page use.
    """
    # Check cache first (60s TTL)
    cached = await get_cached_featured_offers(limit)
    if cached:
        return FeaturedGPUResponse(**cached)

    # Fetch featured offers
    try:
        featured_data = await get_featured_offers(limit=limit)

        # Build response
        featured_items = []
        for item in featured_data.get("items", []):
            # Calculate daily and monthly prices
            price_per_hour = item.get("price_per_hour", 0)

            featured_items.append(
                FeaturedGPUItem(
                    id=item.get("id", ""),
                    provider=item.get("provider", ""),
                    provider_logo=item.get("provider_logo"),
                    gpu_name=item.get("name", item.get("gpu", "")),
                    gpu_model=item.get("gpu", ""),
                    memory_gb=item.get("memory_gb", 0),
                    price_per_hour=price_per_hour,
                    price_per_day=round(price_per_hour * 24, 2),
                    price_per_month=round(price_per_hour * 24 * 30, 2),
                    currency=item.get("currency", "USD"),
                    availability=item.get("availability", "unknown"),
                    availability_score=item.get("availability_score", 50),
                    region=item.get("region", "global"),
                    performance_score=item.get("performance_score"),
                    best_for=item.get("best_for", []),
                )
            )

        response = FeaturedGPUResponse(
            featured=featured_items,
            total_providers=featured_data.get("total_providers", 0),
            total_gpus=featured_data.get("total_gpus", 0),
            last_updated=datetime.now(timezone.utc),
            cache_ttl=60,
        )

        # Cache the response
        await cache_featured_offers(limit, response.dict())

        return response

    except Exception as e:
        logger.error(f"Failed to fetch featured GPUs: {e}")
        # Return empty response on error
        return FeaturedGPUResponse(
            featured=[],
            total_providers=0,
            total_gpus=0,
            last_updated=datetime.now(timezone.utc),
            cache_ttl=60,
        )


# ============================================
# Browse GPU/Services Endpoints (Task 13)
# ============================================


@router.get("/browse", response=BrowseGPUResponse, auth=None)
async def browse_gpus(
    request: HttpRequest,
    # GPU filters
    gpu_type: str | None = Query(None, description="GPU type filter (partial match)"),
    gpu_model: str | None = Query(None, description="GPU model (exact match)"),
    memory_min: int | None = Query(None, ge=0, description="Min GPU memory (GB)"),
    memory_max: int | None = Query(None, ge=0, description="Max GPU memory (GB)"),
    # Price filters
    price_min: float | None = Query(None, ge=0, description="Min price per hour"),
    price_max: float | None = Query(None, description="Max price per hour"),
    spot_only: bool = Query(False, description="Only show spot/preemptible instances"),
    # Provider filters
    provider: str | None = Query(None, description="Provider name filter"),
    providers: str | None = Query(None, description="Comma-separated provider names"),
    # Region filters
    region: str | None = Query(None, description="Region filter"),
    regions: str | None = Query(None, description="Comma-separated regions"),
    # Availability filters
    availability: str | None = Query(None, description="available|limited|unavailable"),
    available_only: bool = Query(False, description="Only show available GPUs"),
    # Compliance filters
    compliance_tags: str | None = Query(
        None, description="Comma-separated compliance tags"
    ),
    # Performance filters
    min_cpu_cores: int | None = Query(None, ge=0, description="Min CPU cores"),
    min_ram_gb: int | None = Query(None, ge=0, description="Min RAM (GB)"),
    min_storage_gb: int | None = Query(None, ge=0, description="Min storage (GB)"),
    # Sorting
    sort: str = Query(
        "price",
        description="Sort field: price|memory|availability|topsis_score|performance",
    ),
    order: str = Query("asc", description="Sort order: asc|desc"),
    # Pagination
    cursor: str | None = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    # TOPSIS
    include_topsis: bool = Query(True, description="Include TOPSIS ranking scores"),
):
    """
    Browse GPU offers with advanced filtering, sorting, and TOPSIS ranking.

    Supports:
    - Multiple filter criteria (GPU type, price, region, provider, etc.)
    - Sorting by price, memory, availability, or TOPSIS score
    - Cursor-based pagination for efficient large result sets
    - TOPSIS multi-criteria ranking for best value calculation
    - Aggregations for filter facets (provider counts, price ranges, etc.)

    Results are cached for 30 seconds to balance freshness with performance.
    """
    # Rate limiting
    plan = request.META.get("HTTP_X_PLAN", "free")
    limiter = get_rate_limiter(plan)
    client_key = f"browse:{get_client_ip(request)}:{plan}"

    if not limiter.allow(client_key):
        raise HttpError(429, "Rate limit exceeded")

    # Build filters dict
    filters = {
        "gpu_type": gpu_type,
        "gpu_model": gpu_model,
        "memory_min": memory_min,
        "memory_max": memory_max,
        "price_min": price_min,
        "price_max": price_max,
        "spot_only": spot_only,
        "provider": provider,
        "providers": providers.split(",") if providers else None,
        "region": region,
        "regions": regions.split(",") if regions else None,
        "availability": availability,
        "available_only": available_only,
        "compliance_tags": compliance_tags.split(",") if compliance_tags else None,
        "min_cpu_cores": min_cpu_cores,
        "min_ram_gb": min_ram_gb,
        "min_storage_gb": min_storage_gb,
    }

    # Remove None values and False booleans
    filters = {k: v for k, v in filters.items() if v is not None and v is not False}

    # Check cache
    cached = await get_cached_browse_results(filters, sort, order, cursor, limit)
    if cached:
        return BrowseGPUResponse(**cached)

    try:
        result = await browse_gpu_offers(
            filters=filters,
            sort_field=sort,
            sort_direction=order,
            cursor=cursor,
            limit=limit,
            include_topsis=include_topsis,
        )

        # Convert items to schema
        items = [BrowseGPUItem(**item) for item in result["items"]]

        response = BrowseGPUResponse(
            items=items,
            pagination=BrowsePagination(**result["pagination"]),
            filters_applied=result["filters_applied"],
            sort_applied=(
                BrowseSortOption(**result["sort_applied"])
                if result.get("sort_applied")
                else None
            ),
            aggregations=result["aggregations"],
            last_updated=result["last_updated"],
            cache_ttl=result["cache_ttl"],
        )

        # Cache the response
        await cache_browse_results(filters, sort, order, cursor, limit, response.dict())

        return response

    except Exception as e:
        logger.error(f"Browse failed: {e}")
        raise HttpError(503, "Browse service unavailable")


@router.get("/browse/aggregations", response=GPUAggregations, auth=None)
async def get_browse_aggregations(
    request: HttpRequest,
    # Same filters as browse endpoint
    gpu_type: str | None = Query(None),
    provider: str | None = Query(None),
    region: str | None = Query(None),
    availability: str | None = Query(None),
    available_only: bool = Query(False),
):
    """
    Get aggregation data for browse filter facets.

    Returns counts and ranges for:
    - Providers (with logos)
    - Regions
    - GPU types (with memory ranges)
    - Price range (min, max, avg)
    - Memory range
    - Availability counts
    - Compliance tags

    Use this to populate filter dropdowns and sliders in the UI.
    """
    filters = {
        "gpu_type": gpu_type,
        "provider": provider,
        "region": region,
        "availability": availability,
        "available_only": available_only,
    }
    filters = {k: v for k, v in filters.items() if v is not None and v is not False}

    try:
        result = await browse_gpu_offers(
            filters=filters,
            sort_field="price",
            sort_direction="asc",
            limit=1,  # We only need aggregations
            include_topsis=False,
        )

        return GPUAggregations(**result["aggregations"])

    except Exception as e:
        logger.error(f"Aggregations failed: {e}")
        return GPUAggregations()


@router.post("/browse/topsis", response=TOPSISRankingResponse, auth=None)
async def calculate_topsis(
    request: HttpRequest,
    data: TOPSISRankingRequest,
):
    """
    Calculate TOPSIS ranking for specific GPU offers.

    TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution)
    is a multi-criteria decision analysis method that ranks alternatives based on
    their distance from ideal and anti-ideal solutions.

    Default criteria:
    - price_per_hour (cost - lower is better, weight: 0.40)
    - memory_gb (benefit - higher is better, weight: 0.35)
    - availability_score (benefit - higher is better, weight: 0.25)

    You can provide custom weights and criteria to adjust the ranking.
    """
    if len(data.offer_ids) < 2:
        raise HttpError(400, "Need at least 2 offers for TOPSIS ranking")

    if len(data.offer_ids) > 100:
        raise HttpError(400, "Maximum 100 offers for TOPSIS ranking")

    try:
        result = await get_topsis_ranking(
            offer_ids=data.offer_ids,
            custom_weights=data.weights,
            custom_criteria=data.criteria,
        )

        return TOPSISRankingResponse(**result)

    except Exception as e:
        logger.error(f"TOPSIS calculation failed: {e}")
        raise HttpError(500, "TOPSIS calculation failed")


@router.get("/browse/regions", auth=None)
async def list_regions(request: HttpRequest):
    """
    List all available regions with GPU offer counts.

    Returns regions sorted by offer count (most offers first).
    """
    from django.db.models import Count

    from .models import GPUOffer

    regions = []
    async for item in (
        GPUOffer.objects.values("region").annotate(count=Count("id")).order_by("-count")
    ):
        if item["region"]:
            regions.append(
                {
                    "region": item["region"],
                    "count": item["count"],
                }
            )

    return {"regions": regions}


@router.get("/browse/gpu-types", auth=None)
async def list_gpu_types(request: HttpRequest):
    """
    List all available GPU types with counts and memory ranges.

    Returns GPU types sorted by offer count (most offers first).
    """
    from django.db.models import Count, Max, Min

    from .models import GPUOffer

    gpu_types = []
    async for item in (
        GPUOffer.objects.values("gpu_type")
        .annotate(
            count=Count("id"),
            min_memory=Min("gpu_memory_gb"),
            max_memory=Max("gpu_memory_gb"),
        )
        .order_by("-count")
    ):
        if item["gpu_type"]:
            gpu_types.append(
                {
                    "gpu_type": item["gpu_type"],
                    "count": item["count"],
                    "memory_range": {
                        "min": item["min_memory"],
                        "max": item["max_memory"],
                    },
                }
            )

    return {"gpu_types": gpu_types}

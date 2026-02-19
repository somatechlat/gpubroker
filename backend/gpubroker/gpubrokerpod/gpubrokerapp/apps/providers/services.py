"""
Provider Services - Business logic for provider operations.

This module contains the core business logic for:
- Fetching and caching provider offers
- Managing provider integrations
- Rate limiting
- Browse GPU/Services with TOPSIS ranking
"""

import base64
import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

import numpy as np
from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache
from gpubrokerpod.gpubrokerapp.apps.auth_app.models import UserPreference
from gpubrokerpod.gpubrokerapp.apps.math_core.algorithms.topsis import TOPSISEngine

from .adapters.base import ProviderOffer
from .adapters.registry import ProviderRegistry
from .circuit_breaker import CircuitBreakerOpen, get_breaker
from .models import GPUOffer

logger = logging.getLogger("gpubroker.providers.services")

# Cache TTL in seconds
CACHE_TTL = 60


def _cache_key(path: str, params: dict[str, Any]) -> str:
    """Generate cache key from path and params."""
    base = path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v)
    return "providers:" + hashlib.sha256(base.encode()).hexdigest()


async def get_provider_api_key(
    provider_name: str, user_id: str | None = None
) -> str | None:
    """
    Get API key for a provider.

    Priority:
    1. User-specific config from database
    2. Environment variable fallback

    Args:
        provider_name: Provider identifier
        user_id: Optional user ID for user-specific config

    Returns:
        API key or None
    """
    # Try user-specific config first
    if user_id:
        try:
            pref = await sync_to_async(
                UserPreference.objects.filter(
                    user_id=user_id, preference_key=f"provider_config:{provider_name}"
                ).first
            )()

            if pref and pref.preference_value:
                config = json.loads(pref.preference_value)
                if config.get("api_key"):
                    return config["api_key"]
        except Exception as e:
            logger.warning(f"Failed to get user config for {provider_name}: {e}")

    # Fallback to environment variable
    import os

    env_key = os.getenv(f"{provider_name.upper()}_API_KEY")
    return env_key


async def fetch_offers_from_adapters(
    user_id: str | None = None,
) -> dict[str, list[dict]]:
    """
    Fetch offers from all registered provider adapters.

    Args:
        user_id: Optional user ID for user-specific API keys

    Returns:
        Dict mapping provider name to list of offer dicts
    """
    results: dict[str, list[dict]] = {}

    for name in ProviderRegistry.list_adapters():
        try:
            adapter = ProviderRegistry.get_adapter(name)
            auth_token = await get_provider_api_key(name, user_id)

            # Use circuit breaker for resilience
            breaker = get_breaker(name)
            offers: list[ProviderOffer] = await breaker.call(
                adapter.get_offers, auth_token
            )

            # Convert to dicts
            items = []
            for o in offers:
                item = {
                    "id": f"{o.provider}:{o.instance_type}:{o.region}",
                    "provider": o.provider,
                    "name": o.instance_type,
                    "gpu": o.instance_type,
                    "memory_gb": o.gpu_memory_gb,
                    "price_per_hour": o.price_per_hour,
                    "currency": "USD",
                    "availability": o.availability,
                    "region": o.region,
                    "tags": o.compliance_tags,
                    "last_updated": o.last_updated.isoformat(),
                }
                items.append(item)

            results[name] = items

        except CircuitBreakerOpen:
            logger.warning(f"Circuit breaker open for {name}")
            results[name] = []
        except Exception as e:
            logger.error(f"Adapter {name} failed: {e}")
            results[name] = []

    return results


async def list_offers_from_db(
    gpu_term: str | None = None,
    region: str | None = None,
    provider_name: str | None = None,
    availability: str | None = None,
    compliance_tag: str | None = None,
    gpu_memory_min: int | None = None,
    gpu_memory_max: int | None = None,
    price_min: float | None = None,
    max_price: float | None = None,
    page: int = 1,
    per_page: int = 20,
) -> dict[str, Any]:
    """
    List offers from database with filters.

    Args:
        gpu_term: Filter by GPU type (partial match)
        region: Filter by region (exact match)
        provider_name: Filter by provider (exact match)
        availability: Filter by availability status
        compliance_tag: Filter by compliance tag
        gpu_memory_min: Minimum GPU memory in GB
        gpu_memory_max: Maximum GPU memory in GB
        price_min: Minimum price per hour
        max_price: Maximum price per hour
        page: Page number (1-indexed)
        per_page: Items per page

    Returns:
        Dict with 'total' and 'items' keys
    """
    from django.db.models import Q

    # Build query
    queryset = GPUOffer.objects.select_related("provider").all()

    if gpu_term:
        queryset = queryset.filter(
            Q(gpu_type__icontains=gpu_term) | Q(name__icontains=gpu_term)
        )

    if region:
        queryset = queryset.filter(region=region)

    if provider_name:
        queryset = queryset.filter(provider__name=provider_name)

    if availability:
        queryset = queryset.filter(availability_status=availability)

    if compliance_tag:
        queryset = queryset.filter(compliance_tags__contains=[compliance_tag])

    if gpu_memory_min is not None:
        queryset = queryset.filter(gpu_memory_gb__gte=gpu_memory_min)

    if gpu_memory_max is not None:
        queryset = queryset.filter(gpu_memory_gb__lte=gpu_memory_max)

    if price_min is not None:
        queryset = queryset.filter(price_per_hour__gte=price_min)

    if max_price is not None:
        queryset = queryset.filter(price_per_hour__lte=max_price)

    # Get total count using Django's native async ORM
    total = await queryset.acount()

    # Paginate using Django's native async iteration
    offset = (page - 1) * per_page
    offers = [
        offer
        async for offer in queryset.order_by("-updated_at")[offset : offset + per_page]
    ]

    # Convert to dicts
    items = []
    for offer in offers:
        items.append(
            {
                "id": str(offer.id),
                "provider": offer.provider.name if offer.provider else "unknown",
                "name": offer.name or offer.gpu_type,
                "gpu": offer.gpu_type,
                "memory_gb": offer.gpu_memory_gb or 0,
                "price_per_hour": float(offer.price_per_hour),
                "currency": offer.currency,
                "availability": offer.availability_status,
                "region": offer.region,
                "tags": offer.compliance_tags or [],
                "last_updated": (
                    offer.last_updated.isoformat() if offer.last_updated else None
                ),
            }
        )

    return {"total": total, "items": items}


async def get_cached_offers(
    filters: dict[str, Any],
    user_id: str | None = None,
) -> dict[str, Any] | None:
    """
    Get cached offers if available.

    Args:
        filters: Filter parameters
        user_id: User ID for cache key

    Returns:
        Cached response or None
    """
    key = _cache_key("/providers", {**filters, "user_id": user_id or ""})
    cached = cache.get(key)
    if cached:
        return json.loads(cached)
    return None


async def cache_offers(
    filters: dict[str, Any],
    response: dict[str, Any],
    user_id: str | None = None,
) -> None:
    """
    Cache offers response.

    Args:
        filters: Filter parameters
        response: Response to cache
        user_id: User ID for cache key
    """
    key = _cache_key("/providers", {**filters, "user_id": user_id or ""})
    cache.set(key, json.dumps(response, default=str), CACHE_TTL)


async def save_integration_config(
    user_id: str,
    provider: str,
    api_key: str | None = None,
    api_url: str | None = None,
) -> bool:
    """
    Save provider integration configuration.

    Args:
        user_id: User ID
        provider: Provider name
        api_key: API key
        api_url: Optional API URL override

    Returns:
        True if saved successfully
    """
    # Validate credentials if provided
    if api_key:
        try:
            adapter = ProviderRegistry.get_adapter(provider)
            is_valid = await adapter.validate_credentials({"api_key": api_key})
            if not is_valid:
                return False
        except ValueError:
            logger.warning(f"Unknown provider: {provider}")
            return False
        except Exception as e:
            logger.error(f"Credential validation failed: {e}")
            return False

    # Save to database
    config = {
        "provider": provider,
        "api_key": api_key,
        "api_url": api_url,
    }

    try:
        pref, created = await sync_to_async(UserPreference.objects.update_or_create)(
            user_id=user_id,
            preference_key=f"provider_config:{provider}",
            defaults={"preference_value": json.dumps(config)},
        )
        return True
    except Exception as e:
        logger.error(f"Failed to save integration config: {e}")
        return False


async def list_integrations(user_id: str) -> list[dict[str, Any]]:
    """
    List all provider integrations and their status.

    Args:
        user_id: User ID

    Returns:
        List of integration status dicts
    """
    statuses = []

    # Get saved configs
    saved_configs: dict[str, dict] = {}
    try:
        prefs = await sync_to_async(list)(
            UserPreference.objects.filter(
                user_id=user_id, preference_key__startswith="provider_config:"
            )
        )
        for pref in prefs:
            provider = pref.preference_key.split(":")[1]
            saved_configs[provider] = json.loads(pref.preference_value)
    except Exception as e:
        logger.error(f"Failed to fetch configs: {e}")

    # Check all adapters
    for name in ProviderRegistry.list_adapters():
        config = saved_configs.get(name)
        api_key = config.get("api_key") if config else None

        if not api_key:
            api_key = await get_provider_api_key(name)

        status = "not_configured"
        message = None

        if api_key:
            try:
                adapter = ProviderRegistry.get_adapter(name)
                is_valid = await adapter.validate_credentials({"api_key": api_key})
                status = "active" if is_valid else "error"
                if not is_valid:
                    message = "Validation failed"
            except Exception as e:
                status = "error"
                message = str(e)

        statuses.append(
            {
                "provider": name,
                "status": status,
                "message": message,
                "last_checked": datetime.now(timezone.utc).isoformat(),
            }
        )

    return statuses


class RateLimiter:
    """
    Simple in-memory rate limiter.

    For production, use Redis-backed rate limiting.
    """

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: dict[str, tuple[int, float]] = {}

    def allow(self, key: str) -> bool:
        """Check if request is allowed."""
        import time

        now = time.time()
        count, start = self._hits.get(key, (0, now))

        if now - start >= self.window:
            # Reset window
            self._hits[key] = (1, now)
            return True

        if count < self.limit:
            self._hits[key] = (count + 1, start)
            return True

        return False


# Rate limiters per plan
_limiters: dict[str, RateLimiter] = {}


def get_rate_limiter(plan: str) -> RateLimiter:
    """Get rate limiter for a plan."""
    if plan not in _limiters:
        limits = getattr(
            settings,
            "RATE_LIMITS",
            {
                "free": 10,
                "pro": 100,
                "enterprise": 1000,
            },
        )
        limit = limits.get(plan, 20)
        _limiters[plan] = RateLimiter(limit=limit, window_seconds=60)
    return _limiters[plan]


# Featured offers cache TTL (60 seconds as per requirements)
FEATURED_CACHE_TTL = 60


async def get_cached_featured_offers(limit: int) -> dict[str, Any] | None:
    """
    Get cached featured offers if available.

    Args:
        limit: Number of featured items

    Returns:
        Cached response or None
    """
    key = f"providers:featured:{limit}"
    cached = cache.get(key)
    if cached:
        return json.loads(cached)
    return None


async def cache_featured_offers(limit: int, response: dict[str, Any]) -> None:
    """
    Cache featured offers response.

    Args:
        limit: Number of featured items
        response: Response to cache
    """
    key = f"providers:featured:{limit}"
    cache.set(key, json.dumps(response, default=str), FEATURED_CACHE_TTL)


async def get_featured_offers(limit: int = 6) -> dict[str, Any]:
    """
    Get featured GPU offers for landing page.

    Selects top offers based on:
    1. Availability (prioritize available GPUs)
    2. Value score (price/performance ratio)
    3. Provider diversity (show different providers)

    Args:
        limit: Maximum number of offers to return

    Returns:
        Dict with featured items and metadata
    """
    # Provider logo mapping
    provider_logos = {
        "runpod": "https://gpubroker.live/images/providers/runpod.svg",
        "vastai": "https://gpubroker.live/images/providers/vastai.svg",
        "lambdalabs": "https://gpubroker.live/images/providers/lambdalabs.svg",
        "paperspace": "https://gpubroker.live/images/providers/paperspace.svg",
        "coreweave": "https://gpubroker.live/images/providers/coreweave.svg",
        "aws": "https://gpubroker.live/images/providers/aws.svg",
        "azure": "https://gpubroker.live/images/providers/azure.svg",
        "gcp": "https://gpubroker.live/images/providers/gcp.svg",
    }

    # GPU use case mapping
    gpu_use_cases = {
        "A100": ["training", "inference", "research"],
        "H100": ["training", "inference", "research"],
        "A6000": ["training", "rendering", "inference"],
        "RTX 4090": ["inference", "rendering", "gaming"],
        "RTX 3090": ["inference", "rendering", "gaming"],
        "V100": ["training", "inference"],
        "T4": ["inference", "development"],
        "L4": ["inference", "video"],
        "A10": ["inference", "rendering"],
    }

    def get_best_for(gpu_type: str) -> list[str]:
        """Get use cases for a GPU type."""
        for key, uses in gpu_use_cases.items():
            if key.lower() in gpu_type.lower():
                return uses
        return ["general"]

    def get_availability_score(status: str) -> int:
        """Convert availability status to score (0-100)."""
        scores = {
            "available": 100,
            "limited": 70,
            "busy": 30,
            "unavailable": 0,
        }
        return scores.get(status.lower(), 50)

    # Try database first
    try:
        queryset = (
            GPUOffer.objects.select_related("provider")
            .filter(availability_status__in=["available", "limited"])
            .order_by("price_per_hour")
        )

        total_gpus = await queryset.acount()

        # Get unique providers count
        provider_ids = set()
        async for offer in queryset.values("provider_id").distinct()[:20]:
            provider_ids.add(offer["provider_id"])
        total_providers = len(provider_ids)

        # Get featured offers with provider diversity
        featured_items = []
        seen_providers = set()

        async for offer in queryset[:50]:  # Get more to ensure diversity
            provider_name = offer.provider.name if offer.provider else "unknown"

            # Ensure provider diversity (max 2 per provider)
            if seen_providers.get(provider_name, 0) >= 2:
                continue

            seen_providers[provider_name] = seen_providers.get(provider_name, 0) + 1

            featured_items.append(
                {
                    "id": str(offer.id),
                    "provider": provider_name,
                    "provider_logo": provider_logos.get(provider_name.lower()),
                    "name": offer.name or offer.gpu_type,
                    "gpu": offer.gpu_type,
                    "memory_gb": offer.gpu_memory_gb or 0,
                    "price_per_hour": float(offer.price_per_hour),
                    "currency": offer.currency,
                    "availability": offer.availability_status,
                    "availability_score": get_availability_score(
                        offer.availability_status
                    ),
                    "region": offer.region,
                    "performance_score": None,  # TOPSIS score if available
                    "best_for": get_best_for(offer.gpu_type),
                }
            )

            if len(featured_items) >= limit:
                break

        return {
            "items": featured_items,
            "total_providers": total_providers,
            "total_gpus": total_gpus,
        }

    except Exception as e:
        logger.warning(f"Database query failed for featured: {e}")

    # Fallback to live adapters
    try:
        all_results = await fetch_offers_from_adapters(None)

        # Flatten and sort by price
        flat = []
        providers_seen = set()

        for provider_name, items in all_results.items():
            providers_seen.add(provider_name)
            for item in items:
                if item.get("availability", "").lower() in ["available", "limited"]:
                    item["provider_logo"] = provider_logos.get(provider_name.lower())
                    item["availability_score"] = get_availability_score(
                        item.get("availability", "")
                    )
                    item["best_for"] = get_best_for(item.get("gpu", ""))
                    flat.append(item)

        # Sort by price
        flat.sort(key=lambda x: x.get("price_per_hour", float("inf")))

        # Select with provider diversity
        featured_items = []
        provider_counts: dict[str, int] = {}

        for item in flat:
            provider = item.get("provider", "")
            if provider_counts.get(provider, 0) >= 2:
                continue

            provider_counts[provider] = provider_counts.get(provider, 0) + 1
            featured_items.append(item)

            if len(featured_items) >= limit:
                break

        return {
            "items": featured_items,
            "total_providers": len(providers_seen),
            "total_gpus": len(flat),
        }

    except Exception as e:
        logger.error(f"Failed to fetch featured from adapters: {e}")
        return {
            "items": [],
            "total_providers": 0,
            "total_gpus": 0,
        }


# ============================================
# Browse GPU/Services (Task 13)
# ============================================

# Browse cache TTL (30 seconds for real-time feel)
BROWSE_CACHE_TTL = 30


async def get_cached_browse_results(
    filters: dict[str, Any],
    sort_field: str,
    sort_direction: str,
    cursor: str | None,
    limit: int,
) -> dict[str, Any] | None:
    """Get cached browse results if available."""
    key = _cache_key(
        "/browse",
        {
            **filters,
            "sort": f"{sort_field}:{sort_direction}",
            "cursor": cursor or "",
            "limit": limit,
        },
    )
    cached = cache.get(key)
    if cached:
        return json.loads(cached)
    return None


async def cache_browse_results(
    filters: dict[str, Any],
    sort_field: str,
    sort_direction: str,
    cursor: str | None,
    limit: int,
    response: dict[str, Any],
) -> None:
    """Cache browse results."""
    key = _cache_key(
        "/browse",
        {
            **filters,
            "sort": f"{sort_field}:{sort_direction}",
            "cursor": cursor or "",
            "limit": limit,
        },
    )
    cache.set(key, json.dumps(response, default=str), BROWSE_CACHE_TTL)


def encode_cursor(offer_id: str, sort_value: Any, page: int) -> str:
    """Encode cursor for pagination."""
    data = json.dumps({"id": offer_id, "val": str(sort_value), "page": page})
    return base64.b64encode(data.encode()).decode()


def decode_cursor(cursor: str) -> dict[str, Any]:
    """Decode cursor from pagination."""
    try:
        data = base64.b64decode(cursor.encode()).decode()
        return json.loads(data)
    except Exception:
        return {"id": None, "val": None, "page": 1}


async def browse_gpu_offers(
    filters: dict[str, Any],
    sort_field: str = "price_per_hour",
    sort_direction: str = "asc",
    cursor: str | None = None,
    limit: int = 20,
    include_topsis: bool = True,
) -> dict[str, Any]:
    """
    Browse GPU offers with advanced filtering, sorting, and TOPSIS ranking.

    Args:
        filters: Filter parameters
        sort_field: Field to sort by
        sort_direction: asc or desc
        cursor: Pagination cursor
        limit: Items per page
        include_topsis: Whether to calculate TOPSIS scores

    Returns:
        Dict with items, pagination, aggregations
    """
    from django.db.models import Q

    # Provider logo mapping
    provider_logos = {
        "runpod": "https://gpubroker.live/images/providers/runpod.svg",
        "vastai": "https://gpubroker.live/images/providers/vastai.svg",
        "lambdalabs": "https://gpubroker.live/images/providers/lambdalabs.svg",
        "paperspace": "https://gpubroker.live/images/providers/paperspace.svg",
        "coreweave": "https://gpubroker.live/images/providers/coreweave.svg",
        "aws": "https://gpubroker.live/images/providers/aws.svg",
        "azure": "https://gpubroker.live/images/providers/azure.svg",
        "gcp": "https://gpubroker.live/images/providers/gcp.svg",
    }

    # GPU use case mapping
    gpu_use_cases = {
        "A100": ["training", "inference", "research"],
        "H100": ["training", "inference", "research"],
        "A6000": ["training", "rendering", "inference"],
        "RTX 4090": ["inference", "rendering", "gaming"],
        "RTX 3090": ["inference", "rendering", "gaming"],
        "V100": ["training", "inference"],
        "T4": ["inference", "development"],
        "L4": ["inference", "video"],
        "A10": ["inference", "rendering"],
    }

    def get_best_for(gpu_type: str) -> list[str]:
        for key, uses in gpu_use_cases.items():
            if key.lower() in gpu_type.lower():
                return uses
        return ["general"]

    def get_availability_score(status: str) -> int:
        scores = {"available": 100, "limited": 70, "busy": 30, "unavailable": 0}
        return scores.get(status.lower(), 50)

    # Build query
    queryset = GPUOffer.objects.select_related("provider").all()
    filters_applied = {}

    # Apply filters
    if filters.get("gpu_type"):
        queryset = queryset.filter(
            Q(gpu_type__icontains=filters["gpu_type"])
            | Q(name__icontains=filters["gpu_type"])
        )
        filters_applied["gpu_type"] = filters["gpu_type"]

    if filters.get("gpu_model"):
        queryset = queryset.filter(gpu_type=filters["gpu_model"])
        filters_applied["gpu_model"] = filters["gpu_model"]

    if filters.get("memory_min") is not None:
        queryset = queryset.filter(gpu_memory_gb__gte=filters["memory_min"])
        filters_applied["memory_min"] = filters["memory_min"]

    if filters.get("memory_max") is not None:
        queryset = queryset.filter(gpu_memory_gb__lte=filters["memory_max"])
        filters_applied["memory_max"] = filters["memory_max"]

    if filters.get("price_min") is not None:
        queryset = queryset.filter(price_per_hour__gte=filters["price_min"])
        filters_applied["price_min"] = filters["price_min"]

    if filters.get("price_max") is not None:
        queryset = queryset.filter(price_per_hour__lte=filters["price_max"])
        filters_applied["price_max"] = filters["price_max"]

    if filters.get("spot_only"):
        queryset = queryset.filter(spot_pricing=True)
        filters_applied["spot_only"] = True

    if filters.get("provider"):
        queryset = queryset.filter(provider__name=filters["provider"])
        filters_applied["provider"] = filters["provider"]

    if filters.get("providers"):
        queryset = queryset.filter(provider__name__in=filters["providers"])
        filters_applied["providers"] = filters["providers"]

    if filters.get("region"):
        queryset = queryset.filter(region=filters["region"])
        filters_applied["region"] = filters["region"]

    if filters.get("regions"):
        queryset = queryset.filter(region__in=filters["regions"])
        filters_applied["regions"] = filters["regions"]

    if filters.get("availability"):
        queryset = queryset.filter(availability_status=filters["availability"])
        filters_applied["availability"] = filters["availability"]

    if filters.get("available_only"):
        queryset = queryset.filter(availability_status__in=["available", "limited"])
        filters_applied["available_only"] = True

    if filters.get("compliance_tags"):
        for tag in filters["compliance_tags"]:
            queryset = queryset.filter(compliance_tags__contains=[tag])
        filters_applied["compliance_tags"] = filters["compliance_tags"]

    if filters.get("min_cpu_cores") is not None:
        queryset = queryset.filter(cpu_cores__gte=filters["min_cpu_cores"])
        filters_applied["min_cpu_cores"] = filters["min_cpu_cores"]

    if filters.get("min_ram_gb") is not None:
        queryset = queryset.filter(ram_gb__gte=filters["min_ram_gb"])
        filters_applied["min_ram_gb"] = filters["min_ram_gb"]

    if filters.get("min_storage_gb") is not None:
        queryset = queryset.filter(storage_gb__gte=filters["min_storage_gb"])
        filters_applied["min_storage_gb"] = filters["min_storage_gb"]

    # Get total count
    total = await queryset.acount()

    # Calculate aggregations for filter facets
    aggregations = await _calculate_aggregations(queryset, provider_logos)

    # Apply sorting
    sort_map = {
        "price": "price_per_hour",
        "price_per_hour": "price_per_hour",
        "memory": "gpu_memory_gb",
        "availability": "availability_status",
        "region": "region",
        "provider": "provider__name",
        "updated": "updated_at",
    }

    db_sort_field = sort_map.get(sort_field, "price_per_hour")
    if sort_direction == "desc":
        db_sort_field = f"-{db_sort_field}"

    queryset = queryset.order_by(db_sort_field)

    # Handle cursor-based pagination
    page = 1
    if cursor:
        cursor_data = decode_cursor(cursor)
        page = cursor_data.get("page", 1)

    offset = (page - 1) * limit

    # Fetch items
    offers = [offer async for offer in queryset[offset : offset + limit + 1]]

    has_next = len(offers) > limit
    if has_next:
        offers = offers[:limit]

    has_prev = page > 1

    # Convert to response items
    items = []
    for offer in offers:
        provider_name = offer.provider.name if offer.provider else "unknown"
        price_per_hour = float(offer.price_per_hour)

        items.append(
            {
                "id": str(offer.id),
                "provider": provider_name,
                "provider_logo": provider_logos.get(provider_name.lower()),
                "name": offer.name or offer.gpu_type,
                "gpu_type": offer.gpu_type,
                "gpu_model": offer.gpu_type,
                "memory_gb": offer.gpu_memory_gb or 0,
                "cpu_cores": offer.cpu_cores or 0,
                "ram_gb": offer.ram_gb or 0,
                "storage_gb": offer.storage_gb or 0,
                "storage_type": offer.storage_type or "SSD",
                "price_per_hour": price_per_hour,
                "price_per_day": round(price_per_hour * 24, 2),
                "price_per_month": round(price_per_hour * 24 * 30, 2),
                "currency": offer.currency,
                "availability": offer.availability_status,
                "availability_score": get_availability_score(offer.availability_status),
                "region": offer.region,
                "availability_zone": offer.availability_zone,
                "spot_pricing": offer.spot_pricing,
                "preemptible": offer.preemptible,
                "min_rental_hours": (
                    offer.min_rental_time / 60 if offer.min_rental_time else 1.0
                ),
                "max_rental_hours": (
                    offer.max_rental_time / 60 if offer.max_rental_time else None
                ),
                "network_speed_gbps": (
                    float(offer.network_speed_gbps)
                    if offer.network_speed_gbps
                    else None
                ),
                "sla_uptime": float(offer.sla_uptime) if offer.sla_uptime else None,
                "compliance_tags": offer.compliance_tags or [],
                "topsis_score": None,
                "topsis_rank": None,
                "best_for": get_best_for(offer.gpu_type),
                "last_updated": offer.last_updated,
            }
        )

    # Calculate TOPSIS scores if requested
    if include_topsis and len(items) >= 2:
        items = await calculate_topsis_rankings(items)

    # Build pagination
    next_cursor = None
    prev_cursor = None

    if has_next and items:
        last_item = items[-1]
        next_cursor = encode_cursor(
            last_item["id"], last_item.get(sort_field, ""), page + 1
        )

    if has_prev:
        prev_cursor = encode_cursor("", "", page - 1)

    pagination = {
        "cursor": cursor,
        "limit": limit,
        "has_next": has_next,
        "has_prev": has_prev,
        "next_cursor": next_cursor,
        "prev_cursor": prev_cursor,
        "total": total,
    }

    sort_applied = {
        "field": sort_field,
        "direction": sort_direction,
    }

    return {
        "items": items,
        "pagination": pagination,
        "filters_applied": filters_applied,
        "sort_applied": sort_applied,
        "aggregations": aggregations,
        "last_updated": datetime.now(timezone.utc),
        "cache_ttl": BROWSE_CACHE_TTL,
    }


async def _calculate_aggregations(
    queryset, provider_logos: dict[str, str]
) -> dict[str, Any]:
    """Calculate aggregations for filter facets."""
    from django.db.models import Avg, Count, Max, Min

    aggregations = {
        "providers": [],
        "regions": [],
        "gpu_types": [],
        "price_range": {},
        "memory_range": {},
        "availability_counts": {},
        "compliance_tags": [],
    }

    try:
        # Provider counts
        provider_counts = {}
        async for item in queryset.values("provider__name").annotate(count=Count("id")):
            name = item["provider__name"]
            if name:
                provider_counts[name] = item["count"]

        aggregations["providers"] = [
            {"name": name, "count": count, "logo": provider_logos.get(name.lower())}
            for name, count in sorted(provider_counts.items(), key=lambda x: -x[1])
        ]

        # Region counts
        region_counts = {}
        async for item in queryset.values("region").annotate(count=Count("id")):
            region = item["region"]
            if region:
                region_counts[region] = item["count"]

        aggregations["regions"] = [
            {"name": name, "count": count}
            for name, count in sorted(region_counts.items(), key=lambda x: -x[1])
        ]

        # GPU type counts
        gpu_counts = {}
        async for item in queryset.values("gpu_type").annotate(
            count=Count("id"),
            min_memory=Min("gpu_memory_gb"),
            max_memory=Max("gpu_memory_gb"),
        ):
            gpu_type = item["gpu_type"]
            if gpu_type:
                gpu_counts[gpu_type] = {
                    "count": item["count"],
                    "memory_range": [item["min_memory"], item["max_memory"]],
                }

        aggregations["gpu_types"] = [
            {"name": name, "count": data["count"], "memory_range": data["memory_range"]}
            for name, data in sorted(gpu_counts.items(), key=lambda x: -x[1]["count"])
        ]

        # Price range
        price_stats = await queryset.aaggregate(
            min_price=Min("price_per_hour"),
            max_price=Max("price_per_hour"),
            avg_price=Avg("price_per_hour"),
        )
        aggregations["price_range"] = {
            "min": float(price_stats["min_price"] or 0),
            "max": float(price_stats["max_price"] or 0),
            "avg": float(price_stats["avg_price"] or 0),
        }

        # Memory range
        memory_stats = await queryset.aaggregate(
            min_memory=Min("gpu_memory_gb"), max_memory=Max("gpu_memory_gb")
        )
        aggregations["memory_range"] = {
            "min": memory_stats["min_memory"] or 0,
            "max": memory_stats["max_memory"] or 0,
        }

        # Availability counts
        avail_counts = {}
        async for item in queryset.values("availability_status").annotate(
            count=Count("id")
        ):
            status = item["availability_status"]
            if status:
                avail_counts[status] = item["count"]
        aggregations["availability_counts"] = avail_counts

    except Exception as e:
        logger.warning(f"Failed to calculate aggregations: {e}")

    return aggregations


async def calculate_topsis_rankings(
    items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """
    Calculate TOPSIS rankings for GPU offers.

    Criteria:
    - price_per_hour (cost - lower is better)
    - memory_gb (benefit - higher is better)
    - availability_score (benefit - higher is better)
    - performance estimate based on GPU type (benefit)
    """
    if len(items) < 2:
        return items

    # Performance estimates based on GPU type
    performance_estimates = {
        "H100": 100,
        "A100": 80,
        "L40": 75,
        "A6000": 70,
        "RTX 4090": 65,
        "RTX 4080": 55,
        "A10": 50,
        "RTX 3090": 45,
        "RTX 3080": 40,
        "V100": 35,
        "T4": 25,
        "L4": 30,
        "RTX 3070": 30,
    }

    def get_performance_score(gpu_type: str) -> float:
        gpu_upper = gpu_type.upper()
        for key, score in performance_estimates.items():
            if key.upper() in gpu_upper:
                return float(score)
        return 30.0  # Default

    # Build decision matrix
    n_items = len(items)
    n_criteria = 4  # price, memory, availability, performance

    matrix = np.zeros((n_items, n_criteria), dtype=np.float64)

    for i, item in enumerate(items):
        matrix[i, 0] = item.get("price_per_hour", 1.0)
        matrix[i, 1] = item.get("memory_gb", 8)
        matrix[i, 2] = item.get("availability_score", 50)
        matrix[i, 3] = get_performance_score(item.get("gpu_type", ""))

    # TOPSIS configuration
    weights = [0.35, 0.25, 0.20, 0.20]  # price, memory, availability, performance
    criteria_types = ["cost", "benefit", "benefit", "benefit"]

    try:
        engine = TOPSISEngine()
        result = engine.calculate(matrix, weights, criteria_types)

        # Apply scores and ranks to items
        for i, item in enumerate(items):
            item["topsis_score"] = round(result["scores"][i], 4)
            item["topsis_rank"] = result["rankings"].index(i) + 1

        # Sort by TOPSIS rank
        items.sort(key=lambda x: x.get("topsis_rank", 999))

    except Exception as e:
        logger.warning(f"TOPSIS calculation failed: {e}")

    return items


async def get_topsis_ranking(
    offer_ids: list[str],
    custom_weights: dict[str, float] | None = None,
    custom_criteria: list[str] | None = None,
) -> dict[str, Any]:
    """
    Calculate TOPSIS ranking for specific offers.

    Args:
        offer_ids: List of offer IDs to rank
        custom_weights: Optional custom weights for criteria
        custom_criteria: Optional custom criteria list

    Returns:
        Dict with rankings, ideal/anti-ideal solutions
    """
    # Fetch offers
    offers = []
    async for offer in GPUOffer.objects.select_related("provider").filter(
        id__in=offer_ids
    ):
        offers.append(
            {
                "id": str(offer.id),
                "price_per_hour": float(offer.price_per_hour),
                "memory_gb": offer.gpu_memory_gb or 0,
                "availability_score": {"available": 100, "limited": 70, "busy": 30}.get(
                    offer.availability_status, 50
                ),
                "gpu_type": offer.gpu_type,
            }
        )

    if len(offers) < 2:
        return {
            "rankings": [
                {"offer_id": o["id"], "score": 1.0, "rank": 1} for o in offers
            ],
            "ideal_solution": {},
            "anti_ideal_solution": {},
            "criteria_used": [],
            "weights_used": {},
        }

    # Default criteria and weights
    criteria = custom_criteria or ["price_per_hour", "memory_gb", "availability_score"]
    weights = custom_weights or {
        "price_per_hour": 0.4,
        "memory_gb": 0.35,
        "availability_score": 0.25,
    }

    # Normalize weights
    weight_sum = sum(weights.values())
    weights = {k: v / weight_sum for k, v in weights.items()}

    # Build matrix
    n_offers = len(offers)
    n_criteria = len(criteria)
    matrix = np.zeros((n_offers, n_criteria), dtype=np.float64)

    for i, offer in enumerate(offers):
        for j, criterion in enumerate(criteria):
            matrix[i, j] = float(offer.get(criterion, 0))

    # Criteria types (price is cost, others are benefit)
    criteria_types = ["cost" if "price" in c else "benefit" for c in criteria]
    weight_list = [weights.get(c, 0.25) for c in criteria]

    try:
        engine = TOPSISEngine()
        result = engine.calculate(matrix, weight_list, criteria_types)

        rankings = []
        for i, offer in enumerate(offers):
            rankings.append(
                {
                    "offer_id": offer["id"],
                    "score": round(result["scores"][i], 4),
                    "rank": result["rankings"].index(i) + 1,
                }
            )

        rankings.sort(key=lambda x: x["rank"])

        return {
            "rankings": rankings,
            "ideal_solution": dict(zip(criteria, result["ideal_solution"])),
            "anti_ideal_solution": dict(zip(criteria, result["anti_ideal_solution"])),
            "criteria_used": criteria,
            "weights_used": weights,
        }

    except Exception as e:
        logger.error(f"TOPSIS ranking failed: {e}")
        return {
            "rankings": [
                {"offer_id": o["id"], "score": 0.5, "rank": i + 1}
                for i, o in enumerate(offers)
            ],
            "ideal_solution": {},
            "anti_ideal_solution": {},
            "criteria_used": criteria,
            "weights_used": weights,
        }

"""
Provider Services - Business logic for provider operations.

This module contains the core business logic for:
- Fetching and caching provider offers
- Managing provider integrations
- Rate limiting
"""
import json
import hashlib
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple, Any

from django.conf import settings
from django.core.cache import cache
from asgiref.sync import sync_to_async

from .models import Provider, GPUOffer, ProviderHealthCheck
from .adapters.registry import ProviderRegistry
from .adapters.base import ProviderOffer
from .circuit_breaker import get_breaker, CircuitBreakerOpen
from apps.auth_app.models import UserPreference

logger = logging.getLogger('gpubroker.providers.services')

# Cache TTL in seconds
CACHE_TTL = 60


def _cache_key(path: str, params: Dict[str, Any]) -> str:
    """Generate cache key from path and params."""
    base = path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v)
    return "providers:" + hashlib.sha256(base.encode()).hexdigest()


async def get_provider_api_key(provider_name: str, user_id: Optional[str] = None) -> Optional[str]:
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
            pref = await sync_to_async(UserPreference.objects.filter(
                user_id=user_id,
                preference_key=f"provider_config:{provider_name}"
            ).first)()
            
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
    user_id: Optional[str] = None
) -> Dict[str, List[Dict]]:
    """
    Fetch offers from all registered provider adapters.
    
    Args:
        user_id: Optional user ID for user-specific API keys
        
    Returns:
        Dict mapping provider name to list of offer dicts
    """
    results: Dict[str, List[Dict]] = {}
    
    for name in ProviderRegistry.list_adapters():
        try:
            adapter = ProviderRegistry.get_adapter(name)
            auth_token = await get_provider_api_key(name, user_id)
            
            # Use circuit breaker for resilience
            breaker = get_breaker(name)
            offers: List[ProviderOffer] = await breaker.call(
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
    gpu_term: Optional[str] = None,
    region: Optional[str] = None,
    provider_name: Optional[str] = None,
    availability: Optional[str] = None,
    compliance_tag: Optional[str] = None,
    gpu_memory_min: Optional[int] = None,
    gpu_memory_max: Optional[int] = None,
    price_min: Optional[float] = None,
    max_price: Optional[float] = None,
    page: int = 1,
    per_page: int = 20,
) -> Dict[str, Any]:
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
    queryset = GPUOffer.objects.select_related('provider').all()
    
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
    offers = [offer async for offer in queryset.order_by('-updated_at')[offset:offset + per_page]]
    
    # Convert to dicts
    items = []
    for offer in offers:
        items.append({
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
            "last_updated": offer.last_updated.isoformat() if offer.last_updated else None,
        })
    
    return {"total": total, "items": items}


async def get_cached_offers(
    filters: Dict[str, Any],
    user_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
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
    filters: Dict[str, Any],
    response: Dict[str, Any],
    user_id: Optional[str] = None,
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
    api_key: Optional[str] = None,
    api_url: Optional[str] = None,
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
            defaults={"preference_value": json.dumps(config)}
        )
        return True
    except Exception as e:
        logger.error(f"Failed to save integration config: {e}")
        return False


async def list_integrations(user_id: str) -> List[Dict[str, Any]]:
    """
    List all provider integrations and their status.
    
    Args:
        user_id: User ID
        
    Returns:
        List of integration status dicts
    """
    statuses = []
    
    # Get saved configs
    saved_configs: Dict[str, Dict] = {}
    try:
        prefs = await sync_to_async(list)(
            UserPreference.objects.filter(
                user_id=user_id,
                preference_key__startswith="provider_config:"
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
        
        statuses.append({
            "provider": name,
            "status": status,
            "message": message,
            "last_checked": datetime.now(timezone.utc).isoformat(),
        })
    
    return statuses


class RateLimiter:
    """
    Simple in-memory rate limiter.
    
    For production, use Redis-backed rate limiting.
    """
    
    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: Dict[str, Tuple[int, float]] = {}
    
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
_limiters: Dict[str, RateLimiter] = {}


def get_rate_limiter(plan: str) -> RateLimiter:
    """Get rate limiter for a plan."""
    if plan not in _limiters:
        limits = getattr(settings, 'RATE_LIMITS', {
            'free': 10,
            'pro': 100,
            'enterprise': 1000,
        })
        limit = limits.get(plan, 20)
        _limiters[plan] = RateLimiter(limit=limit, window_seconds=60)
    return _limiters[plan]

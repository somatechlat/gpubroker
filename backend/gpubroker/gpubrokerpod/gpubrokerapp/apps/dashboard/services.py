"""
Dashboard Services - Business logic for dashboard data.
"""
import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Dict, List, Optional, Any

from django.core.cache import cache
from asgiref.sync import sync_to_async

logger = logging.getLogger('gpubroker.dashboard.services')

# Cache TTL
DASHBOARD_CACHE_TTL = 30  # 30 seconds for real-time feel


async def get_user_dashboard(user_id: str) -> Dict[str, Any]:
    """
    Get complete dashboard data for a user.
    
    Args:
        user_id: User UUID
        
    Returns:
        Dashboard data dict
    """
    # Check cache
    cache_key = f"dashboard:{user_id}"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Gather all dashboard data
    quick_stats = await get_quick_stats(user_id)
    pods = await get_user_pods(user_id)
    billing = await get_billing_summary(user_id)
    activity = await get_recent_activity(user_id)
    provider_health = await get_provider_health()
    
    dashboard = {
        "quick_stats": quick_stats,
        "pods": pods,
        "billing": billing,
        "recent_activity": activity,
        "provider_health": provider_health,
    }
    
    # Cache the result
    cache.set(cache_key, dashboard, DASHBOARD_CACHE_TTL)
    
    return dashboard


async def get_quick_stats(user_id: str) -> Dict[str, Any]:
    """Get quick stats for dashboard header."""
    # Import here to avoid circular imports
    from gpubrokerpod.gpubrokerapp.apps.billing.models import Subscription, UsageRecord
    
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Get user's subscription
    subscription = await sync_to_async(
        Subscription.objects.select_related('plan').filter(
            user_id=user_id,
            status__in=['active', 'trialing']
        ).first
    )()
    
    # Count pods (mock for now - would come from pod management)
    active_pods = 0
    total_pods = 0
    
    # Calculate month spend from usage records
    month_spend = Decimal('0.00')
    if subscription:
        usage_records = UsageRecord.objects.filter(
            user_id=user_id,
            recorded_at__gte=month_start,
        )
        async for record in usage_records:
            month_spend += record.quantity * record.unit_price
    
    # API calls today
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    api_calls_today = 0
    if subscription:
        api_calls = await sync_to_async(
            UsageRecord.objects.filter(
                user_id=user_id,
                usage_type='api_call',
                recorded_at__gte=today_start,
            ).count
        )()
        api_calls_today = api_calls
    
    return {
        "active_pods": active_pods,
        "total_pods": total_pods,
        "month_spend": float(month_spend),
        "month_budget": None,  # Could be set by user
        "api_calls_today": api_calls_today,
        "savings_percentage": 0.0,  # Calculate based on market comparison
    }


async def get_user_pods(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get user's pods.
    
    For now returns empty list - will be populated when pod management is implemented.
    """
    # TODO: Implement when pod management models are created
    return []


async def get_billing_summary(user_id: str) -> Dict[str, Any]:
    """Get billing summary for dashboard."""
    from gpubrokerpod.gpubrokerapp.apps.billing.models import Subscription
    
    subscription = await sync_to_async(
        Subscription.objects.select_related('plan').filter(
            user_id=user_id,
            status__in=['active', 'trialing']
        ).first
    )()
    
    if not subscription:
        return {
            "current_plan": "Free",
            "plan_tier": "free",
            "monthly_cost": 0.0,
            "next_billing_date": None,
            "tokens_used": 0,
            "tokens_limit": 1000,
            "tokens_remaining": 1000,
        }
    
    return {
        "current_plan": subscription.plan.name,
        "plan_tier": subscription.plan.tier,
        "monthly_cost": float(subscription.plan.price_monthly),
        "next_billing_date": subscription.current_period_end,
        "tokens_used": subscription.tokens_used,
        "tokens_limit": subscription.plan.tokens_monthly,
        "tokens_remaining": subscription.tokens_remaining,
    }


async def get_recent_activity(user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent activity for user.
    
    For now returns empty list - will be populated when activity logging is implemented.
    """
    # TODO: Implement activity logging
    return []


async def get_provider_health() -> List[Dict[str, Any]]:
    """
    Get provider health status.
    
    Cached for 60 seconds.
    """
    cache_key = "provider_health"
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Mock provider health data
    # In production, this would come from actual health checks
    providers = [
        {
            "provider": "RunPod",
            "status": "healthy",
            "latency_ms": 45,
            "availability_pct": 99.9,
            "last_checked": datetime.now(timezone.utc),
        },
        {
            "provider": "Vast.ai",
            "status": "healthy",
            "latency_ms": 62,
            "availability_pct": 99.5,
            "last_checked": datetime.now(timezone.utc),
        },
        {
            "provider": "Lambda Labs",
            "status": "healthy",
            "latency_ms": 38,
            "availability_pct": 99.8,
            "last_checked": datetime.now(timezone.utc),
        },
        {
            "provider": "CoreWeave",
            "status": "healthy",
            "latency_ms": 55,
            "availability_pct": 99.7,
            "last_checked": datetime.now(timezone.utc),
        },
    ]
    
    cache.set(cache_key, providers, 60)
    return providers


async def get_pod_detail(user_id: str, pod_id: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific pod.
    
    Args:
        user_id: User UUID
        pod_id: Pod UUID
        
    Returns:
        Pod detail dict or None
    """
    # TODO: Implement when pod management models are created
    return None


async def perform_pod_action(
    user_id: str,
    pod_id: str,
    action: str,
    force: bool = False,
) -> Dict[str, Any]:
    """
    Perform an action on a pod.
    
    Args:
        user_id: User UUID
        pod_id: Pod UUID
        action: Action to perform (start, stop, pause, resume, terminate)
        force: Force the action
        
    Returns:
        Action result dict
    """
    valid_actions = ['start', 'stop', 'pause', 'resume', 'terminate']
    
    if action not in valid_actions:
        return {
            "success": False,
            "pod_id": pod_id,
            "new_status": "unknown",
            "message": f"Invalid action: {action}",
        }
    
    # TODO: Implement when pod management is created
    # For now, return mock success
    
    status_map = {
        'start': 'running',
        'stop': 'stopped',
        'pause': 'paused',
        'resume': 'running',
        'terminate': 'terminated',
    }
    
    return {
        "success": True,
        "pod_id": pod_id,
        "new_status": status_map.get(action, 'unknown'),
        "message": f"Pod {action} initiated",
    }

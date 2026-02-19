"""
Dashboard Services - Business logic for dashboard data.
"""

import logging
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from asgiref.sync import sync_to_async
from django.core.cache import cache

logger = logging.getLogger("gpubroker.dashboard.services")

# Cache TTL
DASHBOARD_CACHE_TTL = 30  # 30 seconds for real-time feel


async def get_user_dashboard(user_id: str) -> dict[str, Any]:
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


async def get_quick_stats(user_id: str) -> dict[str, Any]:
    """Get quick stats for dashboard header."""
    # Import here to avoid circular imports
    from gpubrokerpod.gpubrokerapp.apps.billing.models import Subscription, UsageRecord

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Get user's subscription
    subscription = await sync_to_async(
        Subscription.objects.select_related("plan")
        .filter(user_id=user_id, status__in=["active", "trialing"])
        .first
    )()

    # Count pods (mock for now - would come from pod management)
    active_pods = 0
    total_pods = 0

    # Calculate month spend from usage records
    month_spend = Decimal("0.00")
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
                usage_type="api_call",
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


async def get_user_pods(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Get user's GPU pods from deployment system.

    Args:
        user_id: User UUID
        limit: Maximum number of pods to return

    Returns:
        List of pod dictionaries
    """
    from gpubrokerpod.gpubrokerapp.apps.deployment.models import PodDeploymentConfig

    pods = await sync_to_async(list)(
        PodDeploymentConfig.objects.filter(user_id=user_id).order_by("-created_at")[
            :limit
        ]
    )

    return [
        {
            "pod_id": str(pod.id),
            "name": pod.name,
            "provider": pod.provider,
            "gpu_type": pod.gpu_type,
            "gpu_count": pod.gpu_count,
            "status": pod.status,
            "created_at": pod.created_at,
            "cost_per_hour": float(pod.cost_per_hour) if pod.cost_per_hour else 0.0,
        }
        for pod in pods
    ]


async def get_billing_summary(user_id: str) -> dict[str, Any]:
    """Get billing summary for dashboard."""
    from gpubrokerpod.gpubrokerapp.apps.billing.models import Subscription

    subscription = await sync_to_async(
        Subscription.objects.select_related("plan")
        .filter(user_id=user_id, status__in=["active", "trialing"])
        .first
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


async def get_recent_activity(user_id: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Get recent activity for user from deployment and billing events.

    Args:
        user_id: User UUID
        limit: Maximum number of activities to return

    Returns:
        List of activity dictionaries
    """
    from gpubrokerpod.gpubrokerapp.apps.deployment.models import PodDeploymentConfig

    # Get recent pod deployments as activity
    recent_pods = await sync_to_async(list)(
        PodDeploymentConfig.objects.filter(user_id=user_id).order_by("-created_at")[
            :limit
        ]
    )

    activities = []
    for pod in recent_pods:
        activities.append(
            {
                "type": "pod_deployment",
                "description": f"Deployed {pod.gpu_type} pod: {pod.name}",
                "timestamp": pod.created_at,
                "status": pod.status,
                "metadata": {
                    "pod_id": str(pod.id),
                    "provider": pod.provider,
                    "gpu_count": pod.gpu_count,
                },
            }
        )

    return sorted(activities, key=lambda x: x["timestamp"], reverse=True)[:limit]


async def get_provider_health() -> list[dict[str, Any]]:
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


async def get_pod_detail(user_id: str, pod_id: str) -> dict[str, Any] | None:
    """
    Get detailed information about a specific pod.

    Args:
        user_id: User UUID
        pod_id: Pod UUID

    Returns:
        Pod detail dict or None if not found
    """
    from gpubrokerpod.gpubrokerapp.apps.deployment.models import PodDeploymentConfig

    try:
        pod = await sync_to_async(PodDeploymentConfig.objects.get)(
            id=pod_id, user_id=user_id
        )

        return {
            "pod_id": str(pod.id),
            "name": pod.name,
            "provider": pod.provider,
            "gpu_type": pod.gpu_type,
            "gpu_count": pod.gpu_count,
            "status": pod.status,
            "created_at": pod.created_at,
            "updated_at": pod.updated_at,
            "cost_per_hour": float(pod.cost_per_hour) if pod.cost_per_hour else 0.0,
            "total_cost": float(pod.total_cost) if hasattr(pod, "total_cost") else 0.0,
            "runtime_hours": (
                pod.runtime_hours if hasattr(pod, "runtime_hours") else 0.0
            ),
            "config": pod.config if hasattr(pod, "config") else {},
        }
    except PodDeploymentConfig.DoesNotExist:
        return None


async def perform_pod_action(
    user_id: str,
    pod_id: str,
    action: str,
    force: bool = False,
) -> dict[str, Any]:
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
    valid_actions = ["start", "stop", "pause", "resume", "terminate"]

    if action not in valid_actions:
        return {
            "success": False,
            "pod_id": pod_id,
            "new_status": "unknown",
            "message": f"Invalid action: {action}",
        }

    from gpubrokerpod.gpubrokerapp.apps.deployment.models import PodDeploymentConfig
    from gpubrokerpod.gpubrokerapp.apps.deployment.services import DeploymentService

    try:
        pod = await sync_to_async(PodDeploymentConfig.objects.get)(
            id=pod_id, user_id=user_id
        )

        deployment_service = DeploymentService()

        # Execute action via deployment service
        if action == "start":
            result = await deployment_service.start_pod(pod)
        elif action == "stop":
            result = await deployment_service.stop_pod(pod)
        elif action == "pause":
            result = await deployment_service.pause_pod(pod)
        elif action == "resume":
            result = await deployment_service.resume_pod(pod)
        elif action == "terminate":
            result = await deployment_service.terminate_pod(pod, force=force)

        return {
            "success": result.get("success", False),
            "pod_id": pod_id,
            "new_status": result.get("status", "unknown"),
            "message": result.get("message", f"Action {action} completed"),
        }

    except PodDeploymentConfig.DoesNotExist:
        return {
            "success": False,
            "pod_id": pod_id,
            "new_status": "not_found",
            "message": "Pod not found",
        }
    except Exception as e:
        logger.error(f"Failed to perform pod action {action} on {pod_id}: {e}")
        return {
            "success": False,
            "pod_id": pod_id,
            "new_status": "error",
            "message": str(e),
        }

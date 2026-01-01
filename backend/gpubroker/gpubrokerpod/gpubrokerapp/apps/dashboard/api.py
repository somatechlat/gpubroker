"""
Dashboard API Endpoints - Django Ninja Router.

Endpoints:
- GET / - Get complete dashboard data
- GET /pods - List user's pods
- GET /pods/{pod_id} - Get pod details
- POST /pods/{pod_id}/action - Perform pod action
- GET /activity - Get recent activity
- GET /providers/health - Get provider health status
"""
import logging
from typing import List

from ninja import Router
from ninja.errors import HttpError
from django.http import HttpRequest

from .schemas import (
    DashboardResponse,
    QuickStats,
    PodSummary,
    PodDetailResponse,
    PodActionRequest,
    PodActionResponse,
    ActivityItem,
    ProviderHealth,
    BillingSummary,
)
from .services import (
    get_user_dashboard,
    get_user_pods,
    get_pod_detail,
    perform_pod_action,
    get_recent_activity,
    get_provider_health,
    get_billing_summary,
    get_quick_stats,
)
from gpubrokerpod.gpubrokerapp.apps.auth_app.auth import JWTAuth

logger = logging.getLogger('gpubroker.dashboard.api')

router = Router(tags=["dashboard"])


@router.get("/", response=DashboardResponse, auth=JWTAuth())
async def get_dashboard(request: HttpRequest):
    """
    Get complete dashboard data.
    
    Returns quick stats, pods, billing, activity, and provider health.
    Cached for 30 seconds.
    """
    user = request.auth
    
    dashboard = await get_user_dashboard(str(user.id))
    
    return DashboardResponse(
        quick_stats=QuickStats(**dashboard["quick_stats"]),
        pods=[PodSummary(**p) for p in dashboard["pods"]],
        billing=BillingSummary(**dashboard["billing"]),
        recent_activity=[ActivityItem(**a) for a in dashboard["recent_activity"]],
        provider_health=[ProviderHealth(**p) for p in dashboard["provider_health"]],
    )


@router.get("/stats", response=QuickStats, auth=JWTAuth())
async def get_stats(request: HttpRequest):
    """
    Get quick stats only.
    
    Lighter endpoint for header updates.
    """
    user = request.auth
    
    stats = await get_quick_stats(str(user.id))
    return QuickStats(**stats)


@router.get("/pods", response=List[PodSummary], auth=JWTAuth())
async def list_pods(request: HttpRequest):
    """
    List user's pods.
    """
    user = request.auth
    
    pods = await get_user_pods(str(user.id))
    return [PodSummary(**p) for p in pods]


@router.get("/pods/{pod_id}", response=PodDetailResponse, auth=JWTAuth())
async def get_pod(request: HttpRequest, pod_id: str):
    """
    Get detailed information about a specific pod.
    """
    user = request.auth
    
    pod = await get_pod_detail(str(user.id), pod_id)
    
    if not pod:
        raise HttpError(404, "Pod not found")
    
    return PodDetailResponse(**pod)


@router.post("/pods/{pod_id}/action", response=PodActionResponse, auth=JWTAuth())
async def pod_action(request: HttpRequest, pod_id: str, data: PodActionRequest):
    """
    Perform an action on a pod.
    
    Actions: start, stop, pause, resume, terminate
    """
    user = request.auth
    
    # Verify pod_id matches
    if data.pod_id != pod_id:
        raise HttpError(400, "Pod ID mismatch")
    
    result = await perform_pod_action(
        user_id=str(user.id),
        pod_id=pod_id,
        action=data.action,
        force=data.force,
    )
    
    if not result["success"]:
        raise HttpError(400, result["message"])
    
    return PodActionResponse(**result)


@router.get("/activity", response=List[ActivityItem], auth=JWTAuth())
async def get_activity(request: HttpRequest, limit: int = 20):
    """
    Get recent activity log.
    """
    user = request.auth
    
    activity = await get_recent_activity(str(user.id), limit=limit)
    return [ActivityItem(**a) for a in activity]


@router.get("/billing", response=BillingSummary, auth=JWTAuth())
async def get_billing(request: HttpRequest):
    """
    Get billing summary.
    """
    user = request.auth
    
    billing = await get_billing_summary(str(user.id))
    return BillingSummary(**billing)


@router.get("/providers/health", response=List[ProviderHealth], auth=None)
async def providers_health(request: HttpRequest):
    """
    Get provider health status.
    
    This endpoint is public (no auth required).
    Cached for 60 seconds.
    """
    health = await get_provider_health()
    return [ProviderHealth(**p) for p in health]

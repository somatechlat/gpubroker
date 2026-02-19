"""
Dashboard Schemas - Pydantic models for API request/response.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any

from ninja import Schema


class PodSummary(Schema):
    """Summary of a user's pod."""
    id: str
    name: str
    gpu_type: str
    provider: str
    status: str  # pending, provisioning, running, paused, stopped, terminated
    cost_per_hour: float
    uptime_hours: float = 0.0
    created_at: datetime
    last_active: Optional[datetime] = None


class QuickStats(Schema):
    """Quick stats for dashboard header."""
    active_pods: int
    total_pods: int
    month_spend: float
    month_budget: Optional[float] = None
    api_calls_today: int
    savings_percentage: float = 0.0


class BillingSummary(Schema):
    """Billing summary for dashboard."""
    current_plan: str
    plan_tier: str
    monthly_cost: float
    next_billing_date: Optional[datetime] = None
    tokens_used: int
    tokens_limit: int
    tokens_remaining: int


class ActivityItem(Schema):
    """Activity log item."""
    id: str
    timestamp: datetime
    action: str  # pod_created, pod_started, pod_stopped, payment_made, etc.
    description: str
    resource_id: Optional[str] = None
    resource_type: Optional[str] = None


class ProviderHealth(Schema):
    """Provider health status."""
    provider: str
    status: str  # healthy, degraded, down
    latency_ms: int
    availability_pct: float
    last_checked: datetime


class DashboardResponse(Schema):
    """Complete dashboard response."""
    quick_stats: QuickStats
    pods: List[PodSummary]
    billing: BillingSummary
    recent_activity: List[ActivityItem]
    provider_health: List[ProviderHealth]


class PodDetailResponse(Schema):
    """Detailed pod information."""
    id: str
    name: str
    gpu_type: str
    gpu_count: int
    provider: str
    region: str
    status: str
    
    # Resources
    vcpus: int
    ram_gb: int
    storage_gb: int
    
    # Costs
    cost_per_hour: float
    total_cost: float
    uptime_hours: float
    
    # Connection
    ssh_host: Optional[str] = None
    ssh_port: Optional[int] = None
    jupyter_url: Optional[str] = None
    
    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    last_active: Optional[datetime] = None
    
    # Metrics
    cpu_usage_pct: Optional[float] = None
    memory_usage_pct: Optional[float] = None
    gpu_usage_pct: Optional[float] = None


class PodActionRequest(Schema):
    """Request for pod actions (start, stop, terminate)."""
    pod_id: str
    action: str  # start, stop, pause, resume, terminate
    force: bool = False


class PodActionResponse(Schema):
    """Response for pod actions."""
    success: bool
    pod_id: str
    new_status: str
    message: str

"""
Dashboard Schemas - Pydantic models for API request/response.
"""

from datetime import datetime

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
    last_active: datetime | None = None


class QuickStats(Schema):
    """Quick stats for dashboard header."""

    active_pods: int
    total_pods: int
    month_spend: float
    month_budget: float | None = None
    api_calls_today: int
    savings_percentage: float = 0.0


class BillingSummary(Schema):
    """Billing summary for dashboard."""

    current_plan: str
    plan_tier: str
    monthly_cost: float
    next_billing_date: datetime | None = None
    tokens_used: int
    tokens_limit: int
    tokens_remaining: int


class ActivityItem(Schema):
    """Activity log item."""

    id: str
    timestamp: datetime
    action: str  # pod_created, pod_started, pod_stopped, payment_made, etc.
    description: str
    resource_id: str | None = None
    resource_type: str | None = None


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
    pods: list[PodSummary]
    billing: BillingSummary
    recent_activity: list[ActivityItem]
    provider_health: list[ProviderHealth]


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
    ssh_host: str | None = None
    ssh_port: int | None = None
    jupyter_url: str | None = None

    # Timestamps
    created_at: datetime
    started_at: datetime | None = None
    last_active: datetime | None = None

    # Metrics
    cpu_usage_pct: float | None = None
    memory_usage_pct: float | None = None
    gpu_usage_pct: float | None = None


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

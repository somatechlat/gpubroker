"""
Provider Schemas - Pydantic models for API request/response.

These schemas define the contract for the Provider API endpoints.
"""

from datetime import datetime
from typing import Any

from ninja import Schema


class ProviderItem(Schema):
    """Single provider offer in list response."""

    id: str
    provider: str
    name: str
    gpu: str
    memory_gb: int = 0
    price_per_hour: float
    currency: str | None = "USD"
    availability: str
    region: str
    tags: list[str] = []
    last_updated: datetime


class ProviderListResponse(Schema):
    """Response for provider listing endpoint."""

    total: int
    items: list[ProviderItem]
    warnings: list[str] | None = None


class IntegrationConfig(Schema):
    """Request schema for saving provider integration config."""

    provider: str
    api_key: str | None = None
    api_url: str | None = None


class IntegrationStatus(Schema):
    """Status of a provider integration."""

    provider: str
    status: str  # 'active', 'error', 'not_configured'
    message: str | None = None
    last_checked: datetime


class ProviderFilters(Schema):
    """Query parameters for filtering providers."""

    gpu: str | None = None
    gpu_type: str | None = None  # Alias for gpu
    region: str | None = None
    provider: str | None = None
    availability: str | None = None  # available|limited|unavailable|busy
    compliance_tag: str | None = None
    gpu_memory_min: int | None = None
    gpu_memory_max: int | None = None
    price_min: float | None = None
    max_price: float | None = None
    page: int = 1
    per_page: int = 20


class ProviderHealthResponse(Schema):
    """Health check response for provider service."""

    status: str
    providers: list[str]
    timestamp: datetime


class FeaturedGPUItem(Schema):
    """Featured GPU offer for landing page display."""

    id: str
    provider: str
    provider_logo: str | None = None
    gpu_name: str
    gpu_model: str
    memory_gb: int
    price_per_hour: float
    price_per_day: float
    price_per_month: float
    currency: str = "USD"
    availability: str
    availability_score: int  # 0-100
    region: str
    performance_score: float | None = None  # TOPSIS score if available
    best_for: list[str] = []  # e.g., ["training", "inference", "rendering"]


class FeaturedGPUResponse(Schema):
    """Response for featured GPU endpoint."""

    featured: list[FeaturedGPUItem]
    total_providers: int
    total_gpus: int
    last_updated: datetime
    cache_ttl: int = 60  # seconds


# ============================================
# Browse GPU/Services Schemas (Task 13)
# ============================================


class BrowseGPUItem(Schema):
    """GPU offer item for browse page with extended details."""

    id: str
    provider: str
    provider_logo: str | None = None
    name: str
    gpu_type: str
    gpu_model: str
    memory_gb: int
    cpu_cores: int = 0
    ram_gb: int = 0
    storage_gb: int = 0
    storage_type: str = "SSD"
    price_per_hour: float
    price_per_day: float
    price_per_month: float
    currency: str = "USD"
    availability: str
    availability_score: int  # 0-100
    region: str
    availability_zone: str | None = None
    spot_pricing: bool = False
    preemptible: bool = False
    min_rental_hours: float = 1.0
    max_rental_hours: float | None = None
    network_speed_gbps: float | None = None
    sla_uptime: float | None = None
    compliance_tags: list[str] = []
    topsis_score: float | None = None  # TOPSIS ranking score
    topsis_rank: int | None = None
    best_for: list[str] = []
    last_updated: datetime


class BrowseFilters(Schema):
    """Filter parameters for browse page."""

    # GPU filters
    gpu_type: str | None = None  # Partial match
    gpu_model: str | None = None  # Exact match
    memory_min: int | None = None
    memory_max: int | None = None

    # Price filters
    price_min: float | None = None
    price_max: float | None = None
    spot_only: bool = False

    # Provider filters
    provider: str | None = None
    providers: list[str] | None = None  # Multiple providers

    # Region filters
    region: str | None = None
    regions: list[str] | None = None  # Multiple regions

    # Availability filters
    availability: str | None = None  # available, limited, unavailable
    available_only: bool = False

    # Compliance filters
    compliance_tags: list[str] | None = None

    # Performance filters
    min_cpu_cores: int | None = None
    min_ram_gb: int | None = None
    min_storage_gb: int | None = None


class BrowseSortOption(Schema):
    """Sort option for browse results."""

    field: str  # price, memory, availability, topsis_score, performance
    direction: str = "asc"  # asc, desc


class BrowsePagination(Schema):
    """Cursor-based pagination for browse results."""

    cursor: str | None = None  # Base64 encoded cursor
    limit: int = 20
    has_next: bool = False
    has_prev: bool = False
    next_cursor: str | None = None
    prev_cursor: str | None = None
    total: int = 0


class BrowseGPUResponse(Schema):
    """Response for browse GPU endpoint."""

    items: list[BrowseGPUItem]
    pagination: BrowsePagination
    filters_applied: dict[str, Any] = {}
    sort_applied: BrowseSortOption | None = None
    aggregations: dict[str, Any] = {}  # Facets for filtering UI
    last_updated: datetime
    cache_ttl: int = 30  # seconds


class GPUAggregations(Schema):
    """Aggregation data for filter facets."""

    providers: list[dict[str, Any]] = []  # [{name, count, logo}]
    regions: list[dict[str, Any]] = []  # [{name, count}]
    gpu_types: list[dict[str, Any]] = []  # [{name, count, memory_range}]
    price_range: dict[str, float] = {}  # {min, max, avg}
    memory_range: dict[str, int] = {}  # {min, max}
    availability_counts: dict[str, int] = {}  # {available: N, limited: N, ...}
    compliance_tags: list[dict[str, Any]] = []  # [{tag, count}]


class RealTimeAvailabilityUpdate(Schema):
    """WebSocket message for real-time availability updates."""

    type: str = "availability_update"
    offer_id: str
    provider: str
    gpu_type: str
    old_availability: str
    new_availability: str
    old_price: float | None = None
    new_price: float | None = None
    timestamp: datetime


class TOPSISRankingRequest(Schema):
    """Request for TOPSIS ranking calculation."""

    offer_ids: list[str]
    weights: dict[str, float] | None = None  # Custom weights
    criteria: list[str] | None = None  # Custom criteria


class TOPSISRankingResponse(Schema):
    """Response with TOPSIS rankings."""

    rankings: list[dict[str, Any]]  # [{offer_id, score, rank}]
    ideal_solution: dict[str, float]
    anti_ideal_solution: dict[str, float]
    criteria_used: list[str]
    weights_used: dict[str, float]

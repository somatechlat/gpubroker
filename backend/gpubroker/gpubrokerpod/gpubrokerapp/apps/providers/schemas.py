"""
Provider Schemas - Pydantic models for API request/response.

These schemas define the contract for the Provider API endpoints.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from ninja import Schema


class ProviderItem(Schema):
    """Single provider offer in list response."""
    id: str
    provider: str
    name: str
    gpu: str
    memory_gb: int = 0
    price_per_hour: float
    currency: Optional[str] = "USD"
    availability: str
    region: str
    tags: List[str] = []
    last_updated: datetime


class ProviderListResponse(Schema):
    """Response for provider listing endpoint."""
    total: int
    items: List[ProviderItem]
    warnings: Optional[List[str]] = None


class IntegrationConfig(Schema):
    """Request schema for saving provider integration config."""
    provider: str
    api_key: Optional[str] = None
    api_url: Optional[str] = None


class IntegrationStatus(Schema):
    """Status of a provider integration."""
    provider: str
    status: str  # 'active', 'error', 'not_configured'
    message: Optional[str] = None
    last_checked: datetime


class ProviderFilters(Schema):
    """Query parameters for filtering providers."""
    gpu: Optional[str] = None
    gpu_type: Optional[str] = None  # Alias for gpu
    region: Optional[str] = None
    provider: Optional[str] = None
    availability: Optional[str] = None  # available|limited|unavailable|busy
    compliance_tag: Optional[str] = None
    gpu_memory_min: Optional[int] = None
    gpu_memory_max: Optional[int] = None
    price_min: Optional[float] = None
    max_price: Optional[float] = None
    page: int = 1
    per_page: int = 20


class ProviderHealthResponse(Schema):
    """Health check response for provider service."""
    status: str
    providers: List[str]
    timestamp: datetime


class FeaturedGPUItem(Schema):
    """Featured GPU offer for landing page display."""
    id: str
    provider: str
    provider_logo: Optional[str] = None
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
    performance_score: Optional[float] = None  # TOPSIS score if available
    best_for: List[str] = []  # e.g., ["training", "inference", "rendering"]


class FeaturedGPUResponse(Schema):
    """Response for featured GPU endpoint."""
    featured: List[FeaturedGPUItem]
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
    provider_logo: Optional[str] = None
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
    availability_zone: Optional[str] = None
    spot_pricing: bool = False
    preemptible: bool = False
    min_rental_hours: float = 1.0
    max_rental_hours: Optional[float] = None
    network_speed_gbps: Optional[float] = None
    sla_uptime: Optional[float] = None
    compliance_tags: List[str] = []
    topsis_score: Optional[float] = None  # TOPSIS ranking score
    topsis_rank: Optional[int] = None
    best_for: List[str] = []
    last_updated: datetime


class BrowseFilters(Schema):
    """Filter parameters for browse page."""
    # GPU filters
    gpu_type: Optional[str] = None  # Partial match
    gpu_model: Optional[str] = None  # Exact match
    memory_min: Optional[int] = None
    memory_max: Optional[int] = None
    
    # Price filters
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    spot_only: bool = False
    
    # Provider filters
    provider: Optional[str] = None
    providers: Optional[List[str]] = None  # Multiple providers
    
    # Region filters
    region: Optional[str] = None
    regions: Optional[List[str]] = None  # Multiple regions
    
    # Availability filters
    availability: Optional[str] = None  # available, limited, unavailable
    available_only: bool = False
    
    # Compliance filters
    compliance_tags: Optional[List[str]] = None
    
    # Performance filters
    min_cpu_cores: Optional[int] = None
    min_ram_gb: Optional[int] = None
    min_storage_gb: Optional[int] = None


class BrowseSortOption(Schema):
    """Sort option for browse results."""
    field: str  # price, memory, availability, topsis_score, performance
    direction: str = "asc"  # asc, desc


class BrowsePagination(Schema):
    """Cursor-based pagination for browse results."""
    cursor: Optional[str] = None  # Base64 encoded cursor
    limit: int = 20
    has_next: bool = False
    has_prev: bool = False
    next_cursor: Optional[str] = None
    prev_cursor: Optional[str] = None
    total: int = 0


class BrowseGPUResponse(Schema):
    """Response for browse GPU endpoint."""
    items: List[BrowseGPUItem]
    pagination: BrowsePagination
    filters_applied: Dict[str, Any] = {}
    sort_applied: Optional[BrowseSortOption] = None
    aggregations: Dict[str, Any] = {}  # Facets for filtering UI
    last_updated: datetime
    cache_ttl: int = 30  # seconds


class GPUAggregations(Schema):
    """Aggregation data for filter facets."""
    providers: List[Dict[str, Any]] = []  # [{name, count, logo}]
    regions: List[Dict[str, Any]] = []  # [{name, count}]
    gpu_types: List[Dict[str, Any]] = []  # [{name, count, memory_range}]
    price_range: Dict[str, float] = {}  # {min, max, avg}
    memory_range: Dict[str, int] = {}  # {min, max}
    availability_counts: Dict[str, int] = {}  # {available: N, limited: N, ...}
    compliance_tags: List[Dict[str, Any]] = []  # [{tag, count}]


class RealTimeAvailabilityUpdate(Schema):
    """WebSocket message for real-time availability updates."""
    type: str = "availability_update"
    offer_id: str
    provider: str
    gpu_type: str
    old_availability: str
    new_availability: str
    old_price: Optional[float] = None
    new_price: Optional[float] = None
    timestamp: datetime


class TOPSISRankingRequest(Schema):
    """Request for TOPSIS ranking calculation."""
    offer_ids: List[str]
    weights: Optional[Dict[str, float]] = None  # Custom weights
    criteria: Optional[List[str]] = None  # Custom criteria


class TOPSISRankingResponse(Schema):
    """Response with TOPSIS rankings."""
    rankings: List[Dict[str, Any]]  # [{offer_id, score, rank}]
    ideal_solution: Dict[str, float]
    anti_ideal_solution: Dict[str, float]
    criteria_used: List[str]
    weights_used: Dict[str, float]

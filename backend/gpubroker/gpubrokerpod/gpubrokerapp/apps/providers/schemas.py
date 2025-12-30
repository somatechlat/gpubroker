"""
Provider Schemas - Pydantic models for API request/response.

These schemas define the contract for the Provider API endpoints.
"""
from datetime import datetime
from typing import List, Optional

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

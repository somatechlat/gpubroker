"""
KPI Schemas - Pydantic models for KPI API request/response.

These schemas define the contract for the KPI API endpoints.
"""

from datetime import datetime
from typing import Any

from ninja import Schema


class GPUMetrics(Schema):
    """Comprehensive KPIs for a specific GPU type."""

    gpu_type: str
    provider: str
    avg_price_per_hour: float
    cost_per_token: float | None = None
    cost_per_gflop: float | None = None
    availability_score: float | None = None
    reliability_score: float | None = None
    performance_score: float | None = None
    region: str
    last_updated: datetime


class ProviderKPI(Schema):
    """Comprehensive KPIs for a specific provider."""

    provider: str
    total_offers: int
    avg_price_per_hour: float
    price_volatility: float  # Standard deviation of prices
    uptime_percentage: float
    response_time_ms: float
    customer_satisfaction: float | None = None
    cost_efficiency_score: float
    reliability_index: float


class MarketInsights(Schema):
    """Comprehensive market insights and trends."""

    total_providers: int
    total_offers: int
    cheapest_gpu_offer: dict[str, Any] | None = None
    most_expensive_gpu_offer: dict[str, Any] | None = None
    avg_market_price: float
    price_trend_7d: float  # Percentage change
    demand_hotspots: list[str] = []
    supply_constraints: list[str] = []
    generated_at: datetime


class KPIOverviewResponse(Schema):
    """Aggregate KPI cards for dashboard."""

    cost_per_token: float | None = None
    uptime_pct: float | None = None
    avg_latency_ms: float | None = None
    active_providers: int = 0


class CostOptimizationRequest(Schema):
    """Request for workload cost optimization."""

    type: str = "general"
    gpu_memory_required: int | None = None
    duration_hours: float | None = None
    priority: str | None = "normal"


class CostOptimization(Schema):
    """Cost optimization recommendations for workloads."""

    workload_type: str
    recommended_provider: str
    recommended_gpu: str
    estimated_cost_savings: float
    savings_percentage: float
    reasoning: list[str]
    risk_factors: list[str]


class KPIHealthResponse(Schema):
    """Health check response for KPI service."""

    status: str
    database: str
    kpi_engine: str
    timestamp: datetime

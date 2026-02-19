"""
KPI Schemas - Pydantic models for KPI API request/response.

These schemas define the contract for the KPI API endpoints.
"""
from datetime import datetime
from typing import Dict, List, Optional, Any

from ninja import Schema


class GPUMetrics(Schema):
    """Comprehensive KPIs for a specific GPU type."""
    gpu_type: str
    provider: str
    avg_price_per_hour: float
    cost_per_token: Optional[float] = None
    cost_per_gflop: Optional[float] = None
    availability_score: Optional[float] = None
    reliability_score: Optional[float] = None
    performance_score: Optional[float] = None
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
    customer_satisfaction: Optional[float] = None
    cost_efficiency_score: float
    reliability_index: float


class MarketInsights(Schema):
    """Comprehensive market insights and trends."""
    total_providers: int
    total_offers: int
    cheapest_gpu_offer: Optional[Dict[str, Any]] = None
    most_expensive_gpu_offer: Optional[Dict[str, Any]] = None
    avg_market_price: float
    price_trend_7d: float  # Percentage change
    demand_hotspots: List[str] = []
    supply_constraints: List[str] = []
    generated_at: datetime


class KPIOverviewResponse(Schema):
    """Aggregate KPI cards for dashboard."""
    cost_per_token: Optional[float] = None
    uptime_pct: Optional[float] = None
    avg_latency_ms: Optional[float] = None
    active_providers: int = 0


class CostOptimizationRequest(Schema):
    """Request for workload cost optimization."""
    type: str = "general"
    gpu_memory_required: Optional[int] = None
    duration_hours: Optional[float] = None
    priority: Optional[str] = "normal"


class CostOptimization(Schema):
    """Cost optimization recommendations for workloads."""
    workload_type: str
    recommended_provider: str
    recommended_gpu: str
    estimated_cost_savings: float
    savings_percentage: float
    reasoning: List[str]
    risk_factors: List[str]


class KPIHealthResponse(Schema):
    """Health check response for KPI service."""
    status: str
    database: str
    kpi_engine: str
    timestamp: datetime

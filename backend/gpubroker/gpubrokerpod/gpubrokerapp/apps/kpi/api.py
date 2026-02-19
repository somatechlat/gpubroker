"""
KPI API Endpoints - Django Ninja Router.

Endpoints:
- GET /overview - Aggregate KPI dashboard cards
- GET /gpu/{gpu_type} - GPU-specific KPIs
- GET /provider/{provider_name} - Provider-specific KPIs
- GET /insights/market - Market insights and trends
- POST /optimize/workload - Workload cost optimization
- GET /health - KPI service health check

NO MOCKS. NO FAKE DATA. REAL DATABASE QUERIES ONLY.
"""
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any

from ninja import Router
from ninja.errors import HttpError
from django.http import HttpRequest

from .schemas import (
    KPIOverviewResponse,
    GPUMetrics,
    ProviderKPI,
    MarketInsights,
    CostOptimization,
    CostOptimizationRequest,
    KPIHealthResponse,
)
from .services import (
    get_kpi_overview,
    get_gpu_metrics,
    get_provider_kpis,
    get_market_insights,
    get_workload_optimization,
)

logger = logging.getLogger('gpubroker.kpi.api')

router = Router(tags=["kpi"])


@router.get("/overview", response=KPIOverviewResponse, auth=None)
async def kpi_overview(request: HttpRequest):
    """
    Get aggregate KPI cards for dashboard.
    
    Returns:
    - cost_per_token: Average cost per token across all GPUs
    - uptime_pct: Average uptime percentage
    - avg_latency_ms: Average API latency
    - active_providers: Number of active providers
    """
    try:
        result = await get_kpi_overview()
        return KPIOverviewResponse(**result)
    except Exception as e:
        logger.error(f"KPI overview failed: {e}")
        raise HttpError(503, "Database not available")


@router.get("/gpu/{gpu_type}", response=GPUMetrics, auth=None)
async def get_gpu_kpis(
    request: HttpRequest,
    gpu_type: str,
    provider: Optional[str] = None
):
    """
    Get comprehensive KPIs for a specific GPU type.
    
    Args:
        gpu_type: GPU type to query (e.g., "A100", "RTX 4090")
        provider: Optional provider filter
        
    Returns:
        GPU metrics including cost per token, cost per GFLOP, etc.
    """
    try:
        result = await get_gpu_metrics(gpu_type, provider)
        return GPUMetrics(**result)
    except Exception as e:
        logger.error(f"GPU KPIs failed for {gpu_type}: {e}")
        raise HttpError(503, "Database not available")


@router.get("/provider/{provider_name}", response=ProviderKPI, auth=None)
async def get_provider_kpi(request: HttpRequest, provider_name: str):
    """
    Get comprehensive KPIs for a specific provider.
    
    Args:
        provider_name: Provider name to query
        
    Returns:
        Provider KPIs including total offers, avg price, volatility, etc.
    """
    try:
        result = await get_provider_kpis(provider_name)
        return ProviderKPI(**result)
    except ValueError as e:
        raise HttpError(404, str(e))
    except Exception as e:
        logger.error(f"Provider KPIs failed for {provider_name}: {e}")
        raise HttpError(503, "Database not available")


@router.get("/insights/market", response=MarketInsights, auth=None)
async def market_insights(request: HttpRequest):
    """
    Get comprehensive market insights and trends.
    
    Returns:
        Market insights including totals, extremes, trends, etc.
    """
    try:
        result = await get_market_insights()
        return MarketInsights(**result)
    except Exception as e:
        logger.error(f"Market insights failed: {e}")
        raise HttpError(503, "Database not available")


@router.post("/optimize/workload", response=CostOptimization, auth=None)
async def optimize_workload(request: HttpRequest, data: CostOptimizationRequest):
    """
    Get cost optimization recommendations for a workload.
    
    Args:
        data: Workload specification including type
        
    Returns:
        Optimization recommendations with reasoning
    """
    try:
        result = await get_workload_optimization(data.type)
        return CostOptimization(**result)
    except Exception as e:
        logger.error(f"Workload optimization failed: {e}")
        raise HttpError(500, "Optimization failed")


@router.get("/health", response=KPIHealthResponse, auth=None)
async def health_check(request: HttpRequest):
    """
    KPI service health check.
    
    Returns:
        Health status including database connectivity
    """
    from django.db import connection
    
    db_status = "disconnected"
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        pass
    
    status = "healthy" if db_status == "connected" else "degraded"
    
    return KPIHealthResponse(
        status=status,
        database=db_status,
        kpi_engine="operational",
        timestamp=datetime.now(timezone.utc),
    )

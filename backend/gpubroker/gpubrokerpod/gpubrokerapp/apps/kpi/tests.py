"""
KPI App Tests.

Tests for:
- KPI overview endpoint
- GPU metrics endpoint
- Provider KPI endpoint
- Market insights endpoint
"""

import pytest
from gpubrokerpod.gpubrokerapp.apps.kpi.services import (
    KPIEngine,
    get_gpu_metrics,
    get_kpi_overview,
    get_market_insights,
    get_provider_kpis,
)

# ============================================
# KPI Engine Tests
# ============================================


@pytest.mark.django_db(transaction=True)
class TestKPIEngine:
    """Tests for KPI engine calculations."""

    def test_kpi_engine_initialization(self):
        """Test KPI engine initializes correctly."""
        engine = KPIEngine()
        assert engine is not None

    @pytest.mark.asyncio
    async def test_calculate_cost_per_token(self):
        """Test cost per token calculation."""
        engine = KPIEngine()
        cost = await engine.calculate_cost_per_token("A100", 3.50)

        assert cost > 0
        assert cost < 0.01  # Should be a small number

    @pytest.mark.asyncio
    async def test_calculate_cost_per_gflop(self):
        """Test cost per GFLOP calculation."""
        engine = KPIEngine()
        cost = await engine.calculate_cost_per_gflop("A100", 3.50)

        assert cost > 0

    @pytest.mark.asyncio
    async def test_get_overview_with_data(self, test_gpu_offers):
        """Test KPI overview with existing data."""
        overview = await get_kpi_overview()

        assert "cost_per_token" in overview
        assert "active_providers" in overview
        assert overview["active_providers"] >= 1

    @pytest.mark.asyncio
    async def test_get_gpu_metrics(self, test_gpu_offers):
        """Test getting metrics for specific GPU type."""
        metrics = await get_gpu_metrics("RTX 4090")

        assert "gpu_type" in metrics
        assert "avg_price_per_hour" in metrics
        assert "cost_per_token" in metrics
        assert metrics["gpu_type"] == "RTX 4090"

    @pytest.mark.asyncio
    async def test_get_provider_kpis(self, test_gpu_offers, test_provider):
        """Test getting KPIs for specific provider."""
        kpis = await get_provider_kpis(test_provider.name)

        assert "provider" in kpis
        assert "total_offers" in kpis
        assert "avg_price_per_hour" in kpis
        assert kpis["provider"] == test_provider.name

    @pytest.mark.asyncio
    async def test_get_provider_kpis_not_found(self):
        """Test getting KPIs for non-existent provider raises error."""
        with pytest.raises(ValueError, match="not found"):
            await get_provider_kpis("nonexistent_provider")

    @pytest.mark.asyncio
    async def test_get_market_insights(self, test_gpu_offers):
        """Test getting market insights."""
        insights = await get_market_insights()

        assert "total_providers" in insights
        assert "total_offers" in insights
        assert "cheapest_gpu_offer" in insights
        assert "avg_market_price" in insights


# ============================================
# KPI API Tests
# ============================================


@pytest.mark.django_db(transaction=True)
class TestKPIAPI:
    """Tests for KPI API endpoints."""

    @pytest.mark.asyncio
    async def test_overview_endpoint(self, api_client, test_gpu_offers):
        """Test GET /kpi/overview endpoint."""
        response = await api_client.get("/kpi/overview")

        assert response.status_code == 200
        data = response.json()
        assert "cost_per_token" in data
        assert "active_providers" in data

    @pytest.mark.asyncio
    async def test_gpu_metrics_endpoint(self, api_client, test_gpu_offers):
        """Test GET /kpi/gpu/{gpu_type} endpoint."""
        response = await api_client.get("/kpi/gpu/RTX 4090")

        assert response.status_code == 200
        data = response.json()
        assert data["gpu_type"] == "RTX 4090"
        assert "avg_price_per_hour" in data

    @pytest.mark.asyncio
    async def test_gpu_metrics_unknown_gpu(self, api_client):
        """Test GET /kpi/gpu/{gpu_type} for unknown GPU returns zero metrics."""
        response = await api_client.get("/kpi/gpu/Unknown GPU XYZ")

        assert response.status_code == 200
        data = response.json()
        assert data["avg_price_per_hour"] == 0.0

    @pytest.mark.asyncio
    async def test_provider_kpis_endpoint(
        self, api_client, test_gpu_offers, test_provider
    ):
        """Test GET /kpi/provider/{provider_name} endpoint."""
        response = await api_client.get(f"/kpi/provider/{test_provider.name}")

        assert response.status_code == 200
        data = response.json()
        assert data["provider"] == test_provider.name
        assert "total_offers" in data

    @pytest.mark.asyncio
    async def test_provider_kpis_not_found(self, api_client):
        """Test GET /kpi/provider/{provider_name} for unknown provider."""
        response = await api_client.get("/kpi/provider/nonexistent_provider")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_market_insights_endpoint(self, api_client, test_gpu_offers):
        """Test GET /kpi/insights/market endpoint."""
        response = await api_client.get("/kpi/insights/market")

        assert response.status_code == 200
        data = response.json()
        assert "total_providers" in data
        assert "total_offers" in data
        assert "avg_market_price" in data

    @pytest.mark.asyncio
    async def test_health_endpoint(self, api_client):
        """Test GET /kpi/health endpoint."""
        response = await api_client.get("/kpi/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "timestamp" in data

"""
Math Core Tests.

Tests for:
- Cost per token calculation
- Cost per GFLOP calculation
- TOPSIS algorithm
- Ensemble recommendations
- Workload estimation
- GPU benchmarks
"""

import numpy as np
import pytest
from gpubrokerpod.gpubrokerapp.apps.math_core.benchmarks import BenchmarkRepository

# ============================================
# KPI Calculator Tests
# ============================================


class TestKPICalculator:
    """Tests for KPI calculation functions."""

    def test_cost_per_token_valid_input(self, kpi_calculator):
        """Test cost per token with valid input."""
        result = kpi_calculator.cost_per_token(
            price_per_hour=1.50, gpu_type="RTX 4090", model_size="7b"
        )

        assert "cost_per_token" in result
        assert "cost_per_million_tokens" in result
        assert "tokens_per_second" in result
        assert "confidence" in result
        assert result["cost_per_token"] > 0
        assert result["tokens_per_second"] > 0

    def test_cost_per_token_different_model_sizes(self, kpi_calculator):
        """Test cost per token varies by model size."""
        result_7b = kpi_calculator.cost_per_token(1.50, "RTX 4090", "7b")
        result_70b = kpi_calculator.cost_per_token(1.50, "RTX 4090", "70b")

        # 70B model should have higher cost per token (slower)
        assert (
            result_70b["cost_per_million_tokens"] > result_7b["cost_per_million_tokens"]
        )

    def test_cost_per_token_invalid_price(self, kpi_calculator):
        """Test cost per token with invalid price raises error."""
        with pytest.raises(ValueError, match="price_per_hour must be positive"):
            kpi_calculator.cost_per_token(
                price_per_hour=0, gpu_type="RTX 4090", model_size="7b"
            )

    def test_cost_per_gflop_valid_input(self, kpi_calculator):
        """Test cost per GFLOP with valid input."""
        result = kpi_calculator.cost_per_gflop(
            price_per_hour=1.50, gpu_type="RTX 4090", precision="fp32"
        )

        assert "cost_per_gflop" in result
        assert "cost_per_tflop_hour" in result
        assert "gpu_tflops" in result
        assert "confidence" in result
        assert result["cost_per_gflop"] > 0

    def test_cost_per_gflop_different_precisions(self, kpi_calculator):
        """Test cost per GFLOP varies by precision."""
        result_fp32 = kpi_calculator.cost_per_gflop(1.50, "RTX 4090", "fp32")
        result_fp16 = kpi_calculator.cost_per_gflop(1.50, "RTX 4090", "fp16")

        # FP16 should have lower cost per GFLOP (more TFLOPS)
        assert result_fp16["cost_per_gflop"] < result_fp32["cost_per_gflop"]

    def test_cost_per_gflop_invalid_price(self, kpi_calculator):
        """Test cost per GFLOP with invalid price raises error."""
        with pytest.raises(ValueError, match="price_per_hour must be positive"):
            kpi_calculator.cost_per_gflop(
                price_per_hour=-1.0, gpu_type="RTX 4090", precision="fp32"
            )

    def test_efficiency_score_valid_input(self, kpi_calculator):
        """Test efficiency score calculation."""
        result = kpi_calculator.efficiency_score(
            price_per_hour=1.50,
            gpu_type="RTX 4090",
            availability_score=0.95,
            reliability_score=0.90,
        )

        assert "efficiency_score" in result
        assert "breakdown" in result
        assert 0 <= result["efficiency_score"] <= 1

        breakdown = result["breakdown"]
        assert "performance_score" in breakdown
        assert "price_score" in breakdown
        assert "availability_score" in breakdown
        assert "reliability_score" in breakdown

    def test_efficiency_score_clamps_values(self, kpi_calculator):
        """Test efficiency score clamps input values to [0, 1]."""
        result = kpi_calculator.efficiency_score(
            price_per_hour=1.50,
            gpu_type="RTX 4090",
            availability_score=1.5,  # Over 1
            reliability_score=-0.5,  # Under 0
        )

        breakdown = result["breakdown"]
        assert breakdown["availability_score"] == 1.0
        assert breakdown["reliability_score"] == 0.0

    def test_round_price_precision(self, kpi_calculator):
        """Test price rounding precision."""
        result = kpi_calculator._round_price(1.23456789, decimals=4)
        assert result == 1.2346  # Banker's rounding

    def test_round_price_invalid_value(self, kpi_calculator):
        """Test rounding invalid values raises error."""
        with pytest.raises(ValueError):
            kpi_calculator._round_price(float("nan"))

        with pytest.raises(ValueError):
            kpi_calculator._round_price(float("inf"))


# ============================================
# TOPSIS Algorithm Tests
# ============================================


class TestTOPSISEngine:
    """Tests for TOPSIS algorithm."""

    def test_topsis_basic_calculation(
        self,
        topsis_engine,
        sample_decision_matrix,
        sample_weights,
        sample_criteria_types,
    ):
        """Test basic TOPSIS calculation."""
        result = topsis_engine.calculate(
            decision_matrix=sample_decision_matrix,
            weights=sample_weights,
            criteria_types=sample_criteria_types,
        )

        assert "scores" in result
        assert "rankings" in result
        assert len(result["scores"]) == len(sample_decision_matrix)
        assert len(result["rankings"]) == len(sample_decision_matrix)

    def test_topsis_scores_in_range(
        self,
        topsis_engine,
        sample_decision_matrix,
        sample_weights,
        sample_criteria_types,
    ):
        """Test TOPSIS scores are in [0, 1] range."""
        result = topsis_engine.calculate(
            decision_matrix=sample_decision_matrix,
            weights=sample_weights,
            criteria_types=sample_criteria_types,
        )

        for score in result["scores"]:
            assert 0 <= score <= 1

    def test_topsis_rankings_unique(
        self,
        topsis_engine,
        sample_decision_matrix,
        sample_weights,
        sample_criteria_types,
    ):
        """Test TOPSIS rankings are unique."""
        result = topsis_engine.calculate(
            decision_matrix=sample_decision_matrix,
            weights=sample_weights,
            criteria_types=sample_criteria_types,
        )

        rankings = result["rankings"]
        assert len(rankings) == len(set(rankings))

    def test_topsis_cost_criteria_handling(self, topsis_engine):
        """Test TOPSIS handles cost criteria correctly (lower is better)."""
        # Two alternatives: one cheap, one expensive
        matrix = np.array(
            [
                [1.0, 10],  # Cheap, low performance
                [5.0, 10],  # Expensive, same performance
            ]
        )
        weights = [0.5, 0.5]
        criteria_types = ["cost", "benefit"]

        result = topsis_engine.calculate(matrix, weights, criteria_types)

        # Cheaper option should rank higher
        assert result["rankings"][0] < result["rankings"][1]

    def test_topsis_benefit_criteria_handling(self, topsis_engine):
        """Test TOPSIS handles benefit criteria correctly (higher is better)."""
        # Two alternatives: one high performance, one low
        matrix = np.array(
            [
                [1.0, 100],  # Same price, high performance
                [1.0, 10],  # Same price, low performance
            ]
        )
        weights = [0.5, 0.5]
        criteria_types = ["cost", "benefit"]

        result = topsis_engine.calculate(matrix, weights, criteria_types)

        # Higher performance should rank higher
        assert result["rankings"][0] < result["rankings"][1]

    def test_topsis_weight_sensitivity(self, topsis_engine):
        """Test TOPSIS is sensitive to weight changes."""
        matrix = np.array(
            [
                [1.0, 100],  # Cheap, high performance
                [0.5, 50],  # Cheaper, lower performance
            ]
        )
        criteria_types = ["cost", "benefit"]

        # Price-focused weights
        result_price = topsis_engine.calculate(matrix, [0.8, 0.2], criteria_types)

        # Performance-focused weights
        result_perf = topsis_engine.calculate(matrix, [0.2, 0.8], criteria_types)

        # Rankings may differ based on weight emphasis
        assert result_price["scores"] != result_perf["scores"]


# ============================================
# Workload Mapper Tests
# ============================================


class TestWorkloadMapper:
    """Tests for workload mapping functionality."""

    def test_estimate_image_generation(self, workload_mapper):
        """Test image generation workload estimation."""
        result = workload_mapper.estimate(
            workload_type="image_generation",
            quantity=100,
            duration_hours=1.0,
            quality="standard",
        )

        assert "min_vram_gb" in result
        assert "recommended_vram_gb" in result
        assert "recommended_gpu_tiers" in result
        assert "estimated_cost_range" in result
        assert "confidence" in result
        assert "reasoning" in result

        assert result["min_vram_gb"] > 0
        assert len(result["recommended_gpu_tiers"]) > 0

    def test_estimate_llm_inference(self, workload_mapper):
        """Test LLM inference workload estimation."""
        result = workload_mapper.estimate(
            workload_type="llm_inference",
            quantity=1000,
            duration_hours=1.0,
            model_name="7b",
        )

        assert result["min_vram_gb"] >= 8  # 7B model needs at least 8GB
        assert "tokens_per_second_range" not in result  # Internal detail
        assert result["confidence"] > 0

    def test_estimate_training(self, workload_mapper):
        """Test training workload estimation."""
        result = workload_mapper.estimate(
            workload_type="training",
            quantity=10000,  # 10k samples
            duration_hours=8.0,
            model_name="finetune_7b",
        )

        assert result["min_vram_gb"] >= 16
        assert "reasoning" in result
        assert len(result["reasoning"]) > 0

    def test_estimate_unknown_workload_type(self, workload_mapper):
        """Test estimation with unknown workload type raises error."""
        with pytest.raises(ValueError, match="Unknown workload type"):
            workload_mapper.estimate(
                workload_type="unknown_type", quantity=100, duration_hours=1.0
            )

    def test_estimate_quality_affects_time(self, workload_mapper):
        """Test quality setting affects time estimation."""
        result_draft = workload_mapper.estimate(
            workload_type="image_generation",
            quantity=100,
            duration_hours=1.0,
            quality="draft",
        )

        result_high = workload_mapper.estimate(
            workload_type="image_generation",
            quantity=100,
            duration_hours=1.0,
            quality="high",
        )

        # High quality should take longer per image
        assert (
            result_high["estimated_time_per_unit"]
            > result_draft["estimated_time_per_unit"]
        )

    def test_estimate_large_model_multi_gpu(self, workload_mapper):
        """Test large model estimation suggests multi-GPU."""
        result = workload_mapper.estimate(
            workload_type="llm_inference",
            quantity=1000,
            duration_hours=1.0,
            model_name="70b",
        )

        # 70B model should mention multi-GPU
        reasoning_text = " ".join(result["reasoning"])
        assert "multi" in reasoning_text.lower() or result["min_vram_gb"] >= 140


# ============================================
# Benchmark Repository Tests
# ============================================


class TestBenchmarkRepository:
    """Tests for GPU benchmark repository."""

    def test_get_benchmark_known_gpu(self):
        """Test getting benchmark for known GPU."""
        repo = BenchmarkRepository()
        benchmark = repo.get("RTX 4090")

        assert benchmark is not None
        assert "tflops_fp32" in benchmark
        assert "vram_gb" in benchmark

    def test_get_benchmark_unknown_gpu(self):
        """Test getting benchmark for unknown GPU returns None."""
        repo = BenchmarkRepository()
        benchmark = repo.get("Unknown GPU XYZ")

        assert benchmark is None

    def test_get_tokens_per_second(self):
        """Test getting tokens per second for GPU."""
        repo = BenchmarkRepository()
        tps = repo.get_tokens_per_second("RTX 4090", "7b")

        assert tps > 0

    def test_get_tflops(self):
        """Test getting TFLOPS for GPU."""
        repo = BenchmarkRepository()
        tflops = repo.get_tflops("RTX 4090", "fp32")

        assert tflops > 0

    def test_list_all_benchmarks(self):
        """Test listing all benchmarks."""
        repo = BenchmarkRepository()
        benchmarks = repo.list_all()

        assert len(benchmarks) > 0
        for benchmark in benchmarks:
            assert "gpu_model" in benchmark


# ============================================
# Math Core API Tests
# ============================================


@pytest.mark.django_db(transaction=True)
class TestMathCoreAPI:
    """Tests for math core API endpoints."""

    @pytest.mark.asyncio
    async def test_cost_per_token_endpoint(self, api_client):
        """Test POST /math/cost-per-token endpoint."""
        response = await api_client.post(
            "/math/cost-per-token",
            json={"price_per_hour": 1.50, "gpu_type": "RTX 4090", "model_size": "7b"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "cost_per_million_tokens" in data
        assert data["cost_per_million_tokens"] > 0

    @pytest.mark.asyncio
    async def test_cost_per_gflop_endpoint(self, api_client):
        """Test POST /math/cost-per-gflop endpoint."""
        response = await api_client.post(
            "/math/cost-per-gflop",
            json={"price_per_hour": 1.50, "gpu_type": "RTX 4090", "precision": "fp32"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "cost_per_gflop" in data
        assert "gpu_tflops" in data

    @pytest.mark.asyncio
    async def test_topsis_endpoint(self, api_client):
        """Test POST /math/topsis endpoint."""
        response = await api_client.post(
            "/math/topsis",
            json={
                "decision_matrix": [
                    [1.50, 24, 82.6, 0.95],
                    [3.50, 80, 19.5, 0.85],
                    [0.50, 10, 29.8, 0.99],
                ],
                "weights": [0.30, 0.25, 0.25, 0.20],
                "criteria_types": ["cost", "benefit", "benefit", "benefit"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "scores" in data
        assert "rankings" in data
        assert len(data["scores"]) == 3

    @pytest.mark.asyncio
    async def test_topsis_invalid_weights(self, api_client):
        """Test TOPSIS with weights not summing to 1."""
        response = await api_client.post(
            "/math/topsis",
            json={
                "decision_matrix": [[1, 2], [3, 4]],
                "weights": [0.3, 0.3],  # Sum = 0.6, not 1.0
                "criteria_types": ["cost", "benefit"],
            },
        )

        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_estimate_workload_endpoint(self, api_client):
        """Test POST /math/estimate-workload endpoint."""
        response = await api_client.post(
            "/math/estimate-workload",
            json={
                "workload_type": "image_generation",
                "quantity": 100,
                "duration_hours": 1.0,
                "quality": "standard",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "min_vram_gb" in data
        assert "recommended_gpu_tiers" in data

    @pytest.mark.asyncio
    async def test_benchmarks_list_endpoint(self, api_client):
        """Test GET /math/benchmarks endpoint."""
        response = await api_client.get("/math/benchmarks")

        assert response.status_code == 200
        data = response.json()
        assert "benchmarks" in data
        assert "count" in data
        assert data["count"] > 0

    @pytest.mark.asyncio
    async def test_benchmark_detail_endpoint(self, api_client):
        """Test GET /math/benchmarks/{gpu_type} endpoint."""
        response = await api_client.get("/math/benchmarks/RTX 4090")

        assert response.status_code == 200
        data = response.json()
        assert "gpu_model" in data
        assert "tflops_fp32" in data

    @pytest.mark.asyncio
    async def test_benchmark_not_found(self, api_client):
        """Test GET /math/benchmarks/{gpu_type} for unknown GPU."""
        response = await api_client.get("/math/benchmarks/Unknown GPU")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_ensemble_recommend_endpoint(self, api_client):
        """Test POST /math/ensemble-recommend endpoint."""
        response = await api_client.post(
            "/math/ensemble-recommend",
            json={
                "candidate_offers": [
                    {
                        "id": "1",
                        "price_per_hour": 1.50,
                        "vram_gb": 24,
                        "tflops": 82.6,
                        "availability_score": 0.95,
                        "reliability_score": 0.90,
                    },
                    {
                        "id": "2",
                        "price_per_hour": 3.50,
                        "vram_gb": 80,
                        "tflops": 19.5,
                        "availability_score": 0.85,
                        "reliability_score": 0.95,
                    },
                ],
                "workload_profile": {"budget_per_hour": 2.0},
                "top_k": 2,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "recommendations" in data
        assert "algorithm_contributions" in data
        assert "confidence" in data

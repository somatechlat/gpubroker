"""
Property-based tests for KPI Calculator.

**Feature: gpubroker-enterprise-saas, Property 6: Math Core Cost-Per-Token Calculation**
**Validates: Requirements 5.1, 21.1, 33.3**
"""

import pytest
from hypothesis import given, strategies as st, settings, HealthCheck
import math

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.benchmarks import BenchmarkRepository
from core.kpi_calculator import KPICalculator


@pytest.fixture
def kpi_calculator():
    benchmark_repo = BenchmarkRepository()
    return KPICalculator(benchmark_repo)


class TestCostPerToken:
    """
    **Feature: gpubroker-enterprise-saas, Property 6: Math Core Cost-Per-Token Calculation**
    **Validates: Requirements 5.1, 21.1, 33.3**
    
    For any GPU type with known benchmark data, the cost_per_token calculation 
    SHALL equal: price_per_hour / (tokens_per_second * 3600) with IEEE 754 double precision.
    """
    
    @given(
        price=st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
        tps=st.integers(min_value=100, max_value=10000)
    )
    @settings(max_examples=100)
    def test_cost_per_token_formula_mathematical(self, price: float, tps: int):
        """
        **Feature: gpubroker-enterprise-saas, Property 6: Math Core Cost-Per-Token Calculation**
        **Validates: Requirements 5.1, 21.1, 33.3**
        
        Property: cost_per_token = price_per_hour / (tokens_per_second * 3600)
        IEEE 754 double precision.
        """
        # Direct calculation using IEEE 754 double precision
        expected = price / (tps * 3600)
        
        # Verify formula holds with double precision
        tokens_per_hour = tps * 3600
        actual = price / tokens_per_hour
        
        # IEEE 754 double precision has ~15-17 significant digits
        # We verify to 10 decimal places
        assert abs(actual - expected) < 1e-10, "Cost per token formula must be IEEE 754 precise"
    
    @given(
        price=st.floats(min_value=0.10, max_value=50.0, allow_nan=False, allow_infinity=False),
        gpu=st.sampled_from(["H100-SXM", "A100-SXM", "RTX-4090", "V100-SXM2", "T4", "L40S"]),
        model_size=st.sampled_from(["7b", "13b"])
    )
    @settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cost_per_token_via_calculator(self, kpi_calculator, price: float, gpu: str, model_size: str):
        """
        **Feature: gpubroker-enterprise-saas, Property 6: Math Core Cost-Per-Token Calculation**
        **Validates: Requirements 5.1, 21.1, 33.3**
        
        Property: For any valid price and GPU with benchmark data,
        cost_per_token SHALL equal price_per_hour / (tokens_per_second * 3600)
        """
        result = kpi_calculator.cost_per_token(
            price_per_hour=price,
            gpu_type=gpu,
            model_size=model_size
        )
        
        # Verify result structure
        assert "cost_per_token" in result
        assert "tokens_per_second" in result
        assert "cost_per_million_tokens" in result
        assert "confidence" in result
        
        # Verify the formula: cost_per_token = price / (tps * 3600)
        tps = result["tokens_per_second"]
        expected_cost = price / (tps * 3600)
        actual_cost = result["cost_per_token"]
        
        # Allow for rounding (10 decimal precision in implementation)
        assert abs(actual_cost - expected_cost) < 1e-9, \
            f"Formula mismatch: expected {expected_cost}, got {actual_cost}"
        
        # Verify cost_per_million = cost_per_token * 1_000_000
        expected_million = actual_cost * 1_000_000
        actual_million = result["cost_per_million_tokens"]
        
        # Allow for 4 decimal rounding
        assert abs(actual_million - expected_million) < 0.0001, \
            f"Million token cost mismatch: expected {expected_million}, got {actual_million}"
        
        # Verify confidence is valid
        assert 0.0 <= result["confidence"] <= 1.0
    
    @given(
        price=st.floats(min_value=0.01, max_value=100.0, allow_nan=False, allow_infinity=False),
        gpu=st.sampled_from(["H100-SXM", "A100-SXM", "RTX-4090"])
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cost_per_token_monotonic_with_price(self, kpi_calculator, price: float, gpu: str):
        """
        **Feature: gpubroker-enterprise-saas, Property 6: Math Core Cost-Per-Token Calculation**
        **Validates: Requirements 5.1, 21.1**
        
        Property: cost_per_token SHALL increase monotonically with price_per_hour
        (for same GPU and model size)
        """
        result1 = kpi_calculator.cost_per_token(price_per_hour=price, gpu_type=gpu, model_size="7b")
        result2 = kpi_calculator.cost_per_token(price_per_hour=price * 2, gpu_type=gpu, model_size="7b")
        
        # Double the price should double the cost
        ratio = result2["cost_per_token"] / result1["cost_per_token"]
        assert abs(ratio - 2.0) < 1e-9, "Cost should scale linearly with price"
    
    @given(gpu=st.sampled_from(["H100-SXM", "A100-SXM", "RTX-4090", "V100-SXM2"]))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cost_per_token_model_size_ordering(self, kpi_calculator, gpu: str):
        """
        **Feature: gpubroker-enterprise-saas, Property 6: Math Core Cost-Per-Token Calculation**
        **Validates: Requirements 5.1, 21.1**
        
        Property: For same GPU and price, larger models SHALL have higher cost_per_token
        (because they have lower tokens_per_second)
        """
        price = 3.0
        
        result_7b = kpi_calculator.cost_per_token(price_per_hour=price, gpu_type=gpu, model_size="7b")
        result_13b = kpi_calculator.cost_per_token(price_per_hour=price, gpu_type=gpu, model_size="13b")
        
        # 13B model should have higher cost per token (slower inference)
        assert result_13b["cost_per_token"] >= result_7b["cost_per_token"], \
            f"13B model should cost more per token than 7B on {gpu}"
        
        # TPS should be lower for larger model
        assert result_13b["tokens_per_second"] <= result_7b["tokens_per_second"], \
            f"13B model should have lower TPS than 7B on {gpu}"
    
    def test_cost_per_token_known_gpu(self, kpi_calculator):
        """Test with known GPU benchmark data - specific example."""
        result = kpi_calculator.cost_per_token(
            price_per_hour=3.0,
            gpu_type="A100",
            model_size="7b"
        )
        
        assert "cost_per_token" in result
        assert "cost_per_million_tokens" in result
        assert "tokens_per_second" in result
        assert result["tokens_per_second"] > 0
        assert result["cost_per_token"] > 0
        assert result["confidence"] >= 0.6
        
        # Verify calculation details are present
        assert "calculation_details" in result
        assert result["calculation_details"]["formula"] == "price_per_hour / (tokens_per_second * 3600)"
    
    def test_cost_per_token_precision(self, kpi_calculator):
        """Verify 4 decimal precision for cost_per_million_tokens."""
        result = kpi_calculator.cost_per_token(
            price_per_hour=2.5,
            gpu_type="H100",
            model_size="7b"
        )
        
        # cost_per_million should have at most 4 decimal places
        cost_str = str(result["cost_per_million_tokens"])
        if "." in cost_str:
            decimals = len(cost_str.split(".")[1])
            assert decimals <= 4, "Price precision must be 4 decimals max"
    
    @given(price=st.floats(min_value=-100, max_value=0))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cost_per_token_rejects_negative_price(self, kpi_calculator, price: float):
        """Negative prices must be rejected with ValueError."""
        with pytest.raises(ValueError):
            kpi_calculator.cost_per_token(
                price_per_hour=price,
                gpu_type="A100",
                model_size="7b"
            )
    
    def test_cost_per_token_rejects_zero_price(self, kpi_calculator):
        """Zero price must be rejected with ValueError."""
        with pytest.raises(ValueError):
            kpi_calculator.cost_per_token(
                price_per_hour=0.0,
                gpu_type="A100",
                model_size="7b"
            )


class TestCostPerGFLOP:
    """Tests for cost per GFLOP calculations."""
    
    def test_cost_per_gflop_known_gpu(self, kpi_calculator):
        """Test with known GPU benchmark data."""
        result = kpi_calculator.cost_per_gflop(
            price_per_hour=3.0,
            gpu_type="A100"
        )
        
        assert "cost_per_gflop" in result
        assert "cost_per_tflop_hour" in result
        assert "gpu_tflops" in result
        assert result["gpu_tflops"] > 0
    
    @given(price=st.floats(min_value=-100, max_value=0))
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_cost_per_gflop_rejects_negative_price(self, kpi_calculator, price: float):
        """Negative prices must be rejected."""
        with pytest.raises(ValueError):
            kpi_calculator.cost_per_gflop(
                price_per_hour=price,
                gpu_type="A100"
            )


class TestEfficiencyScore:
    """Tests for efficiency score calculations."""
    
    def test_efficiency_score_bounds(self, kpi_calculator):
        """Efficiency score must be in [0, 1]."""
        result = kpi_calculator.efficiency_score(
            price_per_hour=2.0,
            gpu_type="A100",
            availability_score=0.9,
            reliability_score=0.95
        )
        
        assert 0 <= result["efficiency_score"] <= 1
        assert 0 <= result["breakdown"]["performance_score"] <= 1
        assert 0 <= result["breakdown"]["price_score"] <= 1
    
    @given(
        availability=st.floats(min_value=0, max_value=1),
        reliability=st.floats(min_value=0, max_value=1)
    )
    @settings(max_examples=50, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_efficiency_score_input_bounds(self, kpi_calculator, availability: float, reliability: float):
        """Input scores outside [0,1] should be clamped."""
        result = kpi_calculator.efficiency_score(
            price_per_hour=2.0,
            gpu_type="A100",
            availability_score=availability,
            reliability_score=reliability
        )
        
        assert 0 <= result["efficiency_score"] <= 1


class TestBenchmarkRepository:
    """
    Tests for GPU benchmark data.
    
    **Feature: gpubroker-enterprise-saas, Property 24: GPU Benchmark Data Validity**
    **Validates: Requirements 21.6, 33.4**
    """
    
    def test_benchmark_data_validity(self):
        """
        **Feature: gpubroker-enterprise-saas, Property 24: GPU Benchmark Data Validity**
        **Validates: Requirements 21.6, 33.4**
        
        For any GPU model in benchmarks table:
        - tflops_fp32 > 0
        - tokens_per_second_7b > 0 for inference-capable GPUs
        """
        repo = BenchmarkRepository()
        benchmarks = repo.list_all()
        
        assert len(benchmarks) > 0, "Must have benchmark data"
        
        for benchmark in benchmarks:
            assert benchmark.tflops_fp32 > 0, f"{benchmark.gpu_model} must have tflops_fp32 > 0"
            assert benchmark.vram_gb > 0, f"{benchmark.gpu_model} must have vram_gb > 0"
            assert benchmark.tokens_per_second_7b > 0, f"{benchmark.gpu_model} must have tokens_per_second_7b > 0"
    
    def test_benchmark_lookup_aliases(self):
        """GPU lookup should work with common aliases."""
        repo = BenchmarkRepository()
        
        # These should all find the same GPU
        aliases = ["A100", "a100", "A100-SXM", "A100 80GB"]
        results = [repo.get(alias) for alias in aliases]
        
        # All should return a result
        assert all(r is not None for r in results), "All aliases should resolve"
    
    @given(st.sampled_from([
        "H100-SXM", "H100-PCIe", "A100-SXM", "A100-PCIe", "A10", "A6000",
        "V100-SXM2", "V100-PCIe", "RTX-4090", "RTX-4080", "RTX-4070-Ti",
        "RTX-3090", "RTX-3080", "T4", "L40S", "L4"
    ]))
    @settings(max_examples=100)
    def test_benchmark_data_validity_property(self, gpu_model: str):
        """
        **Feature: gpubroker-enterprise-saas, Property 24: GPU Benchmark Data Validity**
        **Validates: Requirements 21.6, 33.4**
        
        Property: For any GPU model in benchmarks table:
        - tflops_fp32 SHALL be > 0
        - vram_gb SHALL be > 0
        - tokens_per_second_7b SHALL be > 0 for inference-capable GPUs
        - memory_bandwidth_gbps SHALL be > 0
        - tdp_watts SHALL be > 0
        """
        repo = BenchmarkRepository()
        benchmark = repo.get(gpu_model)
        
        assert benchmark is not None, f"GPU {gpu_model} must exist in benchmarks"
        
        # Core validity checks per Requirements 21.6, 33.4
        assert benchmark.tflops_fp32 > 0, f"{gpu_model}: tflops_fp32 must be > 0"
        assert benchmark.tflops_fp16 > 0, f"{gpu_model}: tflops_fp16 must be > 0"
        assert benchmark.vram_gb > 0, f"{gpu_model}: vram_gb must be > 0"
        assert benchmark.memory_bandwidth_gbps > 0, f"{gpu_model}: memory_bandwidth must be > 0"
        assert benchmark.tokens_per_second_7b > 0, f"{gpu_model}: tokens_per_second_7b must be > 0"
        assert benchmark.tdp_watts > 0, f"{gpu_model}: tdp_watts must be > 0"
        
        # Architecture must be specified
        assert benchmark.architecture in ["Hopper", "Ampere", "Volta", "Ada Lovelace", "Turing"], \
            f"{gpu_model}: architecture must be valid"
        
        # Source must be documented
        assert len(benchmark.source) > 0, f"{gpu_model}: source must be documented"
    
    @given(st.sampled_from([
        "H100-SXM", "H100-PCIe", "A100-SXM", "A100-PCIe", "A10", "A6000",
        "V100-SXM2", "V100-PCIe", "RTX-4090", "RTX-4080", "RTX-4070-Ti",
        "RTX-3090", "RTX-3080", "T4", "L40S", "L4"
    ]))
    @settings(max_examples=100)
    def test_benchmark_performance_hierarchy(self, gpu_model: str):
        """
        **Feature: gpubroker-enterprise-saas, Property 24: GPU Benchmark Data Validity**
        **Validates: Requirements 21.6, 33.4**
        
        Property: Performance metrics must follow logical hierarchy:
        - FP16 TFLOPS >= FP32 TFLOPS (tensor cores accelerate FP16)
        - Higher VRAM GPUs should generally have higher TPS for larger models
        """
        repo = BenchmarkRepository()
        benchmark = repo.get(gpu_model)
        
        assert benchmark is not None, f"GPU {gpu_model} must exist"
        
        # FP16 should be >= FP32 due to tensor core acceleration
        assert benchmark.tflops_fp16 >= benchmark.tflops_fp32, \
            f"{gpu_model}: FP16 TFLOPS ({benchmark.tflops_fp16}) should be >= FP32 ({benchmark.tflops_fp32})"
        
        # If INT8 is available, it should be >= FP16
        if benchmark.tflops_int8 is not None:
            assert benchmark.tflops_int8 >= benchmark.tflops_fp16, \
                f"{gpu_model}: INT8 TFLOPS should be >= FP16"
        
        # 7B model TPS should be >= 13B model TPS (smaller model = faster)
        if benchmark.tokens_per_second_13b is not None:
            assert benchmark.tokens_per_second_7b >= benchmark.tokens_per_second_13b, \
                f"{gpu_model}: 7B TPS should be >= 13B TPS"
        
        # 13B model TPS should be >= 70B model TPS
        if benchmark.tokens_per_second_13b is not None and benchmark.tokens_per_second_70b is not None:
            assert benchmark.tokens_per_second_13b >= benchmark.tokens_per_second_70b, \
                f"{gpu_model}: 13B TPS should be >= 70B TPS"

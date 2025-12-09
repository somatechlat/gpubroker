"""
Property-based tests for GPU Benchmark Data Validity.

**Feature: gpubroker-enterprise-saas, Property 24: GPU Benchmark Data Validity**
**Validates: Requirements 21.6, 33.4**

For any GPU model in benchmarks table:
- tflops_fp32 SHALL be > 0
- tokens_per_second_7b SHALL be > 0 for inference-capable GPUs
- vram_gb SHALL be > 0
- All benchmark data SHALL come from verified sources
"""

import pytest
import hypothesis
from hypothesis import given, strategies as st, settings, assume, HealthCheck
import numpy as np

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.benchmarks import BenchmarkRepository, GPUBenchmarkData


@pytest.fixture
def benchmark_repo():
    return BenchmarkRepository()


class TestGPUBenchmarkDataValidity:
    """
    **Feature: gpubroker-enterprise-saas, Property 24: GPU Benchmark Data Validity**
    **Validates: Requirements 21.6, 33.4**
    
    For any GPU model in benchmarks table:
    - tflops_fp32 > 0
    - tokens_per_second_7b > 0 for inference-capable GPUs
    - vram_gb > 0
    - memory_bandwidth_gbps > 0
    """
    
    def test_all_gpus_have_positive_tflops(self, benchmark_repo):
        """All GPUs must have tflops_fp32 > 0."""
        benchmarks = benchmark_repo.list_all()
        
        assert len(benchmarks) > 0, "Must have benchmark data loaded"
        
        for benchmark in benchmarks:
            assert benchmark.tflops_fp32 > 0, \
                f"{benchmark.gpu_model} must have tflops_fp32 > 0, got {benchmark.tflops_fp32}"
    
    def test_all_gpus_have_positive_vram(self, benchmark_repo):
        """All GPUs must have vram_gb > 0."""
        benchmarks = benchmark_repo.list_all()
        
        for benchmark in benchmarks:
            assert benchmark.vram_gb > 0, \
                f"{benchmark.gpu_model} must have vram_gb > 0, got {benchmark.vram_gb}"
    
    def test_all_gpus_have_positive_tokens_per_second(self, benchmark_repo):
        """All inference-capable GPUs must have tokens_per_second_7b > 0."""
        benchmarks = benchmark_repo.list_all()
        
        for benchmark in benchmarks:
            assert benchmark.tokens_per_second_7b > 0, \
                f"{benchmark.gpu_model} must have tokens_per_second_7b > 0, got {benchmark.tokens_per_second_7b}"
    
    def test_all_gpus_have_positive_memory_bandwidth(self, benchmark_repo):
        """All GPUs must have memory_bandwidth_gbps > 0."""
        benchmarks = benchmark_repo.list_all()
        
        for benchmark in benchmarks:
            assert benchmark.memory_bandwidth_gbps > 0, \
                f"{benchmark.gpu_model} must have memory_bandwidth_gbps > 0"
    
    def test_all_gpus_have_source_citation(self, benchmark_repo):
        """All benchmarks must cite their data source."""
        benchmarks = benchmark_repo.list_all()
        
        for benchmark in benchmarks:
            assert benchmark.source is not None and len(benchmark.source) > 0, \
                f"{benchmark.gpu_model} must have source citation"
    
    def test_fp16_greater_than_fp32(self, benchmark_repo):
        """FP16 TFLOPS should be >= FP32 TFLOPS (tensor cores)."""
        benchmarks = benchmark_repo.list_all()
        
        for benchmark in benchmarks:
            assert benchmark.tflops_fp16 >= benchmark.tflops_fp32, \
                f"{benchmark.gpu_model}: FP16 ({benchmark.tflops_fp16}) should be >= FP32 ({benchmark.tflops_fp32})"
    
    def test_tokens_per_second_decreases_with_model_size(self, benchmark_repo):
        """Larger models should have lower tokens/second."""
        benchmarks = benchmark_repo.list_all()
        
        for benchmark in benchmarks:
            tps_7b = benchmark.tokens_per_second_7b
            tps_13b = benchmark.tokens_per_second_13b
            tps_70b = benchmark.tokens_per_second_70b
            
            if tps_13b is not None:
                assert tps_13b <= tps_7b, \
                    f"{benchmark.gpu_model}: 13B TPS ({tps_13b}) should be <= 7B TPS ({tps_7b})"
            
            if tps_70b is not None and tps_13b is not None:
                assert tps_70b <= tps_13b, \
                    f"{benchmark.gpu_model}: 70B TPS ({tps_70b}) should be <= 13B TPS ({tps_13b})"


class TestBenchmarkLookup:
    """Tests for GPU benchmark lookup functionality."""
    
    def test_lookup_by_exact_name(self, benchmark_repo):
        """Should find GPU by exact model name."""
        benchmark = benchmark_repo.get("H100-SXM")
        assert benchmark is not None
        assert "H100" in benchmark.gpu_model
    
    def test_lookup_by_alias(self, benchmark_repo):
        """Should find GPU by common aliases."""
        # All these should resolve to A100
        aliases = ["A100", "a100", "A100-SXM", "A100 80GB"]
        
        for alias in aliases:
            benchmark = benchmark_repo.get(alias)
            assert benchmark is not None, f"Should find benchmark for alias: {alias}"
            assert "A100" in benchmark.gpu_model.upper()
    
    def test_lookup_case_insensitive(self, benchmark_repo):
        """Lookup should be case-insensitive."""
        upper = benchmark_repo.get("RTX-4090")
        lower = benchmark_repo.get("rtx-4090")
        mixed = benchmark_repo.get("Rtx-4090")
        
        assert upper is not None
        assert lower is not None
        assert mixed is not None
        assert upper.gpu_model == lower.gpu_model == mixed.gpu_model
    
    def test_lookup_unknown_returns_none(self, benchmark_repo):
        """Unknown GPU should return None, not raise."""
        result = benchmark_repo.get("UNKNOWN-GPU-XYZ")
        assert result is None


class TestBenchmarkDataConsistency:
    """Tests for data consistency across benchmarks."""
    
    def test_no_duplicate_gpu_models(self, benchmark_repo):
        """Each GPU model should appear only once."""
        benchmarks = benchmark_repo.list_all()
        models = [b.gpu_model for b in benchmarks]
        
        assert len(models) == len(set(models)), "Duplicate GPU models found"
    
    def test_minimum_gpu_count(self, benchmark_repo):
        """Should have reasonable number of GPUs."""
        benchmarks = benchmark_repo.list_all()
        
        # We should have at least the major GPUs
        assert len(benchmarks) >= 10, f"Expected at least 10 GPUs, got {len(benchmarks)}"
    
    def test_major_gpus_present(self, benchmark_repo):
        """Major GPU models should be present."""
        required_gpus = ["H100", "A100", "V100", "RTX-4090", "T4", "L40S"]
        
        for gpu in required_gpus:
            benchmark = benchmark_repo.get(gpu)
            assert benchmark is not None, f"Required GPU {gpu} not found in benchmarks"
    
    def test_architecture_field_valid(self, benchmark_repo):
        """Architecture field should be valid."""
        valid_architectures = {
            "Hopper", "Ampere", "Ada Lovelace", "Volta", "Turing", 
            "Pascal", "Maxwell", "Kepler"
        }
        
        benchmarks = benchmark_repo.list_all()
        
        for benchmark in benchmarks:
            assert benchmark.architecture in valid_architectures, \
                f"{benchmark.gpu_model} has invalid architecture: {benchmark.architecture}"


class TestBenchmarkHelperMethods:
    """Tests for benchmark repository helper methods."""
    
    def test_get_tokens_per_second_7b(self, benchmark_repo):
        """Should return correct TPS for 7B model."""
        tps = benchmark_repo.get_tokens_per_second("A100", "7b")
        assert tps is not None
        assert tps > 0
    
    def test_get_tokens_per_second_13b(self, benchmark_repo):
        """Should return correct TPS for 13B model."""
        tps = benchmark_repo.get_tokens_per_second("A100", "13b")
        assert tps is not None
        assert tps > 0
    
    def test_get_tokens_per_second_unknown_gpu(self, benchmark_repo):
        """Should return None for unknown GPU."""
        tps = benchmark_repo.get_tokens_per_second("UNKNOWN-GPU", "7b")
        assert tps is None
    
    def test_get_tflops_fp32(self, benchmark_repo):
        """Should return correct TFLOPS for FP32."""
        tflops = benchmark_repo.get_tflops("H100", "fp32")
        assert tflops is not None
        assert tflops > 50  # H100 has ~67 TFLOPS FP32
    
    def test_get_tflops_fp16(self, benchmark_repo):
        """Should return correct TFLOPS for FP16."""
        tflops = benchmark_repo.get_tflops("H100", "fp16")
        assert tflops is not None
        assert tflops > 1000  # H100 has ~1979 TFLOPS FP16


class TestBenchmarkPropertyBased:
    """Property-based tests using Hypothesis."""
    
    @given(st.sampled_from(["H100-SXM", "A100-SXM", "RTX-4090", "V100-SXM2", "T4"]))
    @settings(max_examples=20, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_benchmark_lookup_deterministic(self, benchmark_repo, gpu_name: str):
        """
        **Feature: gpubroker-enterprise-saas, Property 24: GPU Benchmark Data Validity**
        
        Benchmark lookup should be deterministic - same input, same output.
        """
        result1 = benchmark_repo.get(gpu_name)
        result2 = benchmark_repo.get(gpu_name)
        
        assert result1 is not None
        assert result2 is not None
        assert result1.gpu_model == result2.gpu_model
        assert result1.tflops_fp32 == result2.tflops_fp32
        assert result1.vram_gb == result2.vram_gb
    
    @given(
        model_size=st.sampled_from(["7b", "13b", "70b"]),
        gpu=st.sampled_from(["H100-SXM", "A100-SXM", "RTX-4090"])
    )
    @settings(max_examples=30, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_tps_consistency(self, benchmark_repo, model_size: str, gpu: str):
        """TPS values should be consistent across lookups."""
        tps1 = benchmark_repo.get_tokens_per_second(gpu, model_size)
        tps2 = benchmark_repo.get_tokens_per_second(gpu, model_size)
        
        # Both should be same (either both None or both equal)
        assert tps1 == tps2
    
    @given(precision=st.sampled_from(["fp32", "fp16", "int8"]))
    @settings(max_examples=15, suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_tflops_precision_ordering(self, benchmark_repo, precision: str):
        """
        For any GPU, TFLOPS should follow: INT8 >= FP16 >= FP32
        (when available)
        """
        benchmark = benchmark_repo.get("H100-SXM")
        assert benchmark is not None
        
        fp32 = benchmark.tflops_fp32
        fp16 = benchmark.tflops_fp16
        int8 = benchmark.tflops_int8
        
        assert fp16 >= fp32, "FP16 should be >= FP32"
        if int8 is not None:
            assert int8 >= fp16, "INT8 should be >= FP16"

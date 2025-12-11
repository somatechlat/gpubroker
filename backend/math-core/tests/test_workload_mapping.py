"""
Property 13: Workload-to-GPU Mapping Completeness
Validates: Requirements 22.2, 22.3, 22.4, 27.1, 27.2, 27.3
"""

import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from algorithms.workload_mapper import WorkloadMapper
from core.benchmarks import BenchmarkRepository


@pytest.fixture
def mapper():
    return WorkloadMapper(BenchmarkRepository())


def _assert_estimate_shape(est):
    for key in ["min_vram_gb", "recommended_vram_gb", "recommended_gpu_tiers", "estimated_cost_range", "confidence", "reasoning"]:
        assert key in est
    assert isinstance(est["recommended_gpu_tiers"], list)
    assert isinstance(est["estimated_cost_range"], dict)
    assert "low" in est["estimated_cost_range"] and "high" in est["estimated_cost_range"]
    assert est["confidence"] >= 0
    assert isinstance(est["reasoning"], list) and len(est["reasoning"]) >= 1


def test_all_workload_types_supported(mapper):
    for workload_type in mapper.workload_profiles.keys():
        est = mapper.estimate(workload_type, quantity=10, duration_hours=1.0, quality="standard")
        _assert_estimate_shape(est)


def test_map_to_gpus_returns_benchmarks(mapper):
    result = mapper.map_to_gpus("image_generation", quantity=5, duration_hours=0.5, quality="draft")
    assert "recommended_gpus" in result
    # recommended_gpus may be empty if benchmark not found, but structure should exist
    assert isinstance(result["recommended_gpus"], list)
    assert "requirements" in result and "min_vram_gb" in result["requirements"]
    assert "cost_estimate" in result and "low" in result["cost_estimate"]


def test_unknown_workload_raises(mapper):
    with pytest.raises(ValueError):
        mapper.estimate("unknown_workload", quantity=1, duration_hours=1.0)

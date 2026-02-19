"""
Math Core Pydantic Schemas.

Request/Response models for math endpoints.
NO MOCKS. NO FAKE DATA. REAL SCHEMAS ONLY.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional

from ninja import Schema
from pydantic import Field


# ============================================
# Cost Per Token
# ============================================

class CostPerTokenRequest(Schema):
    """Request for cost-per-token calculation."""
    price_per_hour: float = Field(..., gt=0, description="Price per hour in USD")
    gpu_type: str = Field(..., description="GPU model name (e.g., 'A100', 'H100')")
    model_size: str = Field("7b", description="LLM model size (e.g., '7b', '13b', '70b')")


class CostPerTokenResponse(Schema):
    """Response for cost-per-token calculation."""
    cost_per_token: float
    cost_per_million_tokens: float
    tokens_per_second: int
    confidence: float
    calculation_details: Dict[str, Any]


# ============================================
# Cost Per GFLOP
# ============================================

class CostPerGFLOPRequest(Schema):
    """Request for cost-per-GFLOP calculation."""
    price_per_hour: float = Field(..., gt=0, description="Price per hour in USD")
    gpu_type: str = Field(..., description="GPU model name")
    precision: str = Field("fp32", description="Compute precision: fp32, fp16, int8")


class CostPerGFLOPResponse(Schema):
    """Response for cost-per-GFLOP calculation."""
    cost_per_gflop: float
    cost_per_tflop_hour: float
    gpu_tflops: float
    confidence: float


# ============================================
# Efficiency Score
# ============================================

class EfficiencyScoreRequest(Schema):
    """Request for efficiency score calculation."""
    price_per_hour: float = Field(..., gt=0)
    gpu_type: str
    availability_score: float = Field(1.0, ge=0, le=1)
    reliability_score: float = Field(1.0, ge=0, le=1)


class EfficiencyScoreResponse(Schema):
    """Response for efficiency score calculation."""
    efficiency_score: float
    breakdown: Dict[str, Any]


# ============================================
# TOPSIS
# ============================================

class TOPSISRequest(Schema):
    """Request for TOPSIS multi-criteria decision analysis."""
    decision_matrix: List[List[float]] = Field(
        ..., description="Alternatives x Criteria matrix"
    )
    weights: List[float] = Field(
        ..., description="Criteria weights (must sum to 1)"
    )
    criteria_types: List[str] = Field(
        ..., description="'benefit' or 'cost' for each criterion"
    )


class TOPSISResponse(Schema):
    """Response for TOPSIS calculation."""
    rankings: List[int]
    scores: List[float]
    ideal_solution: List[float]
    anti_ideal_solution: List[float]


# ============================================
# Ensemble Recommendations
# ============================================

class EnsembleRecommendRequest(Schema):
    """Request for ensemble recommendations."""
    user_id: Optional[str] = None
    workload_profile: Dict[str, Any] = Field(
        ..., description="User's workload requirements"
    )
    candidate_offers: List[Dict[str, Any]] = Field(
        ..., description="List of GPU offers to rank"
    )
    top_k: int = Field(5, ge=1, le=20, description="Number of recommendations")


class EnsembleRecommendResponse(Schema):
    """Response for ensemble recommendations."""
    recommendations: List[Dict[str, Any]]
    algorithm_contributions: Dict[str, float]
    confidence: float


# ============================================
# Workload Estimation
# ============================================

class WorkloadEstimateRequest(Schema):
    """Request for workload estimation."""
    workload_type: str = Field(
        ..., description="'image_generation', 'llm_inference', 'training'"
    )
    quantity: int = Field(..., gt=0, description="Number of items to process")
    duration_hours: float = Field(..., gt=0, description="Target duration in hours")
    quality: str = Field("standard", description="'draft', 'standard', 'high'")
    model_name: Optional[str] = Field(
        None, description="Specific model name if applicable"
    )


class WorkloadEstimateResponse(Schema):
    """Response for workload estimation."""
    min_vram_gb: int
    recommended_vram_gb: int
    recommended_gpu_tiers: List[str]
    estimated_cost_range: Dict[str, float]
    estimated_time_per_unit: float
    confidence: float
    reasoning: List[str]


# ============================================
# GPU Benchmarks
# ============================================

class GPUBenchmarkSchema(Schema):
    """GPU benchmark data schema."""
    gpu_model: str
    tflops_fp32: float
    tflops_fp16: float
    tflops_int8: Optional[float] = None
    memory_bandwidth_gbps: float
    vram_gb: int
    tokens_per_second_7b: int
    tokens_per_second_13b: Optional[int] = None
    tokens_per_second_70b: Optional[int] = None
    image_gen_per_minute: Optional[int] = None
    source: str
    verified_at: Optional[datetime] = None


class BenchmarkListResponse(Schema):
    """Response for benchmark list."""
    benchmarks: List[GPUBenchmarkSchema]
    count: int

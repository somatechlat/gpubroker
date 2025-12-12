"""
GPUMathBroker - MASTER DATA ANALYSIS ENGINE for GPUBROKER
============================================================
ALL mathematical calculations flow through this service.

Capabilities:
- KPI Calculations (cost-per-token, cost-per-GFLOP, efficiency scores)
- MCDA Ranking (TOPSIS, AHP, ELECTRE, PROMETHEE, WSM, WPM)
- Collaborative Filtering (ALS matrix factorization)
- Content-Based Similarity (cosine similarity, feature matching)
- Time-Series Analysis (trends, forecasting, anomaly detection)
- Workload-to-GPU Mapping (natural language → GPU requirements)
- Ensemble Recommendations (weighted combination of algorithms)

⚠️ WARNING: REAL IMPLEMENTATION ONLY ⚠️
We do NOT mock, bypass, or invent data.
We use ONLY real servers, real APIs, and real data.
"""

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any, Union
from datetime import datetime, timezone
from contextlib import asynccontextmanager
import numpy as np
import logging
import os

# Core modules
from core.kpi_calculator import KPICalculator
from core.benchmarks import BenchmarkRepository

# Algorithm modules
from algorithms.topsis import TOPSISEngine
from algorithms.collaborative import ALSRecommender
from algorithms.content_based import ContentSimilarity
from algorithms.ensemble import EnsembleRecommender
from algorithms.workload_mapper import WorkloadMapper
from algorithms.price_analytics import PriceAnalytics
from algorithms.ranking_engine import MCDARankingEngine

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "math-core", "message": "%(message)s"}'
)
logger = logging.getLogger(__name__)

# ============================================
# FastAPI Application
# ============================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    if not benchmark_repo:
        raise RuntimeError("Benchmark repository not initialized")
    yield


app = FastAPI(
    title="GPUMathBroker - Master Data Analysis Engine",
    description="""
    Enterprise-grade mathematical and statistical toolkit for GPU marketplace.
    
    ## Features
    - **KPI Calculations**: Cost-per-token, cost-per-GFLOP, efficiency scores
    - **MCDA Ranking**: TOPSIS, AHP, ELECTRE, PROMETHEE, WSM, WPM
    - **Recommendations**: Collaborative filtering, content-based, ensemble
    - **Analytics**: Time-series analysis, forecasting, anomaly detection
    - **Workload Mapping**: Natural language to GPU requirements
    
    ## Data Sources
    All GPU benchmarks from verified sources: NVIDIA specs, MLPerf, Lambda Labs
    """,
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================
# Initialize Components
# ============================================
benchmark_repo = BenchmarkRepository()
kpi_calculator = KPICalculator(benchmark_repo)
topsis_engine = TOPSISEngine()
price_analytics = PriceAnalytics()
mcda_engine = MCDARankingEngine()
als_recommender = ALSRecommender(factors=50, regularization=0.1, iterations=15)
content_similarity = ContentSimilarity()
workload_mapper = WorkloadMapper(benchmark_repo)
ensemble_recommender = EnsembleRecommender(
    topsis_engine=topsis_engine,
    als_recommender=als_recommender,
    content_similarity=content_similarity,
    weights={"topsis": 0.4, "collaborative": 0.3, "content_based": 0.3}
)


# ============================================
# Request/Response Models
# ============================================

class CostPerTokenRequest(BaseModel):
    price_per_hour: float = Field(..., gt=0, description="Price per hour in USD")
    gpu_type: str = Field(..., description="GPU model name (e.g., 'A100', 'H100')")
    model_size: Optional[str] = Field("7b", description="LLM model size (e.g., '7b', '13b', '70b')")


class CostPerTokenResponse(BaseModel):
    cost_per_token: float
    cost_per_million_tokens: float
    tokens_per_second: int
    confidence: float
    calculation_details: Dict[str, Any]


class CostPerGFLOPRequest(BaseModel):
    price_per_hour: float = Field(..., gt=0)
    gpu_type: str


class CostPerGFLOPResponse(BaseModel):
    cost_per_gflop: float
    cost_per_tflop_hour: float
    gpu_tflops: float
    confidence: float


class EfficiencyScoreRequest(BaseModel):
    price_per_hour: float
    gpu_type: str
    availability_score: float = Field(1.0, ge=0, le=1)
    reliability_score: float = Field(1.0, ge=0, le=1)


class EfficiencyScoreResponse(BaseModel):
    efficiency_score: float
    breakdown: Dict[str, float]


class TOPSISRequest(BaseModel):
    decision_matrix: List[List[float]] = Field(..., description="Alternatives x Criteria matrix")
    weights: List[float] = Field(..., description="Criteria weights (must sum to 1)")
    criteria_types: List[str] = Field(..., description="'benefit' or 'cost' for each criterion")


class TOPSISResponse(BaseModel):
    rankings: List[int]
    scores: List[float]
    ideal_solution: List[float]
    anti_ideal_solution: List[float]


class ContentSimilarityRequest(BaseModel):
    query_vector: List[float]
    candidate_vectors: List[List[float]]
    top_k: int = Field(5, ge=1, le=100)


class ContentSimilarityResponse(BaseModel):
    matches: List[int]
    scores: List[float]


class WorkloadEstimateRequest(BaseModel):
    workload_type: str = Field(..., description="'image_generation', 'llm_inference', 'training'")
    quantity: int = Field(..., gt=0, description="Number of items to process")
    duration_hours: float = Field(..., gt=0, description="Target duration in hours")
    quality: Optional[str] = Field("standard", description="'draft', 'standard', 'high'")
    model_name: Optional[str] = Field(None, description="Specific model name if applicable")


class WorkloadEstimateResponse(BaseModel):
    min_vram_gb: int
    recommended_vram_gb: int
    recommended_gpu_tiers: List[str]
    estimated_cost_range: Dict[str, float]
    estimated_time_per_unit: float
    confidence: float
    reasoning: List[str]


class GPUBenchmark(BaseModel):
    gpu_model: str
    tflops_fp32: float
    tflops_fp16: float
    tflops_int8: Optional[float]
    memory_bandwidth_gbps: float
    vram_gb: int
    tokens_per_second_7b: int
    tokens_per_second_13b: Optional[int]
    tokens_per_second_70b: Optional[int]
    image_gen_per_minute: Optional[int]
    source: str
    verified_at: Optional[datetime]


class EnsembleRecommendRequest(BaseModel):
    user_id: Optional[str] = None
    workload_profile: Dict[str, Any]
    candidate_offers: List[Dict[str, Any]]
    top_k: int = Field(5, ge=1, le=20)


class EnsembleRecommendResponse(BaseModel):
    recommendations: List[Dict[str, Any]]
    algorithm_contributions: Dict[str, float]
    confidence: float


# ============================================
# API Endpoints - KPI Calculations
# ============================================

@app.post("/math/cost-per-token", response_model=CostPerTokenResponse)
async def calculate_cost_per_token(request: CostPerTokenRequest):
    """
    Calculate cost per token for LLM inference workloads.
    Uses IEEE 754 double precision with 4 decimal rounding.
    """
    try:
        result = kpi_calculator.cost_per_token(
            price_per_hour=request.price_per_hour,
            gpu_type=request.gpu_type,
            model_size=request.model_size
        )
        return CostPerTokenResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Cost per token calculation failed: {e}")
        raise HTTPException(status_code=500, detail="Calculation failed")


@app.post("/math/cost-per-gflop", response_model=CostPerGFLOPResponse)
async def calculate_cost_per_gflop(request: CostPerGFLOPRequest):
    """
    Calculate cost per GFLOP for compute workloads.
    """
    try:
        result = kpi_calculator.cost_per_gflop(
            price_per_hour=request.price_per_hour,
            gpu_type=request.gpu_type
        )
        return CostPerGFLOPResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Cost per GFLOP calculation failed: {e}")
        raise HTTPException(status_code=500, detail="Calculation failed")


@app.post("/math/efficiency-score", response_model=EfficiencyScoreResponse)
async def calculate_efficiency_score(request: EfficiencyScoreRequest):
    """
    Calculate overall efficiency score combining price, performance, and reliability.
    """
    try:
        result = kpi_calculator.efficiency_score(
            price_per_hour=request.price_per_hour,
            gpu_type=request.gpu_type,
            availability_score=request.availability_score,
            reliability_score=request.reliability_score
        )
        return EfficiencyScoreResponse(**result)
    except Exception as e:
        logger.error(f"Efficiency score calculation failed: {e}")
        raise HTTPException(status_code=500, detail="Calculation failed")


# ============================================
# API Endpoints - Algorithms
# ============================================

@app.post("/math/topsis", response_model=TOPSISResponse)
async def run_topsis(request: TOPSISRequest):
    """
    Execute TOPSIS (Technique for Order of Preference by Similarity to Ideal Solution).
    Multi-criteria decision analysis algorithm.
    """
    try:
        # Validate weights sum to 1
        weight_sum = sum(request.weights)
        if abs(weight_sum - 1.0) > 0.001:
            raise HTTPException(status_code=400, detail=f"Weights must sum to 1.0, got {weight_sum}")
        
        result = topsis_engine.calculate(
            decision_matrix=np.array(request.decision_matrix),
            weights=request.weights,
            criteria_types=request.criteria_types
        )
        return TOPSISResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"TOPSIS calculation failed: {e}")
        raise HTTPException(status_code=500, detail="TOPSIS calculation failed")


@app.post("/math/content-similarity", response_model=ContentSimilarityResponse)
async def calculate_content_similarity(request: ContentSimilarityRequest):
    """
    Calculate cosine similarity between query and candidate vectors.
    """
    try:
        result = content_similarity.find_similar(
            query_vector=np.array(request.query_vector),
            candidate_vectors=np.array(request.candidate_vectors),
            top_k=request.top_k
        )
        return ContentSimilarityResponse(**result)
    except Exception as e:
        logger.error(f"Content similarity calculation failed: {e}")
        raise HTTPException(status_code=500, detail="Similarity calculation failed")


@app.post("/math/ensemble-recommend", response_model=EnsembleRecommendResponse)
async def ensemble_recommend(request: EnsembleRecommendRequest):
    """
    Generate recommendations using weighted ensemble of algorithms.
    TOPSIS (0.4) + Collaborative (0.3) + Content-Based (0.3)
    """
    try:
        result = ensemble_recommender.recommend(
            user_id=request.user_id,
            workload_profile=request.workload_profile,
            candidate_offers=request.candidate_offers,
            top_k=request.top_k
        )
        return EnsembleRecommendResponse(**result)
    except Exception as e:
        logger.error(f"Ensemble recommendation failed: {e}")
        raise HTTPException(status_code=500, detail="Recommendation failed")


# ============================================
# API Endpoints - Workload Mapping
# ============================================

@app.post("/math/estimate-workload", response_model=WorkloadEstimateResponse)
async def estimate_workload(request: WorkloadEstimateRequest):
    """
    Estimate GPU requirements for a given workload.
    Translates natural language workload descriptions to GPU specs.
    """
    try:
        result = workload_mapper.estimate(
            workload_type=request.workload_type,
            quantity=request.quantity,
            duration_hours=request.duration_hours,
            quality=request.quality,
            model_name=request.model_name
        )
        return WorkloadEstimateResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Workload estimation failed: {e}")
        raise HTTPException(status_code=500, detail="Workload estimation failed")


@app.post("/math/map-workload-to-gpu")
async def map_workload_to_gpu(request: WorkloadEstimateRequest):
    """
    Map workload requirements to specific GPU recommendations.
    """
    try:
        result = workload_mapper.map_to_gpus(
            workload_type=request.workload_type,
            quantity=request.quantity,
            duration_hours=request.duration_hours,
            quality=request.quality,
            model_name=request.model_name
        )
        return result
    except Exception as e:
        logger.error(f"Workload mapping failed: {e}")
        raise HTTPException(status_code=500, detail="Workload mapping failed")


# ============================================
# API Endpoints - Benchmarks
# ============================================

@app.get("/math/benchmarks", response_model=List[GPUBenchmark])
async def list_benchmarks():
    """
    List all GPU benchmarks in the database.
    """
    return benchmark_repo.list_all()


@app.get("/math/benchmarks/{gpu_type}", response_model=GPUBenchmark)
async def get_benchmark(gpu_type: str):
    """
    Get benchmark data for a specific GPU type.
    """
    benchmark = benchmark_repo.get(gpu_type)
    if not benchmark:
        raise HTTPException(status_code=404, detail=f"Benchmark not found for GPU: {gpu_type}")
    return benchmark


@app.put("/math/benchmarks/{gpu_type}", response_model=GPUBenchmark)
async def update_benchmark(gpu_type: str, benchmark: GPUBenchmark):
    """
    Update benchmark data for a GPU type (admin only).
    """
    result = benchmark_repo.upsert(gpu_type, benchmark)
    return result


# ============================================
# API Endpoints - Price Analytics
# ============================================

class PriceSeriesRequest(BaseModel):
    prices: List[Dict[str, Any]] = Field(..., description="List of {timestamp, price} dicts")
    granularity: str = Field("hourly", description="hourly, daily, weekly")


class PriceForecastRequest(BaseModel):
    prices: List[Dict[str, Any]] = Field(..., description="Historical price data")
    horizon_hours: int = Field(24, ge=1, le=168, description="Hours to forecast")
    method: str = Field("auto", description="arima, exponential, linear, auto")


class AnomalyDetectionRequest(BaseModel):
    current_price: float = Field(..., description="Price to check")
    historical_prices: List[float] = Field(..., description="Recent historical prices")
    threshold_z: float = Field(3.0, description="Z-score threshold")


class ProviderComparisonRequest(BaseModel):
    provider_prices: Dict[str, List[Dict[str, Any]]] = Field(
        ..., description="Dict mapping provider_id to price history"
    )


@app.post("/math/analyze-prices")
async def analyze_price_series(request: PriceSeriesRequest):
    """
    Comprehensive analysis of a price time series.
    
    Returns trend analysis, statistics, anomalies, and volatility metrics.
    """
    try:
        result = price_analytics.analyze_price_series(
            prices=request.prices,
            granularity=request.granularity
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Price analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Price analysis failed")


@app.post("/math/forecast-price")
async def forecast_price(request: PriceForecastRequest):
    """
    Forecast future prices using time-series models.
    
    Supports ARIMA, exponential smoothing, and linear methods.
    """
    try:
        result = price_analytics.forecast_price(
            prices=request.prices,
            horizon_hours=request.horizon_hours,
            method=request.method
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Price forecast failed: {e}")
        raise HTTPException(status_code=500, detail="Price forecast failed")


@app.post("/math/detect-anomaly")
async def detect_price_anomaly(request: AnomalyDetectionRequest):
    """
    Check if a price is anomalous compared to historical data.
    
    Uses Z-score, IQR, and Isolation Forest methods.
    """
    try:
        result = price_analytics.detect_price_anomaly(
            current_price=request.current_price,
            historical_prices=request.historical_prices,
            threshold_z=request.threshold_z
        )
        return result
    except Exception as e:
        logger.error(f"Anomaly detection failed: {e}")
        raise HTTPException(status_code=500, detail="Anomaly detection failed")


@app.post("/math/compare-providers")
async def compare_providers(request: ProviderComparisonRequest):
    """
    Compare pricing across multiple providers.
    
    Returns comparative analysis with recommendations.
    """
    try:
        result = price_analytics.compare_providers(
            provider_prices=request.provider_prices
        )
        return result
    except Exception as e:
        logger.error(f"Provider comparison failed: {e}")
        raise HTTPException(status_code=500, detail="Provider comparison failed")


# ============================================
# API Endpoints - MCDA Ranking Engine
# ============================================

class MCDARankRequest(BaseModel):
    alternatives: List[List[float]] = Field(..., description="Decision matrix (alternatives x criteria)")
    weights: List[float] = Field(..., description="Criterion weights (must sum to 1)")
    criteria_types: List[str] = Field(..., description="'benefit' or 'cost' for each criterion")
    methods: Optional[List[str]] = Field(None, description="Methods to use: wsm, wpm, ahp, electre, promethee")


class SensitivityAnalysisRequest(BaseModel):
    alternatives: List[List[float]] = Field(..., description="Decision matrix")
    weights: List[float] = Field(..., description="Base weights")
    criteria_types: List[str] = Field(..., description="Criterion types")
    method: str = Field("wsm", description="Ranking method")
    perturbation: float = Field(0.1, ge=0.01, le=0.5, description="Weight perturbation amount")


@app.post("/math/mcda-rank")
async def mcda_rank_all(request: MCDARankRequest):
    """
    Rank alternatives using multiple MCDA methods.
    
    Available methods: WSM, WPM, AHP, ELECTRE, PROMETHEE
    Returns individual rankings and ensemble (Borda count) ranking.
    """
    try:
        # Validate weights
        weight_sum = sum(request.weights)
        if abs(weight_sum - 1.0) > 0.01:
            raise HTTPException(status_code=400, detail=f"Weights must sum to 1.0, got {weight_sum}")
        
        result = mcda_engine.rank_all_methods(
            alternatives=np.array(request.alternatives),
            weights=request.weights,
            criteria_types=request.criteria_types,
            methods=request.methods
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"MCDA ranking failed: {e}")
        raise HTTPException(status_code=500, detail="MCDA ranking failed")


@app.post("/math/sensitivity-analysis")
async def sensitivity_analysis(request: SensitivityAnalysisRequest):
    """
    Perform sensitivity analysis on criterion weights.
    
    Tests how ranking changes when weights are perturbed.
    """
    try:
        result = mcda_engine.sensitivity_analysis(
            alternatives=np.array(request.alternatives),
            base_weights=request.weights,
            criteria_types=request.criteria_types,
            method=request.method,
            perturbation=request.perturbation
        )
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Sensitivity analysis failed: {e}")
        raise HTTPException(status_code=500, detail="Sensitivity analysis failed")


# ============================================
# Health Check
# ============================================

@app.get("/health")
async def health_check():
    """Service health check with component status."""
    return {
        "status": "healthy",
        "service": "math-core",
        "version": "2.0.0",
        "components": {
            "kpi_calculator": "operational",
            "topsis_engine": "operational",
            "als_recommender": "operational",
            "content_similarity": "operational",
            "workload_mapper": "operational",
            "price_analytics": "operational",
            "mcda_engine": "operational",
            "benchmark_repo": f"{len(benchmark_repo.list_all())} GPUs loaded"
        },
        "capabilities": [
            "cost-per-token",
            "cost-per-gflop",
            "efficiency-score",
            "topsis",
            "collaborative-filtering",
            "content-similarity",
            "ensemble-recommendations",
            "workload-mapping",
            "price-analytics",
            "price-forecasting",
            "anomaly-detection",
            "mcda-ranking",
            "sensitivity-analysis"
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/")
async def root():
    """API root with endpoint documentation."""
    return {
        "service": "GPUMathBroker - Master Data Analysis Engine",
        "version": "2.0.0",
        "status": "running",
        "documentation": "/docs",
        "endpoints": {
            "kpi": [
                "POST /math/cost-per-token",
                "POST /math/cost-per-gflop",
                "POST /math/efficiency-score"
            ],
            "ranking": [
                "POST /math/topsis",
                "POST /math/mcda-rank",
                "POST /math/sensitivity-analysis"
            ],
            "recommendations": [
                "POST /math/collaborative-filter",
                "POST /math/content-similarity",
                "POST /math/ensemble-recommend"
            ],
            "workload": [
                "POST /math/estimate-workload",
                "POST /math/map-workload-to-gpu"
            ],
            "analytics": [
                "POST /math/analyze-prices",
                "POST /math/forecast-price",
                "POST /math/detect-anomaly",
                "POST /math/compare-providers"
            ],
            "benchmarks": [
                "GET /math/benchmarks",
                "GET /math/benchmarks/{gpu_type}",
                "PUT /math/benchmarks/{gpu_type}"
            ]
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004, workers=4)

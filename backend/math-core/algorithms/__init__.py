"""
GPUMathBroker - Mathematical Algorithms Module
===============================================
Enterprise-grade algorithms for GPU marketplace recommendations.

Modules:
- TOPSIS: Multi-criteria decision analysis
- Collaborative: ALS matrix factorization
- Content-Based: Cosine similarity matching
- Ensemble: Weighted algorithm combination
- Workload Mapper: Natural language to GPU requirements
- Price Analytics: Time-series analysis, forecasting, anomaly detection
- Ranking Engine: Multiple MCDA methods (WSM, WPM, AHP, ELECTRE, PROMETHEE)
"""

from .topsis import TOPSISEngine
from .collaborative import ALSRecommender
from .content_based import ContentSimilarity
from .ensemble import EnsembleRecommender
from .workload_mapper import WorkloadMapper
from .price_analytics import PriceAnalytics
from .ranking_engine import (
    MCDARankingEngine,
    WeightedSumModel,
    WeightedProductModel,
    AHPRanker,
    ELECTRERanker,
    PROMETHEERanker
)

__all__ = [
    # Core algorithms
    "TOPSISEngine",
    "ALSRecommender", 
    "ContentSimilarity",
    "EnsembleRecommender",
    "WorkloadMapper",
    # Analytics
    "PriceAnalytics",
    # MCDA Ranking
    "MCDARankingEngine",
    "WeightedSumModel",
    "WeightedProductModel",
    "AHPRanker",
    "ELECTRERanker",
    "PROMETHEERanker"
]

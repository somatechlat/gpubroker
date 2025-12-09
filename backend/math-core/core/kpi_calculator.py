"""
KPI Calculator - Cost and efficiency calculations for GPU offers.

ALL calculations use IEEE 754 double precision with 4 decimal rounding.
This module is the single source of truth for KPI calculations.
"""

from typing import Dict, Any, Optional
from decimal import Decimal, ROUND_HALF_UP
import math
import logging

from .benchmarks import BenchmarkRepository

logger = logging.getLogger(__name__)


class KPICalculator:
    """
    Centralized KPI calculation engine.
    
    All mathematical calculations for cost metrics flow through this class.
    Uses verified GPU benchmark data for accurate calculations.
    """
    
    def __init__(self, benchmark_repo: BenchmarkRepository):
        self.benchmark_repo = benchmark_repo
    
    def _round_price(self, value: float, decimals: int = 4) -> float:
        """
        Round price to specified decimal places using banker's rounding.
        IEEE 754 compliant.
        """
        if math.isnan(value) or math.isinf(value):
            raise ValueError(f"Invalid value for rounding: {value}")
        
        d = Decimal(str(value))
        rounded = d.quantize(Decimal(10) ** -decimals, rounding=ROUND_HALF_UP)
        return float(rounded)
    
    def cost_per_token(
        self,
        price_per_hour: float,
        gpu_type: str,
        model_size: str = "7b"
    ) -> Dict[str, Any]:
        """
        Calculate cost per token for LLM inference.
        
        Formula: cost_per_token = price_per_hour / (tokens_per_second * 3600)
        
        Args:
            price_per_hour: GPU rental price in USD/hour
            gpu_type: GPU model name (e.g., 'A100', 'H100')
            model_size: LLM model size ('7b', '13b', '70b')
        
        Returns:
            Dict with cost_per_token, cost_per_million_tokens, and calculation details
        """
        if price_per_hour <= 0:
            raise ValueError("price_per_hour must be positive")
        
        # Get benchmark data
        tokens_per_second = self.benchmark_repo.get_tokens_per_second(gpu_type, model_size)
        
        if tokens_per_second is None or tokens_per_second <= 0:
            # Fallback: conservative estimate based on GPU class
            tokens_per_second = self._estimate_tokens_per_second(gpu_type, model_size)
            confidence = 0.6
            logger.warning(f"Using estimated TPS for {gpu_type}: {tokens_per_second}")
        else:
            confidence = 0.95
        
        # Calculate tokens per hour
        tokens_per_hour = tokens_per_second * 3600
        
        # Calculate cost per token (IEEE 754 double precision)
        # IMPORTANT: Do NOT round this value - it must preserve mathematical properties
        # such as linear scaling (2x price = 2x cost_per_token)
        cost_per_token = price_per_hour / tokens_per_hour
        
        # Calculate cost per million tokens from the unrounded value
        cost_per_million = cost_per_token * 1_000_000
        
        return {
            # Return unrounded cost_per_token to preserve mathematical invariants
            # (e.g., doubling price must exactly double cost_per_token)
            "cost_per_token": cost_per_token,
            # cost_per_million_tokens is rounded for display purposes only
            "cost_per_million_tokens": self._round_price(cost_per_million, 4),
            "tokens_per_second": tokens_per_second,
            "confidence": confidence,
            "calculation_details": {
                "price_per_hour": price_per_hour,
                "gpu_type": gpu_type,
                "model_size": model_size,
                "tokens_per_hour": tokens_per_hour,
                "formula": "price_per_hour / (tokens_per_second * 3600)"
            }
        }
    
    def _estimate_tokens_per_second(self, gpu_type: str, model_size: str) -> int:
        """
        Estimate tokens per second when benchmark data is unavailable.
        Uses conservative estimates based on GPU naming patterns.
        """
        gpu_upper = gpu_type.upper()
        
        # Base estimates by GPU class
        base_estimates = {
            "H100": 3000,
            "A100": 1800,
            "A10": 700,
            "A6000": 1000,
            "V100": 700,
            "4090": 1100,
            "4080": 850,
            "3090": 550,
            "3080": 400,
            "T4": 140,
            "L40": 1400,
            "L4": 450,
        }
        
        # Find matching base estimate
        base_tps = 500  # Default conservative estimate
        for key, value in base_estimates.items():
            if key in gpu_upper:
                base_tps = value
                break
        
        # Adjust for model size
        size_multipliers = {
            "7b": 1.0,
            "13b": 0.6,
            "70b": 0.15,
        }
        multiplier = size_multipliers.get(model_size.lower(), 1.0)
        
        return int(base_tps * multiplier)
    
    def cost_per_gflop(
        self,
        price_per_hour: float,
        gpu_type: str,
        precision: str = "fp32"
    ) -> Dict[str, Any]:
        """
        Calculate cost per GFLOP for compute workloads.
        
        Formula: cost_per_gflop = price_per_hour / (tflops * 1000)
        
        Args:
            price_per_hour: GPU rental price in USD/hour
            gpu_type: GPU model name
            precision: Compute precision ('fp32', 'fp16', 'int8')
        
        Returns:
            Dict with cost_per_gflop and calculation details
        """
        if price_per_hour <= 0:
            raise ValueError("price_per_hour must be positive")
        
        # Get TFLOPS from benchmark
        tflops = self.benchmark_repo.get_tflops(gpu_type, precision)
        
        if tflops is None or tflops <= 0:
            # Fallback estimate
            tflops = self._estimate_tflops(gpu_type, precision)
            confidence = 0.6
            logger.warning(f"Using estimated TFLOPS for {gpu_type}: {tflops}")
        else:
            confidence = 0.95
        
        # Convert TFLOPS to GFLOPS (1 TFLOP = 1000 GFLOPS)
        gflops = tflops * 1000
        
        # Cost per GFLOP-hour
        cost_per_gflop = price_per_hour / gflops
        
        # Cost per TFLOP-hour (more practical unit)
        cost_per_tflop_hour = price_per_hour / tflops
        
        return {
            "cost_per_gflop": self._round_price(cost_per_gflop, 8),
            "cost_per_tflop_hour": self._round_price(cost_per_tflop_hour, 4),
            "gpu_tflops": tflops,
            "confidence": confidence
        }
    
    def _estimate_tflops(self, gpu_type: str, precision: str) -> float:
        """Estimate TFLOPS when benchmark data is unavailable."""
        gpu_upper = gpu_type.upper()
        
        # Base FP32 estimates
        base_estimates = {
            "H100": 60.0,
            "A100": 19.0,
            "A10": 30.0,
            "A6000": 38.0,
            "V100": 15.0,
            "4090": 80.0,
            "4080": 48.0,
            "3090": 35.0,
            "3080": 29.0,
            "T4": 8.0,
            "L40": 90.0,
            "L4": 30.0,
        }
        
        base_tflops = 10.0  # Default
        for key, value in base_estimates.items():
            if key in gpu_upper:
                base_tflops = value
                break
        
        # Precision multipliers (approximate)
        precision_multipliers = {
            "fp32": 1.0,
            "fp16": 4.0,  # Tensor cores
            "int8": 8.0,
        }
        multiplier = precision_multipliers.get(precision.lower(), 1.0)
        
        return base_tflops * multiplier
    
    def efficiency_score(
        self,
        price_per_hour: float,
        gpu_type: str,
        availability_score: float = 1.0,
        reliability_score: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate overall efficiency score combining multiple factors.
        
        Score = (performance_score * 0.4) + (price_score * 0.35) + 
                (availability_score * 0.15) + (reliability_score * 0.1)
        
        Args:
            price_per_hour: GPU rental price
            gpu_type: GPU model name
            availability_score: 0-1 availability rating
            reliability_score: 0-1 reliability rating
        
        Returns:
            Dict with efficiency_score and breakdown
        """
        # Get benchmark for performance scoring
        benchmark = self.benchmark_repo.get(gpu_type)
        
        if benchmark:
            # Normalize performance (0-1 scale, H100 = 1.0)
            max_tflops = 67.0  # H100 SXM FP32
            performance_score = min(benchmark.tflops_fp32 / max_tflops, 1.0)
            
            # Price score (inverse, lower is better)
            # Normalize against typical range $0.50 - $5.00/hr
            price_normalized = max(0, min((5.0 - price_per_hour) / 4.5, 1.0))
            price_score = price_normalized
        else:
            performance_score = 0.5  # Unknown GPU
            price_score = max(0, min((3.0 - price_per_hour) / 2.5, 1.0))
        
        # Validate input scores
        availability_score = max(0, min(availability_score, 1.0))
        reliability_score = max(0, min(reliability_score, 1.0))
        
        # Weighted combination
        weights = {
            "performance": 0.40,
            "price": 0.35,
            "availability": 0.15,
            "reliability": 0.10
        }
        
        efficiency_score = (
            performance_score * weights["performance"] +
            price_score * weights["price"] +
            availability_score * weights["availability"] +
            reliability_score * weights["reliability"]
        )
        
        return {
            "efficiency_score": self._round_price(efficiency_score, 4),
            "breakdown": {
                "performance_score": self._round_price(performance_score, 4),
                "price_score": self._round_price(price_score, 4),
                "availability_score": self._round_price(availability_score, 4),
                "reliability_score": self._round_price(reliability_score, 4),
                "weights": weights
            }
        }

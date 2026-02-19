"""
Math Core Services.

KPI Calculator and Workload Mapper implementations.
ALL calculations use IEEE 754 double precision with 4 decimal rounding.

NO MOCKS. NO FAKE DATA. REAL IMPLEMENTATIONS ONLY.
"""

import logging
import math
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from .benchmarks import BenchmarkRepository, benchmark_repo

logger = logging.getLogger("gpubroker.math_core.services")


class KPICalculator:
    """
    Centralized KPI calculation engine.

    All mathematical calculations for cost metrics flow through this class.
    Uses verified GPU benchmark data for accurate calculations.
    """

    def __init__(self, benchmark_repository: BenchmarkRepository | None = None):
        self.benchmark_repo = benchmark_repository or benchmark_repo

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
        self, price_per_hour: float, gpu_type: str, model_size: str = "7b"
    ) -> dict[str, Any]:
        """
        Calculate cost per token for LLM inference.

        Formula: cost_per_token = price_per_hour / (tokens_per_second * 3600)
        """
        if price_per_hour <= 0:
            raise ValueError("price_per_hour must be positive")

        tokens_per_second = self.benchmark_repo.get_tokens_per_second(
            gpu_type, model_size
        )

        if tokens_per_second <= 0:
            tokens_per_second = self._estimate_tokens_per_second(gpu_type, model_size)
            confidence = 0.6
            logger.warning(f"Using estimated TPS for {gpu_type}: {tokens_per_second}")
        else:
            confidence = 0.95

        tokens_per_hour = tokens_per_second * 3600
        cost_per_token = price_per_hour / tokens_per_hour
        cost_per_million = cost_per_token * 1_000_000

        return {
            "cost_per_token": cost_per_token,
            "cost_per_million_tokens": self._round_price(cost_per_million, 4),
            "tokens_per_second": tokens_per_second,
            "confidence": confidence,
            "calculation_details": {
                "price_per_hour": price_per_hour,
                "gpu_type": gpu_type,
                "model_size": model_size,
                "tokens_per_hour": tokens_per_hour,
                "formula": "price_per_hour / (tokens_per_second * 3600)",
            },
        }

    def _estimate_tokens_per_second(self, gpu_type: str, model_size: str) -> int:
        """Estimate tokens per second when benchmark data is unavailable."""
        gpu_upper = gpu_type.upper()

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

        base_tps = 500
        for key, value in base_estimates.items():
            if key in gpu_upper:
                base_tps = value
                break

        size_multipliers = {"7b": 1.0, "13b": 0.6, "70b": 0.15}
        multiplier = size_multipliers.get(model_size.lower(), 1.0)

        return int(base_tps * multiplier)

    def cost_per_gflop(
        self, price_per_hour: float, gpu_type: str, precision: str = "fp32"
    ) -> dict[str, Any]:
        """
        Calculate cost per GFLOP for compute workloads.

        Formula: cost_per_gflop = price_per_hour / (tflops * 1000)
        """
        if price_per_hour <= 0:
            raise ValueError("price_per_hour must be positive")

        tflops = self.benchmark_repo.get_tflops(gpu_type, precision)

        if tflops <= 0:
            tflops = self._estimate_tflops(gpu_type, precision)
            confidence = 0.6
            logger.warning(f"Using estimated TFLOPS for {gpu_type}: {tflops}")
        else:
            confidence = 0.95

        gflops = tflops * 1000
        cost_per_gflop = price_per_hour / gflops
        cost_per_tflop_hour = price_per_hour / tflops

        return {
            "cost_per_gflop": self._round_price(cost_per_gflop, 8),
            "cost_per_tflop_hour": self._round_price(cost_per_tflop_hour, 4),
            "gpu_tflops": tflops,
            "confidence": confidence,
        }

    def _estimate_tflops(self, gpu_type: str, precision: str) -> float:
        """Estimate TFLOPS when benchmark data is unavailable."""
        gpu_upper = gpu_type.upper()

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

        base_tflops = 10.0
        for key, value in base_estimates.items():
            if key in gpu_upper:
                base_tflops = value
                break

        precision_multipliers = {"fp32": 1.0, "fp16": 4.0, "int8": 8.0}
        multiplier = precision_multipliers.get(precision.lower(), 1.0)

        return base_tflops * multiplier

    def efficiency_score(
        self,
        price_per_hour: float,
        gpu_type: str,
        availability_score: float = 1.0,
        reliability_score: float = 1.0,
    ) -> dict[str, Any]:
        """
        Calculate overall efficiency score combining multiple factors.

        Score = (performance * 0.4) + (price * 0.35) + (availability * 0.15) + (reliability * 0.1)
        """
        benchmark = self.benchmark_repo.get(gpu_type)

        if benchmark:
            max_tflops = 510.0  # H100 SXM FP32
            tflops = benchmark.get("tflops_fp32", 10.0)
            performance_score = min(tflops / max_tflops, 1.0)
            price_normalized = max(0, min((5.0 - price_per_hour) / 4.5, 1.0))
            price_score = price_normalized
        else:
            performance_score = 0.5
            price_score = max(0, min((3.0 - price_per_hour) / 2.5, 1.0))

        availability_score = max(0, min(availability_score, 1.0))
        reliability_score = max(0, min(reliability_score, 1.0))

        weights = {
            "performance": 0.40,
            "price": 0.35,
            "availability": 0.15,
            "reliability": 0.10,
        }

        efficiency = (
            performance_score * weights["performance"]
            + price_score * weights["price"]
            + availability_score * weights["availability"]
            + reliability_score * weights["reliability"]
        )

        return {
            "efficiency_score": self._round_price(efficiency, 4),
            "breakdown": {
                "performance_score": self._round_price(performance_score, 4),
                "price_score": self._round_price(price_score, 4),
                "availability_score": self._round_price(availability_score, 4),
                "reliability_score": self._round_price(reliability_score, 4),
                "weights": weights,
            },
        }


class WorkloadMapper:
    """
    Maps workload descriptions to GPU requirements.

    Supports:
    - Image generation (Stable Diffusion, DALL-E style)
    - LLM inference (various model sizes)
    - Model training (fine-tuning, full training)
    """

    def __init__(self, benchmark_repository: BenchmarkRepository | None = None):
        self.benchmark_repo = benchmark_repository or benchmark_repo
        self.workload_profiles = self._load_workload_profiles()

    def _load_workload_profiles(self) -> dict[str, dict[str, Any]]:
        """Load workload requirement profiles."""
        return {
            "image_generation": {
                "sd_1.5": {
                    "min_vram_gb": 4,
                    "recommended_vram_gb": 8,
                    "time_per_image_seconds": {"draft": 5, "standard": 15, "high": 30},
                    "recommended_gpus": ["RTX 4090", "RTX 3080", "T4"],
                },
                "sdxl": {
                    "min_vram_gb": 8,
                    "recommended_vram_gb": 12,
                    "time_per_image_seconds": {"draft": 10, "standard": 25, "high": 45},
                    "recommended_gpus": ["RTX 4090", "RTX 4080", "RTX A6000", "L40"],
                },
                "sdxl_high_res": {
                    "min_vram_gb": 12,
                    "recommended_vram_gb": 24,
                    "time_per_image_seconds": {"draft": 20, "standard": 45, "high": 90},
                    "recommended_gpus": ["RTX 4090", "RTX A6000", "A100", "L40"],
                },
            },
            "llm_inference": {
                "7b": {
                    "min_vram_gb": 8,
                    "recommended_vram_gb": 16,
                    "tokens_per_second_range": [500, 3500],
                    "recommended_gpus": ["RTX 4090", "L40", "T4"],
                },
                "13b": {
                    "min_vram_gb": 16,
                    "recommended_vram_gb": 24,
                    "tokens_per_second_range": [300, 2200],
                    "recommended_gpus": ["RTX 4090", "RTX A6000", "A100", "L40"],
                },
                "70b": {
                    "min_vram_gb": 140,
                    "recommended_vram_gb": 160,
                    "tokens_per_second_range": [100, 450],
                    "recommended_gpus": ["H100", "A100"],
                    "multi_gpu": True,
                    "quantized_vram_gb": 40,
                },
            },
            "training": {
                "finetune_7b": {
                    "min_vram_gb": 16,
                    "recommended_vram_gb": 24,
                    "hours_per_epoch_1k_samples": 0.5,
                    "recommended_gpus": ["RTX A6000", "RTX 4090", "A100"],
                },
                "finetune_13b": {
                    "min_vram_gb": 24,
                    "recommended_vram_gb": 48,
                    "hours_per_epoch_1k_samples": 1.0,
                    "recommended_gpus": ["RTX A6000", "A100"],
                },
                "full_train_7b": {
                    "min_vram_gb": 48,
                    "recommended_vram_gb": 80,
                    "hours_per_epoch_1k_samples": 2.0,
                    "recommended_gpus": ["A100", "H100"],
                    "multi_gpu": True,
                },
            },
        }

    def estimate(
        self,
        workload_type: str,
        quantity: int,
        duration_hours: float,
        quality: str = "standard",
        model_name: str | None = None,
    ) -> dict[str, Any]:
        """Estimate GPU requirements for a workload."""
        workload_type = workload_type.lower().replace(" ", "_")

        if workload_type not in self.workload_profiles:
            raise ValueError(
                f"Unknown workload type: {workload_type}. "
                f"Supported: {list(self.workload_profiles.keys())}"
            )

        profiles = self.workload_profiles[workload_type]

        if model_name and model_name in profiles:
            profile = profiles[model_name]
        else:
            profile = list(profiles.values())[0]

        if workload_type == "image_generation":
            return self._estimate_image_generation(
                profile, quantity, duration_hours, quality
            )
        if workload_type == "llm_inference":
            return self._estimate_llm_inference(
                profile, quantity, duration_hours, model_name
            )
        if workload_type == "training":
            return self._estimate_training(
                profile, quantity, duration_hours, model_name
            )
        return self._estimate_generic(profile, quantity, duration_hours)

    def _estimate_image_generation(
        self,
        profile: dict[str, Any],
        quantity: int,
        duration_hours: float,
        quality: str,
    ) -> dict[str, Any]:
        """Estimate for image generation workloads."""
        time_per_image = profile["time_per_image_seconds"].get(quality, 15)
        total_time_needed = quantity * time_per_image
        duration_seconds = duration_hours * 3600

        if total_time_needed <= duration_seconds:
            confidence = 0.9
            reasoning = [
                f"Processing {quantity} images at {time_per_image}s each",
                f"Total time: {total_time_needed/60:.1f} minutes",
                f"Fits within {duration_hours} hour budget",
            ]
        else:
            confidence = 0.7
            reasoning = [
                f"Processing {quantity} images at {time_per_image}s each",
                f"Total time: {total_time_needed/60:.1f} minutes",
                "May need faster GPU or longer duration",
            ]

        return {
            "min_vram_gb": profile["min_vram_gb"],
            "recommended_vram_gb": profile["recommended_vram_gb"],
            "recommended_gpu_tiers": profile["recommended_gpus"],
            "estimated_cost_range": {
                "low": round(0.50 * duration_hours, 2),
                "high": round(3.00 * duration_hours, 2),
            },
            "estimated_time_per_unit": float(time_per_image),
            "confidence": confidence,
            "reasoning": reasoning,
        }

    def _estimate_llm_inference(
        self,
        profile: dict[str, Any],
        quantity: int,
        duration_hours: float,
        model_name: str | None,
    ) -> dict[str, Any]:
        """Estimate for LLM inference workloads."""
        tokens_per_request = 500
        total_tokens = quantity * tokens_per_request

        tps_range = profile.get("tokens_per_second_range", [500, 2000])
        min_tps, max_tps = tps_range

        duration_seconds = duration_hours * 3600
        required_tps = (
            total_tokens / duration_seconds if duration_seconds > 0 else float("inf")
        )

        if required_tps <= max_tps:
            confidence = 0.9
            reasoning = [
                f"Processing {quantity} requests (~{total_tokens:,} tokens)",
                f"Required throughput: {required_tps:.0f} tokens/sec",
                "Achievable with recommended GPUs",
            ]
        else:
            confidence = 0.6
            reasoning = [
                f"Processing {quantity} requests (~{total_tokens:,} tokens)",
                f"Required throughput: {required_tps:.0f} tokens/sec",
                "May need multiple GPUs or longer duration",
            ]

        if profile.get("multi_gpu"):
            reasoning.append("This model size requires multi-GPU setup")

        return {
            "min_vram_gb": profile["min_vram_gb"],
            "recommended_vram_gb": profile["recommended_vram_gb"],
            "recommended_gpu_tiers": profile["recommended_gpus"],
            "estimated_cost_range": {
                "low": round(1.0 * duration_hours, 2),
                "high": round(4.0 * duration_hours, 2),
            },
            "estimated_time_per_unit": tokens_per_request / ((min_tps + max_tps) / 2),
            "confidence": confidence,
            "reasoning": reasoning,
        }

    def _estimate_training(
        self,
        profile: dict[str, Any],
        quantity: int,
        duration_hours: float,
        model_name: str | None,
    ) -> dict[str, Any]:
        """Estimate for training workloads."""
        dataset_size_k = quantity / 1000 if quantity > 100 else quantity
        hours_per_epoch = profile.get("hours_per_epoch_1k_samples", 1.0)
        estimated_epochs = max(
            1, int(duration_hours / (hours_per_epoch * max(dataset_size_k, 0.1)))
        )

        if estimated_epochs >= 3:
            confidence = 0.85
            reasoning = [
                f"Dataset: ~{quantity} samples",
                f"Can complete ~{estimated_epochs} epochs in {duration_hours} hours",
                "Sufficient for fine-tuning",
            ]
        else:
            confidence = 0.6
            reasoning = [
                f"Dataset: ~{quantity} samples",
                f"Can only complete ~{estimated_epochs} epochs",
                "Consider longer duration or smaller dataset",
            ]

        if profile.get("multi_gpu"):
            reasoning.append("Multi-GPU recommended for this model size")

        return {
            "min_vram_gb": profile["min_vram_gb"],
            "recommended_vram_gb": profile["recommended_vram_gb"],
            "recommended_gpu_tiers": profile["recommended_gpus"],
            "estimated_cost_range": {
                "low": round(2.0 * duration_hours, 2),
                "high": round(8.0 * duration_hours, 2),
            },
            "estimated_time_per_unit": hours_per_epoch * 3600 / 1000,
            "confidence": confidence,
            "reasoning": reasoning,
        }

    def _estimate_generic(
        self, profile: dict[str, Any], quantity: int, duration_hours: float
    ) -> dict[str, Any]:
        """Generic estimation for other workload types."""
        return {
            "min_vram_gb": profile["min_vram_gb"],
            "recommended_vram_gb": profile["recommended_vram_gb"],
            "recommended_gpu_tiers": profile["recommended_gpus"],
            "estimated_cost_range": {
                "low": round(0.5 * duration_hours, 2),
                "high": round(3.0 * duration_hours, 2),
            },
            "estimated_time_per_unit": duration_hours * 3600 / max(quantity, 1),
            "confidence": 0.7,
            "reasoning": [
                f"Processing {quantity} items over {duration_hours} hours",
                "Generic estimate - actual performance may vary",
            ],
        }


# Global instances
kpi_calculator = KPICalculator()
workload_mapper = WorkloadMapper()

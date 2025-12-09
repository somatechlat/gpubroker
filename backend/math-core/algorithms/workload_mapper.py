"""
Workload-to-GPU Mapping Engine

Translates natural language workload descriptions to GPU requirements.
"10 AI images for 1 hour" → min_vram=12GB, recommended=RTX 4090/A6000
"""

from typing import Dict, Any, List, Optional
import logging

from core.benchmarks import BenchmarkRepository

logger = logging.getLogger(__name__)


class WorkloadMapper:
    """
    Maps workload descriptions to GPU requirements.
    
    Supports:
    - Image generation (Stable Diffusion, DALL-E style)
    - LLM inference (various model sizes)
    - Model training (fine-tuning, full training)
    - Video processing
    - Data processing
    """
    
    def __init__(self, benchmark_repo: BenchmarkRepository):
        self.benchmark_repo = benchmark_repo
        
        # Workload profiles with GPU requirements
        self.workload_profiles = self._load_workload_profiles()
    
    def _load_workload_profiles(self) -> Dict[str, Dict[str, Any]]:
        """Load workload requirement profiles."""
        return {
            "image_generation": {
                "sd_1.5": {
                    "min_vram_gb": 4,
                    "recommended_vram_gb": 8,
                    "time_per_image_seconds": {"draft": 5, "standard": 15, "high": 30},
                    "recommended_gpus": ["RTX-4070-Ti", "RTX-3080", "A10", "T4"],
                },
                "sdxl": {
                    "min_vram_gb": 8,
                    "recommended_vram_gb": 12,
                    "time_per_image_seconds": {"draft": 10, "standard": 25, "high": 45},
                    "recommended_gpus": ["RTX-4090", "RTX-4080", "A6000", "L4"],
                },
                "sdxl_high_res": {
                    "min_vram_gb": 12,
                    "recommended_vram_gb": 24,
                    "time_per_image_seconds": {"draft": 20, "standard": 45, "high": 90},
                    "recommended_gpus": ["RTX-4090", "A6000", "A100-PCIe", "L40S"],
                },
            },
            "llm_inference": {
                "7b": {
                    "min_vram_gb": 8,
                    "recommended_vram_gb": 16,
                    "tokens_per_second_range": [500, 3500],
                    "recommended_gpus": ["RTX-4090", "A10", "L4", "T4"],
                },
                "13b": {
                    "min_vram_gb": 16,
                    "recommended_vram_gb": 24,
                    "tokens_per_second_range": [300, 2200],
                    "recommended_gpus": ["RTX-4090", "A6000", "A100-PCIe", "L40S"],
                },
                "70b": {
                    "min_vram_gb": 140,  # Requires multi-GPU or quantization
                    "recommended_vram_gb": 160,
                    "tokens_per_second_range": [100, 450],
                    "recommended_gpus": ["H100-SXM", "A100-SXM"],
                    "multi_gpu": True,
                    "quantized_vram_gb": 40,  # With 4-bit quantization
                },
            },
            "training": {
                "finetune_7b": {
                    "min_vram_gb": 16,
                    "recommended_vram_gb": 24,
                    "hours_per_epoch_1k_samples": 0.5,
                    "recommended_gpus": ["A6000", "RTX-4090", "A100-PCIe"],
                },
                "finetune_13b": {
                    "min_vram_gb": 24,
                    "recommended_vram_gb": 48,
                    "hours_per_epoch_1k_samples": 1.0,
                    "recommended_gpus": ["A6000", "A100-PCIe", "A100-SXM"],
                },
                "full_train_7b": {
                    "min_vram_gb": 48,
                    "recommended_vram_gb": 80,
                    "hours_per_epoch_1k_samples": 2.0,
                    "recommended_gpus": ["A100-SXM", "H100-SXM"],
                    "multi_gpu": True,
                },
            },
            "video_processing": {
                "transcoding_4k": {
                    "min_vram_gb": 8,
                    "recommended_vram_gb": 12,
                    "minutes_per_hour_video": 15,
                    "recommended_gpus": ["RTX-4070-Ti", "RTX-4080", "A10"],
                },
                "ai_upscaling": {
                    "min_vram_gb": 12,
                    "recommended_vram_gb": 24,
                    "minutes_per_hour_video": 60,
                    "recommended_gpus": ["RTX-4090", "A6000", "L40S"],
                },
            },
            "data_processing": {
                "general": {
                    "min_vram_gb": 8,
                    "recommended_vram_gb": 16,
                    "recommended_gpus": ["T4", "A10", "L4"],
                },
            },
        }
    
    def estimate(
        self,
        workload_type: str,
        quantity: int,
        duration_hours: float,
        quality: str = "standard",
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Estimate GPU requirements for a workload.
        
        Args:
            workload_type: 'image_generation', 'llm_inference', 'training', etc.
            quantity: Number of items to process
            duration_hours: Target duration in hours
            quality: 'draft', 'standard', 'high'
            model_name: Specific model (e.g., 'sdxl', '7b', '13b')
        
        Returns:
            Dict with GPU requirements and recommendations
        """
        workload_type = workload_type.lower().replace(" ", "_")
        
        if workload_type not in self.workload_profiles:
            raise ValueError(f"Unknown workload type: {workload_type}. "
                           f"Supported: {list(self.workload_profiles.keys())}")
        
        profiles = self.workload_profiles[workload_type]
        
        # Select appropriate profile
        if model_name and model_name in profiles:
            profile = profiles[model_name]
        else:
            # Use default/first profile
            profile = list(profiles.values())[0]
        
        # Calculate requirements based on workload type
        if workload_type == "image_generation":
            return self._estimate_image_generation(
                profile, quantity, duration_hours, quality
            )
        elif workload_type == "llm_inference":
            return self._estimate_llm_inference(
                profile, quantity, duration_hours, model_name
            )
        elif workload_type == "training":
            return self._estimate_training(
                profile, quantity, duration_hours, model_name
            )
        else:
            return self._estimate_generic(profile, quantity, duration_hours)
    
    def _estimate_image_generation(
        self,
        profile: Dict[str, Any],
        quantity: int,
        duration_hours: float,
        quality: str
    ) -> Dict[str, Any]:
        """Estimate for image generation workloads."""
        time_per_image = profile["time_per_image_seconds"].get(quality, 15)
        total_time_needed = quantity * time_per_image
        duration_seconds = duration_hours * 3600
        
        # Can we finish in time?
        if total_time_needed <= duration_seconds:
            confidence = 0.9
            reasoning = [
                f"Processing {quantity} images at {time_per_image}s each",
                f"Total time: {total_time_needed/60:.1f} minutes",
                f"Fits within {duration_hours} hour budget"
            ]
        else:
            confidence = 0.7
            reasoning = [
                f"Processing {quantity} images at {time_per_image}s each",
                f"Total time: {total_time_needed/60:.1f} minutes",
                f"May need faster GPU or longer duration"
            ]
        
        # Estimate cost range
        avg_price_low = 0.50  # Budget GPU
        avg_price_high = 3.00  # High-end GPU
        
        return {
            "min_vram_gb": profile["min_vram_gb"],
            "recommended_vram_gb": profile["recommended_vram_gb"],
            "recommended_gpu_tiers": profile["recommended_gpus"],
            "estimated_cost_range": {
                "low": round(avg_price_low * duration_hours, 2),
                "high": round(avg_price_high * duration_hours, 2)
            },
            "estimated_time_per_unit": time_per_image,
            "confidence": confidence,
            "reasoning": reasoning
        }
    
    def _estimate_llm_inference(
        self,
        profile: Dict[str, Any],
        quantity: int,
        duration_hours: float,
        model_name: Optional[str]
    ) -> Dict[str, Any]:
        """Estimate for LLM inference workloads."""
        # Assume quantity = number of requests, each ~500 tokens
        tokens_per_request = 500
        total_tokens = quantity * tokens_per_request
        
        tps_range = profile.get("tokens_per_second_range", [500, 2000])
        min_tps, max_tps = tps_range
        
        # Time needed at different speeds
        time_at_min_tps = total_tokens / min_tps / 3600  # hours
        time_at_max_tps = total_tokens / max_tps / 3600  # hours
        
        duration_seconds = duration_hours * 3600
        required_tps = total_tokens / duration_seconds if duration_seconds > 0 else float('inf')
        
        if required_tps <= max_tps:
            confidence = 0.9
            reasoning = [
                f"Processing {quantity} requests (~{total_tokens:,} tokens)",
                f"Required throughput: {required_tps:.0f} tokens/sec",
                f"Achievable with recommended GPUs"
            ]
        else:
            confidence = 0.6
            reasoning = [
                f"Processing {quantity} requests (~{total_tokens:,} tokens)",
                f"Required throughput: {required_tps:.0f} tokens/sec",
                f"May need multiple GPUs or longer duration"
            ]
        
        # Check for multi-GPU requirement
        if profile.get("multi_gpu"):
            reasoning.append("This model size requires multi-GPU setup")
        
        return {
            "min_vram_gb": profile["min_vram_gb"],
            "recommended_vram_gb": profile["recommended_vram_gb"],
            "recommended_gpu_tiers": profile["recommended_gpus"],
            "estimated_cost_range": {
                "low": round(1.0 * duration_hours, 2),
                "high": round(4.0 * duration_hours, 2)
            },
            "estimated_time_per_unit": tokens_per_request / ((min_tps + max_tps) / 2),
            "confidence": confidence,
            "reasoning": reasoning
        }
    
    def _estimate_training(
        self,
        profile: Dict[str, Any],
        quantity: int,
        duration_hours: float,
        model_name: Optional[str]
    ) -> Dict[str, Any]:
        """Estimate for training workloads."""
        # Assume quantity = dataset size in thousands
        dataset_size_k = quantity / 1000 if quantity > 100 else quantity
        
        hours_per_epoch = profile.get("hours_per_epoch_1k_samples", 1.0)
        estimated_epochs = max(1, int(duration_hours / (hours_per_epoch * dataset_size_k)))
        
        if estimated_epochs >= 3:
            confidence = 0.85
            reasoning = [
                f"Dataset: ~{quantity} samples",
                f"Can complete ~{estimated_epochs} epochs in {duration_hours} hours",
                "Sufficient for fine-tuning"
            ]
        else:
            confidence = 0.6
            reasoning = [
                f"Dataset: ~{quantity} samples",
                f"Can only complete ~{estimated_epochs} epochs",
                "Consider longer duration or smaller dataset"
            ]
        
        if profile.get("multi_gpu"):
            reasoning.append("Multi-GPU recommended for this model size")
        
        return {
            "min_vram_gb": profile["min_vram_gb"],
            "recommended_vram_gb": profile["recommended_vram_gb"],
            "recommended_gpu_tiers": profile["recommended_gpus"],
            "estimated_cost_range": {
                "low": round(2.0 * duration_hours, 2),
                "high": round(8.0 * duration_hours, 2)
            },
            "estimated_time_per_unit": hours_per_epoch * 3600 / 1000,  # seconds per sample
            "confidence": confidence,
            "reasoning": reasoning
        }
    
    def _estimate_generic(
        self,
        profile: Dict[str, Any],
        quantity: int,
        duration_hours: float
    ) -> Dict[str, Any]:
        """Generic estimation for other workload types."""
        return {
            "min_vram_gb": profile["min_vram_gb"],
            "recommended_vram_gb": profile["recommended_vram_gb"],
            "recommended_gpu_tiers": profile["recommended_gpus"],
            "estimated_cost_range": {
                "low": round(0.5 * duration_hours, 2),
                "high": round(3.0 * duration_hours, 2)
            },
            "estimated_time_per_unit": duration_hours * 3600 / max(quantity, 1),
            "confidence": 0.7,
            "reasoning": [
                f"Processing {quantity} items over {duration_hours} hours",
                "Generic estimate - actual performance may vary"
            ]
        }
    
    def map_to_gpus(
        self,
        workload_type: str,
        quantity: int,
        duration_hours: float,
        quality: str = "standard",
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Map workload to specific GPU recommendations with pricing.
        
        Returns detailed GPU recommendations with benchmark data.
        """
        estimate = self.estimate(
            workload_type, quantity, duration_hours, quality, model_name
        )
        
        recommended_gpus = []
        for gpu_name in estimate["recommended_gpu_tiers"]:
            benchmark = self.benchmark_repo.get(gpu_name)
            if benchmark:
                recommended_gpus.append({
                    "gpu_model": benchmark.gpu_model,
                    "vram_gb": benchmark.vram_gb,
                    "tflops_fp32": benchmark.tflops_fp32,
                    "tokens_per_second_7b": benchmark.tokens_per_second_7b,
                    "architecture": benchmark.architecture,
                    "tdp_watts": benchmark.tdp_watts
                })
        
        return {
            "workload_summary": {
                "type": workload_type,
                "quantity": quantity,
                "duration_hours": duration_hours,
                "quality": quality
            },
            "requirements": {
                "min_vram_gb": estimate["min_vram_gb"],
                "recommended_vram_gb": estimate["recommended_vram_gb"]
            },
            "recommended_gpus": recommended_gpus,
            "cost_estimate": estimate["estimated_cost_range"],
            "confidence": estimate["confidence"],
            "reasoning": estimate["reasoning"]
        }

"""
Math Core App Models - GPU benchmarks and calculation data.

The GPUBenchmark model stores verified benchmark data for GPU performance.
This data is used for KPI calculations (cost-per-token, cost-per-GFLOP).
"""
from django.db import models
import uuid


class GPUBenchmark(models.Model):
    """
    GPU benchmark data with verified specifications.
    
    Sources:
    - NVIDIA Official Specs: https://www.nvidia.com/en-us/data-center/
    - Lambda Labs Benchmarks: https://lambdalabs.com/gpu-benchmarks
    - MLPerf Inference Results: https://mlcommons.org/en/inference-datacenter-31/
    """
    ARCHITECTURE_CHOICES = [
        ('Hopper', 'Hopper'),
        ('Ada Lovelace', 'Ada Lovelace'),
        ('Ampere', 'Ampere'),
        ('Volta', 'Volta'),
        ('Turing', 'Turing'),
        ('Pascal', 'Pascal'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gpu_model = models.CharField(max_length=100, unique=True)
    
    # Compute Performance (TFLOPS)
    tflops_fp32 = models.FloatField(help_text="FP32 Tensor Core performance in TFLOPS")
    tflops_fp16 = models.FloatField(help_text="FP16 Tensor Core performance in TFLOPS")
    tflops_int8 = models.FloatField(null=True, blank=True, help_text="INT8 performance in TFLOPS")
    
    # Memory
    vram_gb = models.IntegerField(help_text="Video RAM in GB")
    memory_bandwidth_gbps = models.FloatField(help_text="Memory bandwidth in GB/s")
    
    # LLM Inference (tokens/second for different model sizes)
    # Based on vLLM/TGI benchmarks with batch_size=1, greedy decoding
    tokens_per_second_7b = models.IntegerField(help_text="Tokens/sec for Llama-2 7B or equivalent")
    tokens_per_second_13b = models.IntegerField(null=True, blank=True, help_text="Tokens/sec for Llama-2 13B")
    tokens_per_second_70b = models.IntegerField(null=True, blank=True, help_text="Tokens/sec for Llama-2 70B")
    
    # Image Generation (Stable Diffusion XL, 1024x1024, 30 steps)
    image_gen_per_minute = models.IntegerField(null=True, blank=True, help_text="Images per minute for SDXL")
    
    # Metadata
    architecture = models.CharField(max_length=50, choices=ARCHITECTURE_CHOICES, blank=True, null=True)
    tdp_watts = models.IntegerField(null=True, blank=True, help_text="Thermal Design Power in Watts")
    source = models.CharField(max_length=255, help_text="Data source citation")
    verified_at = models.DateTimeField(null=True, blank=True, help_text="When benchmark was last verified")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'gpu_benchmarks'
        managed = False  # Don't alter existing schema if table exists
        verbose_name = 'GPU Benchmark'
        verbose_name_plural = 'GPU Benchmarks'
        ordering = ['-tflops_fp32']
    
    def __str__(self):
        return f"{self.gpu_model} ({self.vram_gb}GB, {self.tflops_fp32} TFLOPS)"
    
    def get_tokens_per_second(self, model_size: str = "7b") -> int | None:
        """
        Get tokens per second for a specific model size.
        
        Args:
            model_size: LLM model size ('7b', '13b', '70b')
        
        Returns:
            Tokens per second or None if not available
        """
        size_map = {
            "7b": self.tokens_per_second_7b,
            "13b": self.tokens_per_second_13b,
            "70b": self.tokens_per_second_70b,
        }
        return size_map.get(model_size.lower(), self.tokens_per_second_7b)
    
    def get_tflops(self, precision: str = "fp32") -> float | None:
        """
        Get TFLOPS for a specific precision.
        
        Args:
            precision: 'fp32', 'fp16', or 'int8'
        
        Returns:
            TFLOPS or None if not available
        """
        precision_map = {
            "fp32": self.tflops_fp32,
            "fp16": self.tflops_fp16,
            "int8": self.tflops_int8,
        }
        return precision_map.get(precision.lower(), self.tflops_fp32)

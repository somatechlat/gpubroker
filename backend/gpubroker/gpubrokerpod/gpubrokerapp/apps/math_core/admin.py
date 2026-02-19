"""
Math Core App Admin Configuration.

Django admin interface for GPUBenchmark model.
"""

from django.contrib import admin

from .models import GPUBenchmark


@admin.register(GPUBenchmark)
class GPUBenchmarkAdmin(admin.ModelAdmin):
    """Admin configuration for GPUBenchmark model."""

    list_display = (
        "gpu_model",
        "tflops_fp32",
        "tflops_fp16",
        "vram_gb",
        "memory_bandwidth_gbps",
        "source",
        "verified_at",
    )
    list_filter = ("source", "verified_at")
    search_fields = ("gpu_model",)
    ordering = ("-tflops_fp32",)

    fieldsets = (
        (None, {"fields": ("gpu_model",)}),
        (
            "Compute Performance",
            {
                "fields": ("tflops_fp32", "tflops_fp16", "tflops_int8"),
                "description": "TFLOPS performance metrics",
            },
        ),
        (
            "Memory",
            {
                "fields": ("vram_gb", "memory_bandwidth_gbps"),
                "description": "Memory specifications",
            },
        ),
        (
            "LLM Performance",
            {
                "fields": (
                    "tokens_per_second_7b",
                    "tokens_per_second_13b",
                    "tokens_per_second_70b",
                ),
                "description": "Tokens per second for different model sizes",
            },
        ),
        (
            "Image Generation",
            {
                "fields": ("image_gen_per_minute",),
                "description": "Image generation performance",
            },
        ),
        (
            "Metadata",
            {
                "fields": ("source", "verified_at"),
                "description": "Data source and verification",
            },
        ),
    )

    readonly_fields = ("verified_at",)
    list_per_page = 25

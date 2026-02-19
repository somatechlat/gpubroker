# Generated migration for math_core models
# managed=True for test database creation

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="GPUBenchmark",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("gpu_model", models.CharField(max_length=100, unique=True)),
                (
                    "tflops_fp32",
                    models.FloatField(
                        help_text="FP32 Tensor Core performance in TFLOPS"
                    ),
                ),
                (
                    "tflops_fp16",
                    models.FloatField(
                        help_text="FP16 Tensor Core performance in TFLOPS"
                    ),
                ),
                (
                    "tflops_int8",
                    models.FloatField(
                        blank=True, help_text="INT8 performance in TFLOPS", null=True
                    ),
                ),
                ("vram_gb", models.IntegerField(help_text="Video RAM in GB")),
                (
                    "memory_bandwidth_gbps",
                    models.FloatField(help_text="Memory bandwidth in GB/s"),
                ),
                (
                    "tokens_per_second_7b",
                    models.IntegerField(
                        help_text="Tokens/sec for Llama-2 7B or equivalent"
                    ),
                ),
                (
                    "tokens_per_second_13b",
                    models.IntegerField(
                        blank=True, help_text="Tokens/sec for Llama-2 13B", null=True
                    ),
                ),
                (
                    "tokens_per_second_70b",
                    models.IntegerField(
                        blank=True, help_text="Tokens/sec for Llama-2 70B", null=True
                    ),
                ),
                (
                    "image_gen_per_minute",
                    models.IntegerField(
                        blank=True, help_text="Images per minute for SDXL", null=True
                    ),
                ),
                (
                    "architecture",
                    models.CharField(
                        blank=True,
                        choices=[
                            ("Hopper", "Hopper"),
                            ("Ada Lovelace", "Ada Lovelace"),
                            ("Ampere", "Ampere"),
                            ("Volta", "Volta"),
                            ("Turing", "Turing"),
                            ("Pascal", "Pascal"),
                        ],
                        max_length=50,
                        null=True,
                    ),
                ),
                (
                    "tdp_watts",
                    models.IntegerField(
                        blank=True, help_text="Thermal Design Power in Watts", null=True
                    ),
                ),
                (
                    "source",
                    models.CharField(help_text="Data source citation", max_length=255),
                ),
                (
                    "verified_at",
                    models.DateTimeField(
                        blank=True,
                        help_text="When benchmark was last verified",
                        null=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "GPU Benchmark",
                "verbose_name_plural": "GPU Benchmarks",
                "db_table": "gpu_benchmarks",
                "ordering": ["-tflops_fp32"],
            },
        ),
    ]

"""
Google Vertex AI Adapter for GPUBROKER.

Integration with Google Cloud Vertex AI GPU instances.
https://cloud.google.com/vertex-ai/pricing
"""

import logging
from datetime import datetime, timezone

from .base import BaseProviderAdapter, ProviderOffer

logger = logging.getLogger("gpubroker.providers.adapters.google_vertex_ai")


class GoogleVertexAIAdapter(BaseProviderAdapter):
    """Google Vertex AI GPU instances adapter."""

    PROVIDER_NAME = "google_vertex_ai"
    BASE_URL = "https://compute.googleapis.com"

    # Google Cloud GPU pricing (us-central1)
    INSTANCE_PRICING = [
        {
            "type": "n1-standard-4 + T4",
            "gpu": "T4",
            "price": 0.526,
            "memory": 16,
            "vcpu": 4,
            "ram": 15,
        },
        {
            "type": "n1-standard-8 + T4",
            "gpu": "T4",
            "price": 0.752,
            "memory": 16,
            "vcpu": 8,
            "ram": 30,
        },
        {
            "type": "n1-standard-16 + 2x T4",
            "gpu": "2x T4",
            "price": 1.504,
            "memory": 32,
            "vcpu": 16,
            "ram": 60,
        },
        {
            "type": "n1-standard-32 + 4x T4",
            "gpu": "4x T4",
            "price": 3.008,
            "memory": 64,
            "vcpu": 32,
            "ram": 120,
        },
        {
            "type": "n1-standard-8 + V100",
            "gpu": "V100",
            "price": 2.98,
            "memory": 16,
            "vcpu": 8,
            "ram": 30,
        },
        {
            "type": "n1-standard-16 + 2x V100",
            "gpu": "2x V100",
            "price": 5.96,
            "memory": 32,
            "vcpu": 16,
            "ram": 60,
        },
        {
            "type": "n1-standard-32 + 4x V100",
            "gpu": "4x V100",
            "price": 11.92,
            "memory": 64,
            "vcpu": 32,
            "ram": 120,
        },
        {
            "type": "n1-standard-96 + 8x V100",
            "gpu": "8x V100",
            "price": 23.84,
            "memory": 128,
            "vcpu": 96,
            "ram": 360,
        },
        {
            "type": "a2-highgpu-1g",
            "gpu": "A100 40GB",
            "price": 3.67,
            "memory": 40,
            "vcpu": 12,
            "ram": 85,
        },
        {
            "type": "a2-highgpu-2g",
            "gpu": "2x A100 40GB",
            "price": 7.35,
            "memory": 80,
            "vcpu": 24,
            "ram": 170,
        },
        {
            "type": "a2-highgpu-4g",
            "gpu": "4x A100 40GB",
            "price": 14.69,
            "memory": 160,
            "vcpu": 48,
            "ram": 340,
        },
        {
            "type": "a2-highgpu-8g",
            "gpu": "8x A100 40GB",
            "price": 29.39,
            "memory": 320,
            "vcpu": 96,
            "ram": 680,
        },
        {
            "type": "a2-megagpu-16g",
            "gpu": "16x A100 40GB",
            "price": 58.78,
            "memory": 640,
            "vcpu": 96,
            "ram": 1360,
        },
        {
            "type": "a2-ultragpu-1g",
            "gpu": "A100 80GB",
            "price": 5.00,
            "memory": 80,
            "vcpu": 12,
            "ram": 170,
        },
        {
            "type": "a2-ultragpu-2g",
            "gpu": "2x A100 80GB",
            "price": 10.00,
            "memory": 160,
            "vcpu": 24,
            "ram": 340,
        },
        {
            "type": "a2-ultragpu-4g",
            "gpu": "4x A100 80GB",
            "price": 20.00,
            "memory": 320,
            "vcpu": 48,
            "ram": 680,
        },
        {
            "type": "a2-ultragpu-8g",
            "gpu": "8x A100 80GB",
            "price": 40.00,
            "memory": 640,
            "vcpu": 96,
            "ram": 1360,
        },
        {
            "type": "a3-highgpu-8g",
            "gpu": "8x H100 80GB",
            "price": 98.32,
            "memory": 640,
            "vcpu": 208,
            "ram": 1872,
        },
    ]

    REGIONS = ["us-central1", "us-east1", "europe-west4", "asia-east1"]

    TPS_MAPPING = {
        "h100": 12000,
        "a100": 8000,
        "v100": 3000,
        "t4": 800,
        "l4": 1200,
    }

    async def get_offers(self, auth_token: str | None = None) -> list[ProviderOffer]:
        """Fetch Google Vertex AI GPU offerings."""
        offers = []

        for region in self.REGIONS:
            for inst in self.INSTANCE_PRICING:
                offers.append(
                    ProviderOffer(
                        provider=self.PROVIDER_NAME,
                        region=region,
                        instance_type=f"{inst['type']} ({inst['gpu']})",
                        price_per_hour=inst["price"],
                        tokens_per_second=self._estimate_tps(inst["gpu"]),
                        availability="available",
                        compliance_tags=["gcp", "vertex", "soc2", "hipaa", "gdpr"],
                        last_updated=datetime.now(timezone.utc),
                        gpu_memory_gb=inst["memory"],
                        cpu_cores=inst["vcpu"],
                        ram_gb=inst["ram"],
                    )
                )

        logger.info(f"Google Vertex AI: Fetched {len(offers)} offers")
        return offers

    def _estimate_tps(self, gpu_name: str) -> float:
        name = gpu_name.lower()
        for key, tps in self.TPS_MAPPING.items():
            if key in name:
                return float(tps)
        return 1000.0

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        return bool(credentials.get("api_key") or credentials.get("service_account"))

"""
Azure ML Adapter for GPUBROKER.

Integration with Azure Machine Learning GPU instances.
https://azure.microsoft.com/en-us/pricing/details/machine-learning/
"""

import logging
from datetime import datetime, timezone

from .base import BaseProviderAdapter, ProviderOffer

logger = logging.getLogger("gpubroker.providers.adapters.azure_ml")


class AzureMLAdapter(BaseProviderAdapter):
    """Azure Machine Learning GPU instances adapter."""

    PROVIDER_NAME = "azure_ml"
    BASE_URL = "https://management.azure.com"

    # Azure ML GPU instance pricing (East US)
    INSTANCE_PRICING = [
        {
            "type": "Standard_NC4as_T4_v3",
            "gpu": "T4",
            "price": 0.526,
            "memory": 16,
            "vcpu": 4,
            "ram": 28,
        },
        {
            "type": "Standard_NC8as_T4_v3",
            "gpu": "T4",
            "price": 0.752,
            "memory": 16,
            "vcpu": 8,
            "ram": 56,
        },
        {
            "type": "Standard_NC16as_T4_v3",
            "gpu": "T4",
            "price": 1.204,
            "memory": 16,
            "vcpu": 16,
            "ram": 110,
        },
        {
            "type": "Standard_NC64as_T4_v3",
            "gpu": "4x T4",
            "price": 4.816,
            "memory": 64,
            "vcpu": 64,
            "ram": 440,
        },
        {
            "type": "Standard_NC6s_v3",
            "gpu": "V100",
            "price": 3.366,
            "memory": 16,
            "vcpu": 6,
            "ram": 112,
        },
        {
            "type": "Standard_NC12s_v3",
            "gpu": "2x V100",
            "price": 6.732,
            "memory": 32,
            "vcpu": 12,
            "ram": 224,
        },
        {
            "type": "Standard_NC24s_v3",
            "gpu": "4x V100",
            "price": 13.464,
            "memory": 64,
            "vcpu": 24,
            "ram": 448,
        },
        {
            "type": "Standard_NC24rs_v3",
            "gpu": "4x V100",
            "price": 14.81,
            "memory": 64,
            "vcpu": 24,
            "ram": 448,
        },
        {
            "type": "Standard_ND40rs_v2",
            "gpu": "8x V100",
            "price": 28.80,
            "memory": 256,
            "vcpu": 40,
            "ram": 672,
        },
        {
            "type": "Standard_NC24ads_A100_v4",
            "gpu": "A100",
            "price": 3.673,
            "memory": 80,
            "vcpu": 24,
            "ram": 220,
        },
        {
            "type": "Standard_NC48ads_A100_v4",
            "gpu": "2x A100",
            "price": 7.346,
            "memory": 160,
            "vcpu": 48,
            "ram": 440,
        },
        {
            "type": "Standard_NC96ads_A100_v4",
            "gpu": "4x A100",
            "price": 14.692,
            "memory": 320,
            "vcpu": 96,
            "ram": 880,
        },
        {
            "type": "Standard_ND96asr_v4",
            "gpu": "8x A100",
            "price": 32.77,
            "memory": 320,
            "vcpu": 96,
            "ram": 900,
        },
        {
            "type": "Standard_ND96amsr_A100_v4",
            "gpu": "8x A100 80GB",
            "price": 37.00,
            "memory": 640,
            "vcpu": 96,
            "ram": 1900,
        },
    ]

    REGIONS = ["eastus", "westus2", "westeurope", "southeastasia"]

    TPS_MAPPING = {
        "h100": 12000,
        "a100": 8000,
        "v100": 3000,
        "t4": 800,
    }

    async def get_offers(self, auth_token: str | None = None) -> list[ProviderOffer]:
        """Fetch Azure ML GPU offerings."""
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
                        compliance_tags=["azure", "ml", "soc2", "hipaa", "gdpr"],
                        last_updated=datetime.now(timezone.utc),
                        gpu_memory_gb=inst["memory"],
                        cpu_cores=inst["vcpu"],
                        ram_gb=inst["ram"],
                    )
                )

        logger.info(f"Azure ML: Fetched {len(offers)} offers")
        return offers

    def _estimate_tps(self, gpu_name: str) -> float:
        name = gpu_name.lower()
        for key, tps in self.TPS_MAPPING.items():
            if key in name:
                return float(tps)
        return 1000.0

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        return bool(credentials.get("api_key") or credentials.get("client_id"))

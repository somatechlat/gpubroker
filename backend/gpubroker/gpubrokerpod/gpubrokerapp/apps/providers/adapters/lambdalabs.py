"""
Lambda Labs Adapter for GPUBROKER.

Live integration with Lambda Labs GPU cloud.
https://cloud.lambdalabs.com/api/v1
"""

import logging
from datetime import datetime, timezone

import httpx

from .base import BaseProviderAdapter, ProviderOffer

logger = logging.getLogger("gpubroker.providers.adapters.lambdalabs")


class LambdaLabsAdapter(BaseProviderAdapter):
    """Lambda Labs GPU cloud adapter."""

    PROVIDER_NAME = "lambdalabs"
    BASE_URL = "https://cloud.lambdalabs.com/api/v1"

    TPS_MAPPING = {
        "h100": 12000,
        "a100": 8000,
        "a6000": 2200,
        "4090": 4500,
        "3090": 3500,
        "v100": 3000,
    }

    async def get_offers(self, auth_token: str | None = None) -> list[ProviderOffer]:
        """Fetch Lambda Labs GPU offers."""
        if not auth_token:
            logger.warning("Lambda Labs: No auth token provided")
            return []

        try:
            headers = {"Authorization": f"Bearer {auth_token}"}

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/instance-types", headers=headers
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_offers(data)

        except Exception as e:
            logger.error(f"Lambda Labs fetch failed: {e}")
            return []

    def _parse_offers(self, data: dict) -> list[ProviderOffer]:
        """Parse Lambda Labs response."""
        offers = []
        instance_types = data.get("data", {})

        for name, info in instance_types.items():
            specs = info.get("instance_type", {}).get("specs", {})
            price = info.get("instance_type", {}).get("price_cents_per_hour", 0) / 100

            gpu_name = (
                specs.get("gpus", [{}])[0].get("name", name)
                if specs.get("gpus")
                else name
            )
            memory_gb = (
                specs.get("gpus", [{}])[0].get("memory_gib", 0)
                if specs.get("gpus")
                else 0
            )

            availability = (
                "available"
                if info.get("regions_with_capacity_available")
                else "unavailable"
            )

            offers.append(
                ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region="us-west-1",
                    instance_type=gpu_name,
                    price_per_hour=price,
                    tokens_per_second=self._estimate_tps(gpu_name),
                    availability=availability,
                    compliance_tags=["lambdalabs", "cloud"],
                    last_updated=datetime.now(timezone.utc),
                    gpu_memory_gb=int(memory_gb),
                )
            )

        logger.info(f"Lambda Labs: Fetched {len(offers)} offers")
        return offers

    def _estimate_tps(self, gpu_name: str) -> float:
        name = gpu_name.lower()
        for key, tps in self.TPS_MAPPING.items():
            if key in name:
                return float(tps)
        return 1000.0

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        api_key = credentials.get("api_key")
        if not api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/instance-types",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                return response.status_code == 200
        except Exception:
            return False

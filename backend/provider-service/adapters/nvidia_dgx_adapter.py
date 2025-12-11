"""
NVIDIA DGX Cloud Adapter for GPUBROKER
Live integration with NVIDIA DGX Cloud enterprise pricing
"""

import httpx
from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone

from .base_adapter import BaseProviderAdapter
from models.provider_offer import ProviderOffer

logger = logging.getLogger(__name__)


class NVIDIADGXAdapter(BaseProviderAdapter):
    """Live NVIDIA DGX Cloud adapter with enterprise pricing"""

    PROVIDER_NAME = "nvidia_dgx"
    BASE_URL = "https://api.nvidia.com/dgx/v1"

    async def get_offers(self, auth_token: str) -> List[ProviderOffer]:
        """Fetch real-time NVIDIA DGX Cloud pricing"""
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/instances", headers=headers
                )
                response.raise_for_status()

                data = response.json()
                return await self._parse_dgx_data(data)

        except Exception as e:
            logger.error(f"Failed to fetch NVIDIA DGX data: {e}")
            return []

    async def _parse_dgx_data(self, data: Dict) -> List[ProviderOffer]:
        """Parse NVIDIA DGX Cloud instance data"""
        offers = []

        instances = data.get("instances", [])
        for instance in instances:
            instance_type = instance.get("type")
            gpu_count = int(instance.get("gpus", 0))
            price_hour = float(instance.get("price_per_hour", 0))
            region = instance.get("region", "us-west-2")

            if not instance_type or price_hour == 0:
                continue

            tokens_per_second = self._estimate_tps_dgx(instance_type, gpu_count)

            offer = ProviderOffer(
                provider="nvidia_dgx",
                region=region,
                instance_type=instance_type,
                price_per_hour=price_hour,
                tokens_per_second=tokens_per_second,
                availability="available",
                compliance_tags=["nvidia", "dgx", "enterprise", "bare-metal"],
                last_updated=datetime.now(timezone.utc),
            )
            offers.append(offer)

        return offers

    def _estimate_tps_dgx(self, instance_type: str, gpu_count: int) -> float:
        """Estimate tokens per second for DGX instances"""
        base_tps = {
            "DGX-A100": 4000,
            "DGX-H100": 7000,
            "DGX-2": 2000,
            "DGX-Station": 1500,
        }

        base = base_tps.get(instance_type, 1000)
        return base * gpu_count

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate NVIDIA DGX credentials"""
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                return False

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.BASE_URL}/user", headers=headers)
                return response.status_code == 200

        except Exception as e:
            logger.error(f"NVIDIA DGX credential validation failed: {e}")
            return False

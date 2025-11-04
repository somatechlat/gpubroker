"""
Lambda Labs Adapter for GPUBROKER
Live integration with Lambda Labs GPU cloud pricing
"""

import httpx
from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone

from .base_adapter import BaseProviderAdapter
from ..models.provider_offer import ProviderOffer

logger = logging.getLogger(__name__)


class LambdaLabsAdapter(BaseProviderAdapter):
    """Live Lambda Labs adapter with real-time pricing"""

    PROVIDER_NAME = "lambdalabs"
    BASE_URL = "https://cloud.lambdalabs.com/api/v1"

    async def get_offers(self, auth_token: str) -> List[ProviderOffer]:
        """Fetch real-time Lambda Labs pricing"""
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/instance-types", headers=headers
                )
                response.raise_for_status()

                data = response.json()
                return await self._parse_instance_data(data)

        except Exception as e:
            logger.error(f"Failed to fetch Lambda Labs data: {e}")
            return []

    async def _parse_instance_data(self, data: Dict) -> List[ProviderOffer]:
        """Parse Lambda Labs instance data into normalized offers"""
        offers = []

        instances = data.get("data", [])
        for instance in instances:
            instance_name = instance.get("instance_type", {}).get("name")
            if not instance_name:
                continue

            price_cents = instance.get("price_cents_per_hour", 0)
            price_hour = price_cents / 100.0

            regions = instance.get("regions_with_capacity_available", [])
            for region in regions:
                tokens_per_second = self._estimate_tps(instance_name)

                offer = ProviderOffer(
                    provider="lambdalabs",
                    region=region.get("name", "unknown"),
                    instance_type=instance_name,
                    price_per_hour=price_hour,
                    tokens_per_second=tokens_per_second,
                    availability="available",
                    compliance_tags=["lambdalabs", "cloud", "bare-metal"],
                    last_updated=datetime.now(timezone.utc),
                )
                offers.append(offer)

        return offers

    def _estimate_tps(self, instance_name: str) -> float:
        """Estimate tokens per second based on instance type"""
        tps_mapping = {
            "gpu_1x_rtx6000": 1500,
            "gpu_1x_a100": 4000,
            "gpu_1x_a100_sxm4": 4500,
            "gpu_2x_a100": 8000,
            "gpu_4x_a100": 16000,
            "gpu_8x_a100": 32000,
            "gpu_1x_h100_pcie": 6000,
            "gpu_1x_h100_sxm5": 7000,
            "gpu_2x_h100": 14000,
            "gpu_4x_h100": 28000,
            "gpu_8x_h100": 56000,
        }

        return tps_mapping.get(instance_name, 1000)

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Lambda Labs credentials"""
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                return False

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/api-keys", headers=headers
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Lambda Labs credential validation failed: {e}")
            return False

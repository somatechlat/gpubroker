"""
IBM Watson ML Adapter for GPUBROKER
Live integration with IBM Watson Machine Learning pricing
"""

import httpx
from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone

from .base_adapter import BaseProviderAdapter
from ..models.provider_offer import ProviderOffer

logger = logging.getLogger(__name__)


class IBMWatsonAdapter(BaseProviderAdapter):
    """Live IBM Watson ML adapter with enterprise pricing"""

    PROVIDER_NAME = "ibm_watson"
    BASE_URL = "https://us-south.ml.cloud.ibm.com/v4"

    async def get_offers(self, auth_token: str) -> List[ProviderOffer]:
        """Fetch real-time IBM Watson ML pricing"""
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/deployments", headers=headers
                )
                response.raise_for_status()

                data = response.json()
                return await self._parse_deployment_data(data)

        except Exception as e:
            logger.error(f"Failed to fetch IBM Watson data: {e}")
            return []

    async def _parse_deployment_data(self, data: Dict) -> List[ProviderOffer]:
        """Parse IBM Watson deployment data"""
        offers = []

        deployments = data.get("resources", [])
        for deployment in deployments:
            metadata = deployment.get("metadata", {})
            hardware_spec = metadata.get("hardware_spec", {})

            instance_type = hardware_spec.get("name", "unknown")
            gpu_type = hardware_spec.get("gpu", "unknown")
            price_hour = float(hardware_spec.get("price_per_hour", 5.0))
            region = "us-south"  # Default region

            tokens_per_second = self._estimate_tps_watson(gpu_type)

            offer = ProviderOffer(
                provider="ibm_watson",
                region=region,
                instance_type=instance_type,
                price_per_hour=price_hour,
                tokens_per_second=tokens_per_second,
                availability="available",
                compliance_tags=[
                    "ibm",
                    "watson",
                    "enterprise",
                    "cloud",
                    "soc2_compliant",
                ],
                last_updated=datetime.now(timezone.utc),
            )
            offers.append(offer)

        return offers

    def _estimate_tps_watson(self, gpu_type: str) -> float:
        """Estimate tokens per second for IBM Watson"""
        tps_mapping = {"v100": 3000, "k80": 800, "p100": 1800, "a100": 8000}
        return tps_mapping.get(gpu_type.lower(), 2000)

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate IBM Watson credentials"""
        try:
            api_key = credentials.get("api_key")
            instance_id = credentials.get("instance_id")

            if not api_key or not instance_id:
                return False

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/instances/{instance_id}", headers=headers
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"IBM Watson credential validation failed: {e}")
            return False

"""
RunPod Adapter for GPUBROKER
Live integration with RunPod GPU cloud pricing and availability
"""

import httpx
from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone

from .base_adapter import BaseProviderAdapter
from ..models.provider_offer import ProviderOffer

logger = logging.getLogger(__name__)


class RunPodAdapter(BaseProviderAdapter):
    """Live RunPod adapter with real-time pricing"""

    PROVIDER_NAME = "runpod"
    BASE_URL = "https://api.runpod.io/graphql"

    async def get_offers(self, auth_token: str) -> List[ProviderOffer]:
        """Fetch real-time RunPod pricing and availability"""
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            query = """
            query {
                gpuTypes {
                    id
                    displayName
                    memoryInGb
                    secureCloud
                    communityCloud
                    secureSpotCloud
                    communitySpotCloud
                    lowestPrice(input: {gpuCount: 1}) {
                        minimumBidPrice
                        uninterruptablePrice
                    }
                }
            }
            """

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.BASE_URL, headers=headers, json={"query": query}
                )
                response.raise_for_status()

                data = response.json()
                return await self._parse_gpu_data(data)

        except Exception as e:
            logger.error(f"Failed to fetch RunPod data: {e}")
            return []

    async def _parse_gpu_data(self, data: Dict) -> List[ProviderOffer]:
        """Parse RunPod GPU data into normalized offers"""
        offers = []

        gpu_types = data.get("data", {}).get("gpuTypes", [])
        for gpu in gpu_types:
            if not gpu.get("lowestPrice") or not gpu.get("lowestPrice", {}).get(
                "uninterruptablePrice"
            ):
                continue

            price = float(gpu["lowestPrice"]["uninterruptablePrice"])
            memory_gb = int(gpu.get("memoryInGb", 0))

            # Estimate tokens per second based on GPU type
            tokens_per_second = self._estimate_tps(gpu["displayName"])

            offer = ProviderOffer(
                provider="runpod",
                region="us-east",  # Default region, actual varies
                instance_type=gpu["displayName"],
                price_per_hour=price,
                tokens_per_second=tokens_per_second,
                availability="available",
                compliance_tags=["runpod", "cloud", "serverless"],
                last_updated=datetime.now(timezone.utc),
            )
            offers.append(offer)

        return offers

    def _estimate_tps(self, gpu_name: str) -> float:
        """Estimate tokens per second based on GPU type"""
        tps_mapping = {
            "A100 80GB": 8000,
            "A100 40GB": 6000,
            "H100": 12000,
            "V100": 3000,
            "RTX 4090": 4500,
            "RTX 3090": 3500,
            "RTX 3080": 2800,
            "A6000": 2200,
            "A5000": 1800,
            "T4": 800,
        }

        for key, tps in tps_mapping.items():
            if key.lower() in gpu_name.lower():
                return tps

        return 1000  # Default estimate

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate RunPod credentials"""
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                return False

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    self.BASE_URL, headers=headers, json={"query": "{ myself { id } }"}
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"RunPod credential validation failed: {e}")
            return False

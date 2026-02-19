"""
RunPod Adapter for GPUBROKER.

Live integration with RunPod GPU cloud pricing and availability.
https://docs.runpod.io/reference/graphql-api
"""

import logging
from datetime import datetime, timezone

import httpx

from .base import BaseProviderAdapter, ProviderOffer

logger = logging.getLogger("gpubroker.providers.adapters.runpod")


class RunPodAdapter(BaseProviderAdapter):
    """
    Live RunPod adapter with real-time pricing.

    Uses RunPod's GraphQL API to fetch GPU types and pricing.
    """

    PROVIDER_NAME = "runpod"
    BASE_URL = "https://api.runpod.io/graphql"

    # GPU performance estimates (tokens per second)
    TPS_MAPPING = {
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

    async def get_offers(self, auth_token: str | None = None) -> list[ProviderOffer]:
        """
        Fetch real-time RunPod pricing and availability.

        Args:
            auth_token: RunPod API key

        Returns:
            List of normalized ProviderOffer instances
        """
        if not auth_token:
            logger.warning("RunPod: No auth token provided")
            return []

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
                return self._parse_gpu_data(data)

        except httpx.HTTPStatusError as e:
            logger.error(f"RunPod API error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch RunPod data: {e}")
            return []

    def _parse_gpu_data(self, data: dict) -> list[ProviderOffer]:
        """Parse RunPod GPU data into normalized offers."""
        offers = []

        gpu_types = data.get("data", {}).get("gpuTypes", [])
        for gpu in gpu_types:
            lowest_price = gpu.get("lowestPrice")
            if not lowest_price:
                continue

            price = lowest_price.get("uninterruptablePrice")
            if not price:
                continue

            price = float(price)
            memory_gb = int(gpu.get("memoryInGb", 0))
            display_name = gpu.get("displayName", "Unknown")

            # Estimate tokens per second based on GPU type
            tokens_per_second = self._estimate_tps(display_name)

            # Determine availability based on cloud options
            availability = "available"
            if not gpu.get("secureCloud") and not gpu.get("communityCloud"):
                availability = "limited"

            offer = ProviderOffer(
                provider=self.PROVIDER_NAME,
                region="us-east",  # Default region, actual varies
                instance_type=display_name,
                price_per_hour=price,
                tokens_per_second=tokens_per_second,
                availability=availability,
                compliance_tags=["runpod", "cloud", "serverless"],
                last_updated=datetime.now(timezone.utc),
                gpu_memory_gb=memory_gb,
            )
            offers.append(offer)

        logger.info(f"RunPod: Fetched {len(offers)} offers")
        return offers

    def _estimate_tps(self, gpu_name: str) -> float:
        """
        Estimate tokens per second based on GPU type.

        Args:
            gpu_name: GPU display name

        Returns:
            Estimated tokens per second
        """
        for key, tps in self.TPS_MAPPING.items():
            if key.lower() in gpu_name.lower():
                return float(tps)
        return 1000.0  # Default estimate

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        """
        Validate RunPod API credentials.

        Args:
            credentials: Dict with 'api_key'

        Returns:
            True if credentials are valid
        """
        api_key = credentials.get("api_key")
        if not api_key:
            return False

        try:
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

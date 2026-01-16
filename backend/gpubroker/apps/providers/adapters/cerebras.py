"""
Cerebras Adapter for GPUBROKER.

Live integration with Cerebras Cloud for high-performance AI inference.
https://docs.cerebras.ai/api/
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from .base import BaseProviderAdapter, ProviderOffer
from ..common.messages import get_message

logger = logging.getLogger("gpubroker.providers.adapters.cerebras")


class CerebrasAdapter(BaseProviderAdapter):
    """
    Live Cerebras adapter using their cloud API.

    Cerebras specializes in large-scale AI inference with their CS-2 chips.
    """

    PROVIDER_NAME = "cerebras"
    BASE_URL = "https://api.cerebras.ai/v1"

    # GPU performance estimates (tokens per second)
    TPS_MAPPING = {
        "cs-2": 50000,  # Cerebras CS-2 wafer-scale engine
    }

    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """
        Fetch real-time Cerebras inference offers.

        Args:
            auth_token: Cerebras API key

        Returns:
            List of normalized ProviderOffer instances
        """
        if not auth_token:
            logger.warning(get_message("adapter.no_auth", provider=self.PROVIDER_NAME))
            return []

        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            client = await self.get_client()
            response = await client.get(
                f"{self.BASE_URL}/cloud/instances/types", headers=headers
            )
            response.raise_for_status()
            data = response.json()

            return self._parse_offers(data)

        except httpx.HTTPStatusError as e:
            logger.error(
                get_message(
                    "adapter.api_error",
                    provider=self.PROVIDER_NAME,
                    status=e.response.status_code,
                )
            )
            return []
        except Exception as e:
            logger.error(
                get_message(
                    "adapter.fetch_failed", provider=self.PROVIDER_NAME, error=str(e)
                )
            )
            return []

    def _parse_offers(self, data: Dict) -> List[ProviderOffer]:
        """Parse Cerebras offers list into normalized objects."""
        offers = []
        instance_types = data.get("instance_types", [])

        for instance in instance_types:
            try:
                # Cerebras fields:
                # - name: "cs2.xlarge"
                # - description: "Cerebras CS-2 Cloud Instance"
                # - memory_gb: int
                # - price_per_hour: float
                # - region: "us-east-1"
                # - available: bool

                instance_name = instance.get("name", "Unknown")
                price = float(instance.get("price_per_hour", 0.0))
                region = instance.get("region", "us-east-1")
                memory_gb = instance.get("memory_gb", 0)
                available = instance.get("available", True)

                # Estimate tokens per second
                tps = self._estimate_tps(instance_name)

                # Determine availability
                availability = "available" if available else "unavailable"

                offer = ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region=region,
                    instance_type=instance_name,
                    price_per_hour=price,
                    tokens_per_second=tps,
                    availability=availability,
                    compliance_tags=["cerebras", "ai-inference", "enterprise"],
                    last_updated=datetime.now(timezone.utc),
                    gpu_memory_gb=memory_gb,
                )
                offers.append(offer)

            except Exception as e:
                logger.warning(
                    get_message(
                        "adapter.parsing_failed",
                        provider=self.PROVIDER_NAME,
                        error=str(e),
                    )
                )
                continue

        logger.info(
            get_message(
                "adapter.fetched", provider=self.PROVIDER_NAME, count=len(offers)
            )
        )
        return offers

    def _estimate_tps(self, instance_name: str) -> float:
        """
        Estimate tokens per second based on instance type.

        Args:
            instance_name: Cerebras instance name

        Returns:
            Estimated tokens per second
        """
        name = instance_name.lower()
        for key, tps in self.TPS_MAPPING.items():
            if key in name:
                return float(tps)
        return 50000.0  # Default CS-2 estimate

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Validate Cerebras API credentials.

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

            client = await self.get_client()
            response = await client.get(f"{self.BASE_URL}/user/me", headers=headers)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Cerebras credential validation failed: {e}")
            return False

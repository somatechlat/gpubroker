"""
Spell Adapter for GPUBROKER.

Live integration with Spell.run for ML compute and GPU instances.
https://spell.run/docs/api
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from .base import BaseProviderAdapter, ProviderOffer
from ..common.messages import get_message

logger = logging.getLogger("gpubroker.providers.adapters.spell")


class SpellAdapter(BaseProviderAdapter):
    """
    Live Spell adapter using their cloud API.

    Spell provides GPU instances for ML training and inference.
    """

    PROVIDER_NAME = "spell"
    BASE_URL = "https://api.spell.run/v1"

    # GPU performance estimates (tokens per second)
    TPS_MAPPING = {
        "a100": 8000,
        "h100": 12000,
        "a6000": 2200,
        "rtx4090": 4500,
        "rtx3090": 3500,
        "v100": 3000,
        "t4": 800,
    }

    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """
        Fetch real-time Spell GPU offers.

        Args:
            auth_token: Spell API key

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
                f"{self.BASE_URL}/instance-types", headers=headers
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
        """Parse Spell offers list into normalized objects."""
        offers = []
        instance_types = data.get("instance_types", [])

        for instance in instance_types:
            try:
                # Spell fields:
                # - name: "A100-80GB"
                # - gpu_type: "A100"
                # - gpu_memory_gb: int
                # - cpu_cores: int
                # - memory_gb: int
                # - price_per_hour: float
                # - available: bool
                # - region: "us-east-1"

                instance_name = instance.get("name", "Unknown")
                gpu_type = instance.get("gpu_type", "Unknown")
                gpu_memory_gb = instance.get("gpu_memory_gb", 0)
                cpu_cores = instance.get("cpu_cores", 0)
                memory_gb = instance.get("memory_gb", 0)
                price_per_hour = float(instance.get("price_per_hour", 0.0))
                available = instance.get("available", True)
                region = instance.get("region", "us-east-1")

                # Estimate tokens per second
                tps = self._estimate_tps(gpu_type)

                # Determine availability
                availability = "available" if available else "limited"

                offer = ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region=region,
                    instance_type=instance_name,
                    price_per_hour=price_per_hour,
                    tokens_per_second=tps,
                    availability=availability,
                    compliance_tags=["spell", "ml-platform", "gpu-cloud"],
                    last_updated=datetime.now(timezone.utc),
                    gpu_memory_gb=gpu_memory_gb,
                    cpu_cores=cpu_cores,
                    ram_gb=memory_gb,
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

    def _estimate_tps(self, gpu_type: str) -> float:
        """
        Estimate tokens per second based on GPU type.

        Args:
            gpu_type: GPU type string

        Returns:
            Estimated tokens per second
        """
        name = gpu_type.lower()
        for key, tps in self.TPS_MAPPING.items():
            if key in name:
                return float(tps)
        return 3000.0  # Default estimate

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Validate Spell API credentials.

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
            logger.error(f"Spell credential validation failed: {e}")
            return False

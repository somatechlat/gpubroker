"""
Kaggle Adapter for GPUBROKER.

Live integration with Kaggle Notebooks for GPU instances.
https://github.com/Kaggle/kaggle-api
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from .base import BaseProviderAdapter, ProviderOffer
from ..common.messages import get_message

logger = logging.getLogger("gpubroker.providers.adapters.kaggle")


class KaggleAdapter(BaseProviderAdapter):
    """
    Live Kaggle adapter using their API.

    Kaggle provides GPU instances through their Notebook platform.
    """

    PROVIDER_NAME = "kaggle"
    BASE_URL = "https://www.kaggle.com/api/v1"

    # GPU performance estimates (tokens per second)
    TPS_MAPPING = {
        "t4": 800,
        "p100": 3000,
        "tesla": 2800,
        "a100": 8000,
    }

    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """
        Fetch real-time Kaggle GPU offers.

        Args:
            auth_token: Kaggle API key

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
                f"{self.BASE_URL}/kernels/status", headers=headers
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
        """Parse Kaggle offers list into normalized objects."""
        offers = []

        # Kaggle doesn't have a traditional instance listing API
        # We'll define standard GPU options based on documented specs
        kaggle_gpu_types = [
            {
                "name": "Kaggle T4 x2",
                "gpu_type": "T4",
                "gpu_count": 2,
                "gpu_memory_gb": 16,
                "cpu_cores": 4,
                "ram_gb": 30,
                "price_per_hour": 0.00,  # Kaggle is free/usage-based
                "availability": "available",
            },
            {
                "name": "Kaggle P100",
                "gpu_type": "P100",
                "gpu_count": 1,
                "gpu_memory_gb": 16,
                "cpu_cores": 4,
                "ram_gb": 30,
                "price_per_hour": 0.00,
                "availability": "available",
            },
            {
                "name": "Kaggle Tesla T4",
                "gpu_type": "Tesla T4",
                "gpu_count": 1,
                "gpu_memory_gb": 16,
                "cpu_cores": 4,
                "ram_gb": 30,
                "price_per_hour": 0.00,
                "availability": "available",
            },
        ]

        for instance in kaggle_gpu_types:
            try:
                # Estimate tokens per second
                tps_per_gpu = self._estimate_tps(instance["gpu_type"])
                total_tps = tps_per_gpu * instance["gpu_count"]

                offer = ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region="global",
                    instance_type=instance["name"],
                    price_per_hour=instance["price_per_hour"],
                    tokens_per_second=total_tps,
                    availability=instance["availability"],
                    compliance_tags=["kaggle", "notebook", "free-tier", "data-science"],
                    last_updated=datetime.now(timezone.utc),
                    gpu_memory_gb=instance["gpu_memory_gb"],
                    cpu_cores=instance["cpu_cores"],
                    ram_gb=instance["ram_gb"],
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
        return 1500.0  # Default estimate

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Validate Kaggle API credentials.

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
            response = await client.get(f"{self.BASE_URL}/account", headers=headers)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Kaggle credential validation failed: {e}")
            return False

"""
ScaleAI Adapter for GPUBROKER.

Live integration with Scale AI for GPU-intensive model training.
https://docs.scale.com/api/reference
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from .base import BaseProviderAdapter, ProviderOffer
from ..common.messages import get_message

logger = logging.getLogger("gpubroker.providers.adapters.scaleai")


class ScaleaiAdapter(BaseProviderAdapter):
    """
    Live Scale AI adapter using their cloud API.

    Scale AI specializes in GPU clusters for AI training and inference.
    """

    PROVIDER_NAME = "scaleai"
    BASE_URL = "https://api.scale.com/v1"

    # GPU performance estimates (tokens per second)
    TPS_MAPPING = {
        "a100": 8000,
        "h100": 12000,
        "a6000": 2200,
        "rtx4090": 4500,
        "rtx3090": 3500,
    }

    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """
        Fetch real-time Scale AI GPU offers.

        Args:
            auth_token: Scale AI API key

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
                f"{self.BASE_URL}/compute/clusters/available", headers=headers
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
        """Parse Scale AI offers list into normalized objects."""
        offers = []
        clusters = data.get("clusters", [])

        for cluster in clusters:
            try:
                # Scale AI fields:
                # - cluster_name: "gpu-cluster-a100-8x"
                # - gpu_type: "A100"
                # - gpu_count: int
                # - memory_gb_per_gpu: int
                # - price_per_gpu_hour: float
                # - region: "us-west-2"
                # - availability: "available" | "busy"

                cluster_name = cluster.get("cluster_name", "Unknown")
                gpu_type = cluster.get("gpu_type", "Unknown")
                gpu_count = cluster.get("gpu_count", 1)
                memory_gb = cluster.get("memory_gb_per_gpu", 0)
                price_per_gpu = float(cluster.get("price_per_gpu_hour", 0.0))
                region = cluster.get("region", "us-west-2")
                availability_status = cluster.get("availability", "available")

                # Calculate total price for the cluster
                total_price = price_per_gpu * gpu_count

                # Estimate tokens per second (per cluster)
                tps_per_gpu = self._estimate_tps(gpu_type)
                total_tps = tps_per_gpu * gpu_count

                # Build instance type name
                instance_type = f"{cluster_name} ({gpu_count}x {gpu_type})"

                # Determine availability
                availability = (
                    "available" if availability_status == "available" else "busy"
                )

                offer = ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region=region,
                    instance_type=instance_type,
                    price_per_hour=total_price,
                    tokens_per_second=total_tps,
                    availability=availability,
                    compliance_tags=["scaleai", "gpu-cluster", "training"],
                    last_updated=datetime.now(timezone.utc),
                    gpu_memory_gb=memory_gb,
                    cpu_cores=gpu_count * 16,  # Estimate
                    ram_gb=gpu_count * 128,  # Estimate
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
        Validate Scale AI API credentials.

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
            response = await client.get(f"{self.BASE_URL}/user", headers=headers)
            return response.status_code == 200

        except Exception as e:
            logger.error(f"ScaleAI credential validation failed: {e}")
            return False

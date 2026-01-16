"""
NVIDIA DGX Adapter for GPUBROKER.

Live integration with NVIDIA DGX Cloud for enterprise AI infrastructure.
https://docs.nvidia.com/dgx-cloud/api/
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from .base import BaseProviderAdapter, ProviderOffer
from ..common.messages import get_message

logger = logging.getLogger("gpubroker.providers.adapters.nvidia_dgx")


class NVIDIADGXAdapter(BaseProviderAdapter):
    """
    Live NVIDIA DGX Cloud adapter using their enterprise API.

    DGX Cloud provides premium AI infrastructure with H100 clusters.
    """

    PROVIDER_NAME = "nvidia_dgx"
    BASE_URL = "https://api.dgx.cloud.nvidia.com/v1"

    # GPU performance estimates (tokens per second)
    TPS_MAPPING = {
        "h100": 12000,
        "a100": 8000,
        "a6000": 2200,
    }

    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """
        Fetch real-time NVIDIA DGX Cloud offers.

        Args:
            auth_token: NVIDIA DGX API key

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
                "NVAPI-KEY": auth_token,
            }

            client = await self.get_client()
            response = await client.get(
                f"{self.BASE_URL}/clusters/available", headers=headers
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
        """Parse NVIDIA DGX offers list into normalized objects."""
        offers = []
        clusters = data.get("clusters", [])

        for cluster in clusters:
            try:
                # NVIDIA DGX fields:
                # - name: "DGX H100-8x"
                # - gpu_type: "H100"
                # - gpu_count: int
                # - memory_per_gpu_gb: int
                # - price_per_hour: float
                # - region: "us-east-1"
                # - availability: "available" | "reserved"

                cluster_name = cluster.get("name", "Unknown")
                gpu_type = cluster.get("gpu_type", "H100")
                gpu_count = cluster.get("gpu_count", 8)
                memory_per_gpu = cluster.get("memory_per_gpu_gb", 80)
                price_per_hour = float(cluster.get("price_per_hour", 0.0))
                region = cluster.get("region", "us-east-1")
                availability_status = cluster.get("availability", "available")

                # Estimate tokens per second (per cluster)
                tps_per_gpu = self._estimate_tps(gpu_type)
                total_tps = tps_per_gpu * gpu_count

                # Determine availability
                availability = (
                    "available" if availability_status == "available" else "limited"
                )

                # Build instance type name
                instance_type = f"{cluster_name} ({gpu_count}x {gpu_type})"

                # Estimate system specs
                total_memory_gb = memory_per_gpu * gpu_count
                cpu_cores = gpu_count * 16  # DGX typically has 16 CPU cores per GPU
                ram_gb = gpu_count * 256  # DGX typically has 256GB RAM per GPU

                offer = ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region=region,
                    instance_type=instance_type,
                    price_per_hour=price_per_hour,
                    tokens_per_second=total_tps,
                    availability=availability,
                    compliance_tags=["nvidia", "dgx", "enterprise", "premium"],
                    last_updated=datetime.now(timezone.utc),
                    gpu_memory_gb=memory_per_gpu,
                    cpu_cores=cpu_cores,
                    ram_gb=ram_gb,
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
        return 8000.0  # Default H100 estimate

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Validate NVIDIA DGX API credentials.

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
                "NVAPI-KEY": api_key,
            }

            client = await self.get_client()
            response = await client.get(
                f"{self.BASE_URL}/account/info", headers=headers
            )
            return response.status_code == 200

        except Exception as e:
            logger.error(f"NVIDIA DGX credential validation failed: {e}")
            return False

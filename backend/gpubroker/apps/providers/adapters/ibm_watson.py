"""
IBM Watson Adapter for GPUBROKER.

Live integration with IBM Cloud for Watson AI and GPU services.
https://cloud.ibm.com/apidocs
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from .base import BaseProviderAdapter, ProviderOffer
from ..common.messages import get_message

logger = logging.getLogger("gpubroker.providers.adapters.ibm_watson")


class IBMWatsonAdapter(BaseProviderAdapter):
    """
    Live IBM Cloud adapter using their VPC and Watson APIs.

    IBM Cloud provides GPU instances through VPC and AI services.
    """

    PROVIDER_NAME = "ibm_watson"
    BASE_URL = "https://resource-manager.cloud.ibm.com"

    # GPU performance estimates (tokens per second)
    TPS_MAPPING = {
        "p100": 2000,
        "v100": 3000,
        "a100": 8000,
        "l40s": 4000,
    }

    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """
        Fetch real-time IBM Cloud GPU offers.

        Args:
            auth_token: IBM Cloud IAM token

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

            # Get available instance profiles
            response = await client.get(
                "https://us-south.iaas.cloud.ibm.com/v1/instance/profiles?version=2022-10-28&generation=2",
                headers=headers,
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
        """Parse IBM Cloud offers list into normalized objects."""
        offers = []
        profiles = data.get("profiles", [])

        for profile in profiles:
            try:
                # IBM Cloud fields:
                # - name: "bx2-2x8"
                # - vcpu_count: int
                # - memory: int (GB)
                # - gpu_count: int
                # - gpu_manufacturer: "nvidia"
                # - gpu_model: "V100"
                # - architecture: "amd64" | "s390x"

                profile_name = profile.get("name", "Unknown")
                vcpu_count = profile.get("vcpu_count", 0)
                memory_gb = profile.get("memory", 0)
                gpu_count = profile.get("gpu_count", 0)
                gpu_manufacturer = profile.get("gpu_manufacturer", "")
                gpu_model = profile.get("gpu_model", "")

                # Skip if no GPU
                if gpu_count == 0:
                    continue

                # Get pricing from predefined mapping
                price_per_hour = self._get_pricing(profile_name)

                # Estimate tokens per second
                full_gpu_name = f"{gpu_manufacturer} {gpu_model}"
                tps_per_gpu = self._estimate_tps(full_gpu_name.lower())
                total_tps = tps_per_gpu * gpu_count

                # Determine GPU memory from model
                gpu_memory_gb = self._get_gpu_memory(gpu_model)

                # Assume available (would need separate inventory API call)
                availability = "available"

                instance_type = f"{profile_name} ({gpu_count}x {full_gpu_name})"

                offer = ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region="us-south",
                    instance_type=instance_type,
                    price_per_hour=price_per_hour,
                    tokens_per_second=total_tps,
                    availability=availability,
                    compliance_tags=["ibm", "watson", "enterprise", "vpc"],
                    last_updated=datetime.now(timezone.utc),
                    gpu_memory_gb=gpu_memory_gb,
                    cpu_cores=vcpu_count,
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

    def _get_pricing(self, profile_name: str) -> float:
        """Get estimated pricing for instance profile."""
        # Simplified pricing table (production would use Pricing Catalog API)
        pricing_map = {
            # V100 profiles
            "bc-gpu-v100": 2.50,
            "nc-gpu-v100": 3.00,
            "pd-gpu-v100": 4.00,
            # A100 profiles
            "bc-gpu-a100": 4.50,
            "nc-gpu-a100": 5.50,
            "pd-gpu-a100": 7.00,
            # L40S profiles
            "bc-gpu-l40s": 2.00,
            "nc-gpu-l40s": 2.50,
            "pd-gpu-l40s": 3.00,
        }
        return pricing_map.get(profile_name, 2.50)  # Default price

    def _get_gpu_memory(self, gpu_model: str) -> int:
        """Get GPU memory in GB from GPU model."""
        memory_map = {
            "V100": 32,
            "A100": 80,
            "L40S": 48,
            "P100": 16,
        }
        return memory_map.get(gpu_model, 32)

    def _estimate_tps(self, gpu_name: str) -> float:
        """
        Estimate tokens per second based on GPU type.

        Args:
            gpu_name: GPU name string

        Returns:
            Estimated tokens per second
        """
        for key, tps in self.TPS_MAPPING.items():
            if key in gpu_name.lower():
                return float(tps)
        return 3000.0  # Default estimate

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Validate IBM Cloud IAM credentials.

        Args:
            credentials: Dict with 'api_key' (IAM token)

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
            response = await client.get(
                f"{self.BASE_URL}/v1/resource_groups", headers=headers
            )
            return response.status_code == 200

        except Exception as e:
            logger.error(f"IBM Watson credential validation failed: {e}")
            return False

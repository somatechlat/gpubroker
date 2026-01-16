"""
Oracle OCI Adapter for GPUBROKER.

Live integration with Oracle Cloud Infrastructure for GPU instances.
https://docs.oracle.com/en-us/iaas/api/
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from .base import BaseProviderAdapter, ProviderOffer
from ..common.messages import get_message

logger = logging.getLogger("gpubroker.providers.adapters.oracle_oci")


class OracleOCIAdapter(BaseProviderAdapter):
    """
    Live Oracle OCI adapter using their Compute API.

    Oracle Cloud provides GPU instances through their Compute service.
    """

    PROVIDER_NAME = "oracle_oci"
    BASE_URL = "https://iaas.us-ashburn-1.oraclecloud.com"

    # GPU performance estimates (tokens per second)
    TPS_MAPPING = {
        "a100": 8000,
        "v100": 3000,
        "t4": 800,
    }

    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """
        Fetch real-time Oracle OCI GPU offers.

        Args:
            auth_token: OCI API key or token

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
                "opc-user-agent": "GPUBroker/2.0",
            }

            client = await self.get_client()
            response = await client.get(
                f"{self.BASE_URL}/20160918/instanceShapes?compartmentId=ocid1.compartment.oc1..example",
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
        """Parse Oracle OCI offers list into normalized objects."""
        offers = []
        shapes = data.get("items", [])

        for shape in shapes:
            try:
                # Oracle OCI fields:
                # - shape: "GPU.GPU.A100.1"
                # - ocpus: float
                # - memory_in_gbs: float
                # - gpus: int
                # - gpu_description: "NVIDIA A100"
                # - gpu_memory_in_gbs: float

                shape_name = shape.get("shape", "Unknown")
                ocpus = shape.get("ocpus", 0)
                memory_gb = int(shape.get("memory_in_gbs", 0))
                gpu_count = shape.get("gpus", 0)
                gpu_description = shape.get("gpu_description", "")
                gpu_memory_gb = int(shape.get("gpu_memory_in_gbs", 0))

                # Skip if no GPU
                if gpu_count == 0:
                    continue

                # Get pricing from predefined mapping
                price_per_hour = self._get_pricing(shape_name)

                # Estimate tokens per second
                tps_per_gpu = self._estimate_tps(gpu_description.lower())
                total_tps = tps_per_gpu * gpu_count

                # Assume available (would need separate availability API call)
                availability = "available"

                # Build instance type name
                instance_type = f"{shape_name} ({gpu_count}x {gpu_description})"

                # Convert OCPU to CPU cores (1 OCPU = 2 vCPUs on x86)
                cpu_cores = int(ocpus * 2)

                offer = ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region="us-ashburn-1",
                    instance_type=instance_type,
                    price_per_hour=price_per_hour,
                    tokens_per_second=total_tps,
                    availability=availability,
                    compliance_tags=["oracle", "oci", "enterprise"],
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

    def _get_pricing(self, shape_name: str) -> float:
        """Get estimated pricing for shape."""
        # Simplified pricing table (production would use Pricing API)
        pricing_map = {
            "GPU.GPU.A100.1": 3.20,  # 1x A100
            "GPU.GPU.A100.2": 6.40,  # 2x A100
            "GPU.GPU.A100.4": 12.80,  # 4x A100
            "GPU.GPU.A100.8": 25.60,  # 8x A100
            "GPU.GPU.V100.1": 1.50,  # 1x V100
            "GPU.GPU.V100.2": 3.00,  # 2x V100
            "GPU.GPU.T4.1": 0.35,  # 1x T4
            "GPU.GPU.T4.2": 0.70,  # 2x T4
            "GPU.GPU.T4.4": 1.40,  # 4x T4
            "GPU.GPU.T4.8": 2.80,  # 8x T4
        }
        return pricing_map.get(shape_name, 2.00)  # Default price

    def _estimate_tps(self, gpu_description: str) -> float:
        """
        Estimate tokens per second based on GPU description.

        Args:
            gpu_description: GPU description string

        Returns:
            Estimated tokens per second
        """
        for key, tps in self.TPS_MAPPING.items():
            if key in gpu_description.lower():
                return float(tps)
        return 3000.0  # Default estimate

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Validate Oracle OCI credentials.

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
                "opc-user-agent": "GPUBroker/2.0",
            }

            client = await self.get_client()
            response = await client.get(
                f"{self.BASE_URL}/20160918/users/ocid1.user.oc1..example",
                headers=headers,
            )
            return response.status_code == 200

        except Exception as e:
            logger.error(f"Oracle OCI credential validation failed: {e}")
            return False

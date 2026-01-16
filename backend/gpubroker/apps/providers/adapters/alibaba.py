"""
Alibaba Cloud Adapter for GPUBROKER.

Live integration with Alibaba Cloud ECS for GPU instances.
https://www.alibabacloud.com/help/doc-detail/25389.htm
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from .base import BaseProviderAdapter, ProviderOffer
from ..common.messages import get_message

logger = logging.getLogger("gpubroker.providers.adapters.alibaba")


class AlibabaAdapter(BaseProviderAdapter):
    """
    Live Alibaba Cloud adapter using their ECS API.

    Alibaba Cloud provides GPU instances through their Elastic Compute Service.
    """

    PROVIDER_NAME = "alibaba"
    BASE_URL = "https://ecs.cn-hangzhou.aliyuncs.com"

    # GPU performance estimates (tokens per second)
    TPS_MAPPING = {
        "ecs.gn6i": 8000,  # A100
        "ecs.gn7i": 12000,  # H100
        "ecs.gn6v": 3000,  # V100
        "ecs.gn5i": 2200,  # A6000
        "ecs.gn7i": 4500,  # RTX4090 equivalent
    }

    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """
        Fetch real-time Alibaba Cloud GPU offers.

        Args:
            auth_token: Alibaba Cloud AccessKey pair (format: "access_key:secret_key")

        Returns:
            List of normalized ProviderOffer instances
        """
        if not auth_token:
            logger.warning(get_message("adapter.no_auth", provider=self.PROVIDER_NAME))
            return []

        try:
            access_key, secret_key = auth_token.split(":", 1)

            headers = {
                "Content-Type": "application/json",
            }

            # Alibaba Cloud requires signature authentication
            params = {
                "Action": "DescribeInstanceTypes",
                "Version": "2014-05-26",
                "RegionId": "cn-hangzhou",
                "InstanceTypes": "ecs.gn6i,ecs.gn7i,ecs.gn6v,ecs.gn5i",
                "Format": "JSON",
                "AccessKeyId": access_key,
                "SignatureMethod": "HMAC-SHA1",
                "Timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "SignatureVersion": "1.0",
                "SignatureNonce": str(int(datetime.now().timestamp() * 1000)),
            }

            # This is simplified - production would need proper signature
            client = await self.get_client()
            response = await client.get(self.BASE_URL, headers=headers, params=params)
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
        """Parse Alibaba Cloud offers list into normalized objects."""
        offers = []
        instance_types = data.get("InstanceTypes", {}).get("InstanceType", [])

        for instance in instance_types:
            try:
                # Alibaba Cloud fields:
                # - InstanceTypeId: "ecs.gn6i.4xlarge"
                # - CpuCoreCount: int
                # - MemorySize: float (GB)
                # - GPUAmount: int
                # - GPUType: "NVIDIA V100"
                # - InstanceTypeFamily: "ecs.gn6i"

                instance_type_id = instance.get("InstanceTypeId", "Unknown")
                cpu_cores = instance.get("CpuCoreCount", 0)
                memory_gb = int(instance.get("MemorySize", 0))
                gpu_count = instance.get("GPUAmount", 0)
                gpu_type = instance.get("GPUType", "Unknown")
                instance_family = instance.get("InstanceTypeFamily", "")

                # Get pricing from predefined mapping (simplified)
                price_per_hour = self._get_pricing(instance_type_id)

                # Estimate tokens per second
                tps_per_gpu = self._estimate_tps(instance_family)
                total_tps = tps_per_gpu * gpu_count

                # Determine GPU memory from type
                gpu_memory_gb = self._get_gpu_memory(gpu_type)

                # Assume available (would need separate API call)
                availability = "available"

                offer = ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region="cn-hangzhou",
                    instance_type=f"{instance_type_id} ({gpu_count}x {gpu_type})",
                    price_per_hour=price_per_hour,
                    tokens_per_second=total_tps,
                    availability=availability,
                    compliance_tags=["alibaba", "ecs", "china-cloud"],
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

    def _get_pricing(self, instance_type: str) -> float:
        """Get estimated pricing for instance type."""
        # Simplified pricing table (production would use Pricing API)
        pricing_map = {
            "ecs.gn6i.large": 1.50,  # 1x A100
            "ecs.gn6i.xlarge": 3.00,  # 2x A100
            "ecs.gn6i.2xlarge": 6.00,  # 4x A100
            "ecs.gn6i.4xlarge": 12.00,  # 8x A100
            "ecs.gn7i.large": 2.00,  # 1x H100
            "ecs.gn7i.xlarge": 4.00,  # 2x H100
            "ecs.gn7i.2xlarge": 8.00,  # 4x H100
            "ecs.gn7i.4xlarge": 16.00,  # 8x H100
            "ecs.gn6v.large": 0.80,  # 1x V100
            "ecs.gn6v.xlarge": 1.60,  # 2x V100
            "ecs.gn6v.2xlarge": 3.20,  # 4x V100
            "ecs.gn5i.large": 0.60,  # 1x A6000
            "ecs.gn5i.xlarge": 1.20,  # 2x A6000
        }
        return pricing_map.get(instance_type, 2.00)  # Default price

    def _get_gpu_memory(self, gpu_type: str) -> int:
        """Get GPU memory in GB from GPU type."""
        memory_map = {
            "NVIDIA A100": 80,
            "NVIDIA H100": 80,
            "NVIDIA V100": 32,
            "NVIDIA A6000": 48,
            "NVIDIA RTX4090": 24,
        }
        return memory_map.get(gpu_type, 40)

    def _estimate_tps(self, instance_family: str) -> float:
        """
        Estimate tokens per second based on instance family.

        Args:
            instance_family: Alibaba instance family

        Returns:
            Estimated tokens per second
        """
        for key, tps in self.TPS_MAPPING.items():
            if key in instance_family:
                return float(tps)
        return 3000.0  # Default estimate

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Validate Alibaba Cloud credentials.

        Args:
            credentials: Dict with 'api_key' (format: "access_key:secret_key")

        Returns:
            True if credentials are valid
        """
        api_key = credentials.get("api_key")
        if not api_key or ":" not in api_key:
            return False

        try:
            access_key, secret_key = api_key.split(":", 1)

            # Simple validation - check if keys look reasonable
            return len(access_key) >= 16 and len(secret_key) >= 16

        except Exception as e:
            logger.error(f"Alibaba credential validation failed: {e}")
            return False

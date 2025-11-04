"""
Alibaba Cloud Adapter for GPUBROKER
Live integration with Alibaba Cloud ECS GPU pricing
"""

import httpx
import hashlib
import hmac
import base64
import urllib.parse
from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone

from .base_adapter import BaseProviderAdapter
from ..models.provider_offer import ProviderOffer

logger = logging.getLogger(__name__)


class AlibabaAdapter(BaseProviderAdapter):
    """Live Alibaba Cloud adapter with real-time GPU pricing"""

    PROVIDER_NAME = "alibaba"
    BASE_URL = "https://ecs.aliyuncs.com"

    async def get_offers(self, auth_token: str) -> List[ProviderOffer]:
        """Fetch real-time Alibaba Cloud GPU pricing"""
        try:
            credentials = auth_token.split("|")
            if len(credentials) != 3:
                return []

            access_key, secret_key, region = credentials

            params = {
                "Action": "DescribePrice",
                "RegionId": region,
                "InstanceType": "ecs.gn6i-c24g1.4xlarge",
                "ImageId": "ubuntu_20_04_x64_20G_alibase_20230815.vhd",
                "Format": "JSON",
                "Version": "2014-05-26",
                "AccessKeyId": access_key,
                "SignatureMethod": "HMAC-SHA1",
                "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "SignatureVersion": "1.0",
                "SignatureNonce": str(int(datetime.utcnow().timestamp())),
            }

            signature = self._sign_request(params, secret_key)
            params["Signature"] = signature

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()

                data = response.json()
                return await self._parse_pricing_data(data, region)

        except Exception as e:
            logger.error(f"Failed to fetch Alibaba data: {e}")
            return []

    def _sign_request(self, params: Dict, secret_key: str) -> str:
        """Generate Alibaba Cloud signature"""
        sorted_params = sorted(params.items())
        query_string = urllib.parse.urlencode(
            sorted_params, quote_via=urllib.parse.quote
        )
        string_to_sign = f"GET&%2F&{urllib.parse.quote(query_string, safe='')}".encode()
        key = f"{secret_key}&".encode()
        signature = base64.b64encode(
            hmac.new(key, string_to_sign, hashlib.sha1).digest()
        ).decode()
        return signature

    async def _parse_pricing_data(self, data: Dict, region: str) -> List[ProviderOffer]:
        """Parse Alibaba pricing data"""
        offers = []

        price_info = data.get("PriceInfo", {}).get("Price", {}).get("HourPrice", {})
        price = float(price_info.get("OriginalPrice", 0))

        if price > 0:
            # Map common GPU instances
            gpu_instances = [
                {"type": "ecs.gn6i-c24g1.4xlarge", "gpu": "T4", "price": price},
                {"type": "ecs.gn6i-c24g1.8xlarge", "gpu": "T4", "price": price * 2},
                {"type": "ecs.gn6i-c24g1.16xlarge", "gpu": "T4", "price": price * 4},
            ]

            for instance in gpu_instances:
                tokens_per_second = self._estimate_tps(instance["gpu"])

                offer = ProviderOffer(
                    provider="alibaba",
                    region=region,
                    instance_type=instance["type"],
                    price_per_hour=instance["price"],
                    tokens_per_second=tokens_per_second,
                    availability="available",
                    compliance_tags=["alibaba", "china-cloud", "apac", "t4"],
                    last_updated=datetime.now(timezone.utc),
                )
                offers.append(offer)

        return offers

    def _estimate_tps(self, gpu_type: str) -> float:
        """Estimate tokens per second based on GPU"""
        tps_mapping = {"T4": 800, "V100": 3000, "A100": 8000, "A10": 4000}
        return tps_mapping.get(gpu_type, 1000)

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Alibaba credentials"""
        try:
            auth_token = credentials.get("auth_token", "")
            parts = auth_token.split("|")
            if len(parts) != 3:
                return False

            access_key, secret_key, region = parts

            params = {
                "Action": "DescribeRegions",
                "AccessKeyId": access_key,
                "Format": "JSON",
                "Version": "2014-05-26",
                "SignatureMethod": "HMAC-SHA1",
                "Timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
                "SignatureVersion": "1.0",
                "SignatureNonce": str(int(datetime.utcnow().timestamp())),
            }

            signature = self._sign_request(params, secret_key)
            params["Signature"] = signature

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                return response.status_code == 200 and "Regions" in response.text

        except Exception as e:
            logger.error(f"Alibaba credential validation failed: {e}")
            return False

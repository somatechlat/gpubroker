"""
Google Vertex AI Adapter for GPUBROKER
Live integration with Google Cloud Vertex AI pricing and instance availability
"""

import asyncio
import os
import httpx
from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone

from .base_adapter import BaseProviderAdapter
from ..models.provider_offer import ProviderOffer
from ..core.security import hash_provider_key

logger = logging.getLogger(__name__)


class GoogleVertexAIAdapter(BaseProviderAdapter):
    """Live Google Cloud Vertex AI adapter with real-time pricing"""

    PROVIDER_NAME = "google_vertex_ai"
    BASE_URL = "https://cloudbilling.googleapis.com/v1"

    async def get_offers(self, auth_token: str) -> List[ProviderOffer]:
        """Fetch real-time Google Vertex AI pricing and availability"""
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch Vertex AI compute pricing
                response = await client.get(
                    f"{self.BASE_URL}/services/6F81-5844-456A/skus",
                    headers=headers,
                    params={
                        "pageSize": 1000,
                        "filter": 'description : "Vertex AI" AND description : "GPU"',
                    },
                )
                response.raise_for_status()

                pricing_data = response.json()
                return await self._parse_pricing_data(pricing_data)

        except Exception as e:
            logger.error(f"Failed to fetch Google Vertex AI data: {e}")
            return []

    async def _parse_pricing_data(self, data: Dict) -> List[ProviderOffer]:
        """Parse Google pricing data into normalized offers"""
        offers = []

        skus = data.get("skus", [])
        for sku in skus:
            description = sku.get("description", "")

            # Filter for GPU instances
            if not any(
                gpu in description.lower() for gpu in ["a100", "v100", "t4", "h100"]
            ):
                continue

            # Extract instance type from description
            instance_type = self._extract_instance_type(description)
            if not instance_type:
                continue

            # Get pricing info
            pricing_info = sku.get("pricingInfo", [])
            if not pricing_info:
                continue

            # Get hourly pricing
            price = self._extract_hourly_price(pricing_info)
            if not price:
                continue

            # Map to regions
            service_regions = sku.get("serviceRegions", [])
            for region in service_regions:
                tokens_per_second = self._estimate_tps(instance_type)

                offer = ProviderOffer(
                    provider="google_vertex_ai",
                    region=region,
                    instance_type=instance_type,
                    price_per_hour=price,
                    tokens_per_second=tokens_per_second,
                    availability="available",
                    compliance_tags=self._get_compliance_tags(region),
                    last_updated=datetime.now(timezone.utc),
                )
                offers.append(offer)

        return offers

    def _extract_instance_type(self, description: str) -> Optional[str]:
        """Extract instance type from Google SKU description"""
        # Extract patterns like "n1-standard-8 with 1 x NVIDIA Tesla V100"
        import re

        patterns = [
            r"(n1-standard-\d+|n1-highmem-\d+|a2-highgpu-\d+g)",
            r"(n1-ultramem-\d+)",
            r"(c2-standard-\d+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, description)
            if match:
                # Add GPU info
                if "v100" in description.lower():
                    return f"{match.group(1)}-v100"
                elif "a100" in description.lower():
                    return f"{match.group(1)}-a100"
                elif "t4" in description.lower():
                    return f"{match.group(1)}-t4"
                elif "h100" in description.lower():
                    return f"{match.group(1)}-h100"
                return match.group(1)

        return None

    def _extract_hourly_price(self, pricing_info: List[Dict]) -> Optional[float]:
        """Extract hourly price from Google pricing info"""
        try:
            for info in pricing_info:
                pricing_expression = info.get("pricingExpression", {})
                usage_unit = pricing_expression.get("usageUnit")

                if usage_unit == "h":
                    tiered_rates = pricing_expression.get("tieredRates", [])
                    if tiered_rates:
                        # Get the base hourly rate
                        rate = tiered_rates[0].get("unitPrice", {}).get("units", 0)
                        nanos = tiered_rates[0].get("unitPrice", {}).get("nanos", 0)
                        return float(rate) + (float(nanos) / 1e9)
        except Exception as e:
            logger.error(f"Failed to extract hourly price: {e}")

        return None

    def _estimate_tps(self, instance_type: str) -> float:
        """Estimate tokens per second based on Google instance type"""
        tps_mapping = {
            "n1-standard-4-v100": 500,
            "n1-standard-8-v100": 1000,
            "n1-standard-16-v100": 2000,
            "n1-highmem-8-a100": 2000,
            "n1-highmem-16-a100": 4000,
            "n1-highmem-32-a100": 8000,
            "a2-highgpu-1g-a100": 2000,
            "a2-highgpu-2g-a100": 4000,
            "a2-highgpu-4g-a100": 8000,
            "n1-standard-2-t4": 200,
            "n1-standard-4-t4": 400,
            "n1-standard-8-t4": 800,
        }
        return tps_mapping.get(instance_type, 100)

    def _get_compliance_tags(self, region: str) -> List[str]:
        """Get compliance tags for Google region"""
        tags = ["google", "vertexai", "gcp", "cloud"]

        # GDPR compliance for EU regions
        if region.startswith("europe-"):
            tags.extend(["gdpr_compliant", "soc2_compliant"])

        # HIPAA compliance for US regions
        if region.startswith("us-"):
            tags.extend(["hipaa_compliant", "soc2_compliant"])

        return tags

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Google credentials"""
        try:
            project_id = credentials.get("project_id")
            service_account_key = credentials.get("service_account_key")

            if not project_id or not service_account_key:
                return False

            # Test credentials with Google Cloud Resource Manager
            headers = {
                "Authorization": f"Bearer {credentials.get('auth_token')}",
                "X-Google-Project": project_id,
                "X-Google-Service-Key": service_account_key,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://cloudresourcemanager.googleapis.com/v1/projects/{project_id}",
                    headers=headers,
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Google credential validation failed: {e}")
            return False

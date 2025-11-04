"""
Azure ML Adapter for GPUBROKER
Live integration with Azure Machine Learning pricing and instance availability
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


class AzureMLAdapter(BaseProviderAdapter):
    """Live Azure Machine Learning adapter with real-time pricing"""

    PROVIDER_NAME = "azure_ml"
    BASE_URL = "https://management.azure.com"

    async def get_offers(self, auth_token: str) -> List[ProviderOffer]:
        """Fetch real-time Azure ML pricing and availability"""
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Fetch Azure ML compute pricing
                response = await client.get(
                    f"{self.BASE_URL}/providers/Microsoft.MachineLearningServices/skus",
                    headers=headers,
                    params={
                        "api-version": "2023-04-01",
                        "$filter": "resourceType eq 'compute'",
                    },
                )
                response.raise_for_status()

                pricing_data = response.json()
                return await self._parse_pricing_data(pricing_data)

        except Exception as e:
            logger.error(f"Failed to fetch Azure ML data: {e}")
            return []

    async def _parse_pricing_data(self, data: Dict) -> List[ProviderOffer]:
        """Parse Azure pricing data into normalized offers"""
        offers = []

        skus = data.get("value", [])
        for sku in skus:
            sku_name = sku.get("name")

            # Skip non-GPU instances
            if not self._is_gpu_instance(sku_name):
                continue

            # Get region info
            location_info = sku.get("locationInfo", [])
            for loc in location_info:
                region = loc.get("location")

                # Get pricing from retail API
                price = await self._get_pricing_for_sku(sku_name, region)
                if not price:
                    continue

                # Calculate tokens per second
                tokens_per_second = self._estimate_tps(sku_name)

                offer = ProviderOffer(
                    provider="azure_ml",
                    region=region,
                    instance_type=sku_name,
                    price_per_hour=price,
                    tokens_per_second=tokens_per_second,
                    availability="available",
                    compliance_tags=self._get_compliance_tags(region),
                    last_updated=datetime.now(timezone.utc),
                )
                offers.append(offer)

        return offers

    async def _get_pricing_for_sku(self, sku_name: str, region: str) -> Optional[float]:
        """Get pricing for specific Azure SKU"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"https://prices.azure.com/api/retail/prices",
                    params={
                        "$filter": f"serviceName eq 'Azure Machine Learning' and armRegionName eq '{region}' and armSkuName eq '{sku_name}'"
                    },
                )
                response.raise_for_status()

                data = response.json()
                items = data.get("Items", [])
                if items:
                    # Get the hourly price
                    price = items[0].get("retailPrice")
                    return float(price) if price else None

        except Exception as e:
            logger.error(f"Failed to get pricing for {sku_name} in {region}: {e}")

        return None

    def _is_gpu_instance(self, instance_type: str) -> bool:
        """Check if Azure instance has GPU"""
        gpu_instances = ["Standard_NC", "Standard_ND", "Standard_NV"]
        return any(instance_type.startswith(prefix) for prefix in gpu_instances)

    def _estimate_tps(self, instance_type: str) -> float:
        """Estimate tokens per second based on Azure instance type"""
        tps_mapping = {
            "Standard_NC6s_v3": 500,
            "Standard_NC12s_v3": 1000,
            "Standard_NC24s_v3": 2000,
            "Standard_ND40rs_v2": 4000,
            "Standard_NV6": 200,
            "Standard_NV12": 400,
            "Standard_NV24": 800,
            "Standard_NC4as_T4_v3": 300,
            "Standard_NC8as_T4_v3": 600,
            "Standard_NC16as_T4_v3": 1200,
        }
        return tps_mapping.get(instance_type, 100)

    def _get_compliance_tags(self, region: str) -> List[str]:
        """Get compliance tags for Azure region"""
        tags = ["azure", "azureml", "cloud"]

        # GDPR compliance for EU regions
        if region.startswith("westeurope") or region.startswith("northeurope"):
            tags.extend(["gdpr_compliant", "soc2_compliant"])

        # HIPAA compliance for US regions
        if region.startswith("eastus") or region.startswith("westus"):
            tags.extend(["hipaa_compliant", "soc2_compliant"])

        return tags

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Azure credentials"""
        try:
            subscription_id = credentials.get("subscription_id")
            client_id = credentials.get("client_id")
            client_secret = credentials.get("client_secret")
            tenant_id = credentials.get("tenant_id")

            if not all([subscription_id, client_id, client_secret, tenant_id]):
                return False

            # Test credentials with Azure REST API
            headers = {
                "Authorization": f"Bearer {credentials.get('auth_token')}",
                "X-Azure-Subscription": subscription_id,
                "X-Azure-Client-Id": client_id,
                "X-Azure-Client-Secret": client_secret,
                "X-Azure-Tenant-Id": tenant_id,
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/subscriptions/{subscription_id}/providers/Microsoft.MachineLearningServices",
                    headers=headers,
                    params={"api-version": "2023-04-01"},
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Azure credential validation failed: {e}")
            return False

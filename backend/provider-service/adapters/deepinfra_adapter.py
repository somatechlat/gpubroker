"""
DeepInfra Adapter for GPUBROKER
Live integration with DeepInfra API for model inference pricing
"""

import httpx
from typing import Dict, List
import logging
from datetime import datetime, timezone

from .base_adapter import BaseProviderAdapter
from ..models.provider_offer import ProviderOffer

logger = logging.getLogger(__name__)


class DeepInfraAdapter(BaseProviderAdapter):
    """Live DeepInfra adapter with real-time pricing"""

    PROVIDER_NAME = "deepinfra"
    BASE_URL = "https://api.deepinfra.com"

    async def get_offers(self, auth_token: str) -> List[ProviderOffer]:
        """Fetch real-time DeepInfra pricing"""
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get model pricing and availability
                response = await client.get(
                    f"{self.BASE_URL}/v1/models", headers=headers
                )
                response.raise_for_status()

                data = response.json()
                return await self._parse_model_data(data)

        except Exception as e:
            logger.error(f"Failed to fetch DeepInfra data: {e}")
            raise RuntimeError("DeepInfra data fetch failed")

    async def _parse_model_data(self, data: Dict) -> List[ProviderOffer]:
        """Parse DeepInfra model data into normalized offers"""
        offers = []

        models = data.get("models", [])
        for model in models:
            model_id = model.get("id")
            if not model_id:
                continue

            # Get pricing from model metadata
            pricing = model.get("pricing", {})
            price_per_token = pricing.get("input", 0.0)

            # Convert to hourly rate assuming 1000 tokens/sec for 1 hour = 3.6M tokens
            price_per_hour = price_per_token * 3_600_000

            tokens_per_second = self._estimate_tps(model_id)

            offer = ProviderOffer(
                provider="deepinfra",
                region="us-central-1",
                instance_type=f"deepinfra-{model_id}",
                price_per_hour=price_per_hour,
                tokens_per_second=tokens_per_second,
                availability="available",
                compliance_tags=["deepinfra", "inference", "api", "us-central"],
                last_updated=datetime.now(timezone.utc),
            )
            offers.append(offer)

        return offers

    def _estimate_tps(self, model_id: str) -> float:
        """Estimate tokens per second for DeepInfra models"""
        tps_mapping = {
            "meta-llama/llama-3.1-8b": 120,
            "meta-llama/llama-3.1-70b": 45,
            "meta-llama/llama-3.1-405b": 25,
            "mistralai/mistral-7b": 150,
            "mistralai/mixtral-8x7b": 80,
            "google/gemma-2-9b": 200,
            "google/gemma-2-27b": 100,
        }

        for key, tps in tps_mapping.items():
            if key in model_id.lower():
                return tps

        return 100  # Default for DeepInfra

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate DeepInfra credentials"""
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                return False

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/v1/models", headers=headers
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"DeepInfra credential validation failed: {e}")
            return False

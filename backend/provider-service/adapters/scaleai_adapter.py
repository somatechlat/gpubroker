"""
ScaleAI Adapter for GPUBROKER
Live integration with ScaleAI Generative AI Platform pricing
"""

import httpx
from typing import Dict, List
import logging
from datetime import datetime, timezone

from .base_adapter import BaseProviderAdapter
from ..models.provider_offer import ProviderOffer

logger = logging.getLogger(__name__)


class ScaleAIAdapter(BaseProviderAdapter):
    """Live ScaleAI adapter with real-time pricing"""

    PROVIDER_NAME = "scaleai"
    BASE_URL = "https://api.scale.com/v1"

    async def get_offers(self, auth_token: str) -> List[ProviderOffer]:
        """Fetch real-time ScaleAI pricing"""
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get model pricing and availability
                response = await client.get(
                    f"{self.BASE_URL}/llm/endpoints", headers=headers
                )
                response.raise_for_status()

                data = response.json()
                return await self._parse_endpoint_data(data)

        except Exception as e:
            logger.error(f"Failed to fetch ScaleAI data: {e}")
            return []

    async def _parse_endpoint_data(self, data: Dict) -> List[ProviderOffer]:
        """Parse ScaleAI endpoint data into normalized offers"""
        offers = []

        endpoints = data.get("endpoints", [])
        for endpoint in endpoints:
            model_name = endpoint.get("model_name")
            if not model_name:
                continue

            # ScaleAI pricing based on model and usage
            pricing = endpoint.get("pricing", {})
            price_per_token = pricing.get("per_token", 0.0)

            # Convert to hourly rate assuming 1000 tokens/sec for 1 hour
            price_per_hour = price_per_token * 3_600_000

            tokens_per_second = self._estimate_tps_scaleai(model_name)

            offer = ProviderOffer(
                provider="scaleai",
                region="us-west-2",
                instance_type=f"scaleai-{model_name}",
                price_per_hour=price_per_hour,
                tokens_per_second=tokens_per_second,
                availability=endpoint.get("status", "available"),
                compliance_tags=["scaleai", "enterprise", "api", "us-west"],
                last_updated=datetime.now(timezone.utc),
            )
            offers.append(offer)

        return offers

    def _estimate_tps_scaleai(self, model_name: str) -> float:
        """Estimate tokens per second for ScaleAI models"""
        tps_mapping = {
            "llama-3.1-8b": 80,
            "llama-3.1-70b": 35,
            "llama-3.1-405b": 15,
            "mistral-7b": 120,
            "mixtral-8x7b": 60,
            "claude-3-haiku": 200,
            "claude-3-sonnet": 100,
            "claude-3-opus": 50,
        }

        for key, tps in tps_mapping.items():
            if key in model_name.lower():
                return tps

        return 75  # Default for ScaleAI

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate ScaleAI credentials"""
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
                    f"{self.BASE_URL}/llm/endpoints", headers=headers
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"ScaleAI credential validation failed: {e}")
            return False

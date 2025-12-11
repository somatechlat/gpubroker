"""
Cerebras Adapter for GPUBROKER
Live integration with Cerebras CS-2 Wafer-Scale Engine pricing
"""

import httpx
from typing import Dict, List
import logging
from datetime import datetime, timezone

from .base_adapter import BaseProviderAdapter
from models.provider_offer import ProviderOffer

logger = logging.getLogger(__name__)


class CerebrasAdapter(BaseProviderAdapter):
    """Live Cerebras adapter with real-time pricing"""

    PROVIDER_NAME = "cerebras"
    BASE_URL = "https://api.cerebras.ai/v1"

    async def get_offers(self, auth_token: str) -> List[ProviderOffer]:
        """Fetch real-time Cerebras pricing"""
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                # Get model pricing and availability
                response = await client.get(f"{self.BASE_URL}/models", headers=headers)
                response.raise_for_status()

                data = response.json()
                return await self._parse_model_data(data)

        except Exception as e:
            logger.error(f"Failed to fetch Cerebras data: {e}")
            raise RuntimeError("Cerebras data fetch failed")

    async def _parse_model_data(self, data: Dict) -> List[ProviderOffer]:
        """Parse Cerebras model data into normalized offers"""
        offers = []

        models = data.get("data", [])
        for model in models:
            model_id = model.get("id")
            if not model_id or "cerebras" not in model_id.lower():
                continue

            # Cerebras uses fixed pricing per model
            pricing_info = model.get("pricing", {})
            price_per_request = pricing_info.get("price", 0.0)

            # Convert to hourly assuming 100 requests/hour for consistent pricing
            price_per_hour = price_per_request * 100

            tokens_per_second = self._estimate_tps_wse(model_id)

            offer = ProviderOffer(
                provider="cerebras",
                region="us-east-1",
                instance_type=f"cerebras-{model_id}",
                price_per_hour=price_per_hour,
                tokens_per_second=tokens_per_second,
                availability="available",
                compliance_tags=["cerebras", "wse", "wafer-scale", "us-east"],
                last_updated=datetime.now(timezone.utc),
            )
            offers.append(offer)

        return offers

    def _estimate_tps_wse(self, model_id: str) -> float:
        """Estimate tokens per second for Cerebras Wafer-Scale Engine"""
        # Cerebras CS-2 is extremely fast due to wafer-scale architecture
        tps_mapping = {
            "cerebras-llama3.1-8b": 4500,  # 4500 tokens/sec on CS-2
            "cerebras-llama3.1-70b": 1800,  # 1800 tokens/sec on CS-2
            "cerebras-llama3.2-3b": 8000,  # 8000 tokens/sec on CS-2
        }

        for key, tps in tps_mapping.items():
            if key in model_id.lower():
                return tps

        return 3000  # Default for Cerebras WSE

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Cerebras credentials"""
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                return False

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.BASE_URL}/models", headers=headers)
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Cerebras credential validation failed: {e}")
            return False

"""
Spell Adapter for GPUBROKER
Live integration with Spell.run ML platform pricing
"""

import httpx
from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone

from .base_adapter import BaseProviderAdapter
from ..models.provider_offer import ProviderOffer

logger = logging.getLogger(__name__)


class SpellAdapter(BaseProviderAdapter):
    """Live Spell.run adapter with ML platform pricing"""

    PROVIDER_NAME = "spell"
    BASE_URL = "https://api.spell.ml/v1"

    async def get_offers(self, auth_token: str) -> List[ProviderOffer]:
        """Fetch real-time Spell.run pricing"""
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/runs/pricing", headers=headers
                )
                response.raise_for_status()

                data = response.json()
                return await self._parse_pricing_data(data)

        except Exception as e:
            logger.error(f"Failed to fetch Spell data: {e}")
            return []

    async def _parse_pricing_data(self, data: Dict) -> List[ProviderOffer]:
        """Parse Spell instance data"""
        offers = []

        instance_types = data.get("instance_types", [])
        for instance in instance_types:
            name = instance.get("name")
            gpu_type = instance.get("gpu", "unknown")
            price_hour = float(instance.get("price_per_hour", 0))

            if not name or price_hour == 0:
                continue

            tokens_per_second = self._estimate_tps_spell(gpu_type)

            offer = ProviderOffer(
                provider="spell",
                region="us-east-1",
                instance_type=name,
                price_per_hour=price_hour,
                tokens_per_second=tokens_per_second,
                availability="available",
                compliance_tags=["spell", "ml-platform", "cloud", gpu_type.lower()],
                last_updated=datetime.now(timezone.utc),
            )
            offers.append(offer)

        return offers

    def _estimate_tps_spell(self, gpu_type: str) -> float:
        """Estimate tokens per second for Spell instances"""
        tps_mapping = {"t4": 800, "v100": 3000, "a100": 8000, "k80": 600, "p100": 1800}
        return tps_mapping.get(gpu_type.lower(), 1000)

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Spell credentials"""
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                return False

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.BASE_URL}/user", headers=headers)
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Spell credential validation failed: {e}")
            return False

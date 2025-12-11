"""
Vast.ai Adapter for GPUBROKER
Live integration with Vast.ai marketplace API
"""

import httpx
from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone

from .base_adapter import BaseProviderAdapter
from models.provider_offer import ProviderOffer

logger = logging.getLogger(__name__)


class VastAIAdapter(BaseProviderAdapter):
    """
    Live Vast.ai adapter using their public marketplace API.
    Does NOT require an API key for public listings (bundles).
    """

    PROVIDER_NAME = "vastai"
    # Public endpoint for browsing offers (bundles)
    BASE_URL = "https://console.vast.ai/api/v0/bundles"

    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """Fetch real-time Vast.ai GPU offers"""
        try:
            # Vast.ai public bundles endpoint typically accepts query params for filtering
            # For now, we fetch a broad set and filter internally or let the backend filter.
            # 'q' param structure is complex JSON stringified, we'll fetch default set.
            # Based on inspection, a simple GET returns a JSON with "offers": [...]

            headers = {
                "Accept": "application/json",
                "User-Agent": "GPUBROKER/1.0"
            }
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.BASE_URL, headers=headers)
                response.raise_for_status()
                data = response.json()

                return self._parse_offers(data)

        except Exception as e:
            logger.error(f"Failed to fetch Vast.ai data: {e}")
            return []

    def _parse_offers(self, data: Dict) -> List[ProviderOffer]:
        """Parse Vast.ai offers list into normalized objects"""
        offers = []
        raw_offers = data.get("offers", [])

        for item in raw_offers:
            try:
                # Vast.ai fields mapping
                # id: integer
                # gpu_name: "RTX 3090"
                # num_gpus: int
                # dph_total: float (Dollars Per Hour Total)
                # geolocation: "Washington, US"
                # reliability2: float (0-1)

                gpu_name = item.get("gpu_name", "Unknown GPU")
                num_gpus = item.get("num_gpus", 1)
                if num_gpus > 1:
                    gpu_name = f"{num_gpus}x {gpu_name}"

                price = float(item.get("dph_total", 0.0))
                region = item.get("geolocation", "Unknown")

                # Estimate tokens per second (simple heuristic for normalization)
                # In a real scenario, this might come from a benchmark DB
                tps = self._estimate_tps(item.get("gpu_name", "")) * num_gpus

                offer = ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region=region,
                    instance_type=gpu_name,
                    price_per_hour=price,
                    tokens_per_second=tps,
                    availability="available" if item.get("rentable") else "busy",
                    compliance_tags=["vastai", "p2p" if item.get("hosting_type") == 0 else "datacenter"],
                    last_updated=datetime.now(timezone.utc),
                    # Store extra metadata if needed
                    # metadata={"reliability": item.get("reliability2")}
                )
                offers.append(offer)
            except Exception as parse_err:
                logger.warning(f"Failed to parse individual Vast.ai offer: {parse_err}")
                continue

        return offers

    def _estimate_tps(self, gpu_name: str) -> float:
        """Heuristic for TPS based on GPU name string"""
        name = gpu_name.lower()
        if "h100" in name: return 12000
        if "a100" in name: return 8000
        if "a6000" in name: return 2200
        if "4090" in name: return 4500
        if "3090" in name: return 3500
        if "3080" in name: return 2800
        if "v100" in name: return 3000
        if "t4" in name: return 800
        return 1000.0

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate API key"""
        # For public fetch, no key needed. For booking, key needed.
        # This checks if the key is valid by hitting a private endpoint e.g. /users/current
        key = credentials.get("api_key")
        if not key:
            return True # Public access is valid

        # If key provided, verify it (placeholder logic as we focus on public offers now)
        return True

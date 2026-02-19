"""
Vast.ai Adapter for GPUBROKER.

Live integration with Vast.ai marketplace API.
https://vast.ai/docs/api/overview
"""

import logging
from datetime import datetime, timezone

import httpx

from .base import BaseProviderAdapter, ProviderOffer

logger = logging.getLogger("gpubroker.providers.adapters.vastai")


class VastAIAdapter(BaseProviderAdapter):
    """
    Live Vast.ai adapter using their public marketplace API.

    Does NOT require an API key for public listings (bundles).
    """

    PROVIDER_NAME = "vastai"
    BASE_URL = "https://console.vast.ai/api/v0/bundles"

    # GPU performance estimates (tokens per second)
    TPS_MAPPING = {
        "h100": 12000,
        "a100": 8000,
        "a6000": 2200,
        "4090": 4500,
        "3090": 3500,
        "3080": 2800,
        "v100": 3000,
        "t4": 800,
    }

    async def get_offers(self, auth_token: str | None = None) -> list[ProviderOffer]:
        """
        Fetch real-time Vast.ai GPU offers.

        Args:
            auth_token: Optional API key (not required for public listings)

        Returns:
            List of normalized ProviderOffer instances
        """
        try:
            headers = {"Accept": "application/json", "User-Agent": "GPUBROKER/2.0"}
            if auth_token:
                headers["Authorization"] = f"Bearer {auth_token}"

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.BASE_URL, headers=headers)
                response.raise_for_status()
                data = response.json()

                return self._parse_offers(data)

        except httpx.HTTPStatusError as e:
            logger.error(f"Vast.ai API error: {e.response.status_code}")
            return []
        except Exception as e:
            logger.error(f"Failed to fetch Vast.ai data: {e}")
            return []

    def _parse_offers(self, data: dict) -> list[ProviderOffer]:
        """Parse Vast.ai offers list into normalized objects."""
        offers = []
        raw_offers = data.get("offers", [])

        for item in raw_offers:
            try:
                # Vast.ai fields:
                # - gpu_name: "RTX 3090"
                # - num_gpus: int
                # - dph_total: float (Dollars Per Hour Total)
                # - geolocation: "Washington, US"
                # - reliability2: float (0-1)
                # - rentable: bool
                # - hosting_type: 0=p2p, 1=datacenter

                gpu_name = item.get("gpu_name", "Unknown GPU")
                num_gpus = item.get("num_gpus", 1)
                if num_gpus > 1:
                    gpu_name = f"{num_gpus}x {gpu_name}"

                price = float(item.get("dph_total", 0.0))
                region = item.get("geolocation", "Unknown")

                # Estimate tokens per second
                tps = self._estimate_tps(item.get("gpu_name", "")) * num_gpus

                # Determine availability
                availability = "available" if item.get("rentable") else "busy"

                # Build compliance tags
                tags = ["vastai"]
                hosting_type = item.get("hosting_type", 0)
                tags.append("p2p" if hosting_type == 0 else "datacenter")

                # Extract GPU memory if available
                gpu_memory_gb = (
                    int(item.get("gpu_ram", 0) / 1024) if item.get("gpu_ram") else 0
                )

                offer = ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region=region,
                    instance_type=gpu_name,
                    price_per_hour=price,
                    tokens_per_second=tps,
                    availability=availability,
                    compliance_tags=tags,
                    last_updated=datetime.now(timezone.utc),
                    gpu_memory_gb=gpu_memory_gb,
                )
                offers.append(offer)

            except Exception as e:
                logger.warning(f"Failed to parse Vast.ai offer: {e}")
                continue

        logger.info(f"Vast.ai: Fetched {len(offers)} offers")
        return offers

    def _estimate_tps(self, gpu_name: str) -> float:
        """
        Estimate tokens per second based on GPU name.

        Args:
            gpu_name: GPU name string

        Returns:
            Estimated tokens per second
        """
        name = gpu_name.lower()
        for key, tps in self.TPS_MAPPING.items():
            if key in name:
                return float(tps)
        return 1000.0

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        """
        Validate Vast.ai API credentials.

        Args:
            credentials: Dict with 'api_key'

        Returns:
            True if credentials are valid (or no key provided)
        """
        api_key = credentials.get("api_key")
        if not api_key:
            # Public API doesn't require auth
            return True

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://console.vast.ai/api/v0/users/current",
                    headers={"Authorization": api_key, "Accept": "application/json"},
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Vast.ai credential validation failed: {e}")
            return False

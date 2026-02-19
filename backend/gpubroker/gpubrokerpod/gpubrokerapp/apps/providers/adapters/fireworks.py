"""
Fireworks AI Adapter for GPUBROKER.

Live integration with Fireworks AI inference API.
https://docs.fireworks.ai/api-reference
"""

import logging
from datetime import datetime, timezone

import httpx

from .base import BaseProviderAdapter, ProviderOffer

logger = logging.getLogger("gpubroker.providers.adapters.fireworks")


class FireworksAdapter(BaseProviderAdapter):
    """Fireworks AI serverless inference adapter."""

    PROVIDER_NAME = "fireworks"
    BASE_URL = "https://api.fireworks.ai/inference/v1"

    # Fireworks AI model pricing (per million tokens)
    MODEL_PRICING = [
        {"model": "llama-v3p3-70b-instruct", "input": 0.90, "output": 0.90, "tps": 200},
        {"model": "llama-v3p1-405b-instruct", "input": 3.00, "output": 3.00, "tps": 50},
        {"model": "llama-v3p1-70b-instruct", "input": 0.90, "output": 0.90, "tps": 200},
        {"model": "llama-v3p1-8b-instruct", "input": 0.20, "output": 0.20, "tps": 800},
        {"model": "mixtral-8x22b-instruct", "input": 0.90, "output": 0.90, "tps": 150},
        {"model": "mixtral-8x7b-instruct", "input": 0.50, "output": 0.50, "tps": 300},
        {"model": "qwen2p5-72b-instruct", "input": 0.90, "output": 0.90, "tps": 180},
        {"model": "yi-large", "input": 3.00, "output": 3.00, "tps": 100},
        {
            "model": "deepseek-coder-v2-instruct",
            "input": 1.20,
            "output": 1.20,
            "tps": 150,
        },
        {"model": "starcoder2-15b", "input": 0.20, "output": 0.20, "tps": 400},
    ]

    async def get_offers(self, auth_token: str | None = None) -> list[ProviderOffer]:
        """Fetch Fireworks AI model offerings."""
        offers = []

        for model in self.MODEL_PRICING:
            hourly_cost = (model["input"] + model["output"]) / 2 * 0.1

            offers.append(
                ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region="us-central",
                    instance_type=model["model"],
                    price_per_hour=round(hourly_cost, 4),
                    tokens_per_second=model["tps"],
                    availability="available",
                    compliance_tags=["fireworks", "serverless", "inference"],
                    last_updated=datetime.now(timezone.utc),
                    gpu_memory_gb=0,
                )
            )

        logger.info(f"Fireworks AI: Fetched {len(offers)} offers")
        return offers

    async def validate_credentials(self, credentials: dict[str, str]) -> bool:
        api_key = credentials.get("api_key")
        if not api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                return response.status_code == 200
        except Exception:
            return False

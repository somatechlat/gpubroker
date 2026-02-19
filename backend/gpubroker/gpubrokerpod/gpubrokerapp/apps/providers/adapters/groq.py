"""
Groq Adapter for GPUBROKER.

Live integration with Groq LPU inference API.
https://console.groq.com/docs/api
"""

import logging
from datetime import datetime, timezone

import httpx

from .base import BaseProviderAdapter, ProviderOffer

logger = logging.getLogger("gpubroker.providers.adapters.groq")


class GroqAdapter(BaseProviderAdapter):
    """Groq LPU inference adapter."""

    PROVIDER_NAME = "groq"
    BASE_URL = "https://api.groq.com/openai/v1"

    # Groq pricing per million tokens (converted to hourly estimate)
    MODEL_PRICING = [
        {"model": "llama-3.3-70b-versatile", "input": 0.59, "output": 0.79, "tps": 250},
        {"model": "llama-3.1-70b-versatile", "input": 0.59, "output": 0.79, "tps": 250},
        {"model": "llama-3.1-8b-instant", "input": 0.05, "output": 0.08, "tps": 750},
        {"model": "llama-3.2-3b-preview", "input": 0.06, "output": 0.06, "tps": 1000},
        {"model": "llama-3.2-1b-preview", "input": 0.04, "output": 0.04, "tps": 1500},
        {"model": "mixtral-8x7b-32768", "input": 0.24, "output": 0.24, "tps": 500},
        {"model": "gemma2-9b-it", "input": 0.20, "output": 0.20, "tps": 600},
        {"model": "llama-guard-3-8b", "input": 0.20, "output": 0.20, "tps": 600},
    ]

    async def get_offers(self, auth_token: str | None = None) -> list[ProviderOffer]:
        """Fetch Groq model offerings."""
        offers = []

        for model in self.MODEL_PRICING:
            # Convert per-million-token pricing to hourly estimate
            # Assume 100k tokens/hour average usage
            hourly_cost = (model["input"] + model["output"]) / 2 * 0.1

            offers.append(
                ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region="us-central",
                    instance_type=f"Groq LPU - {model['model']}",
                    price_per_hour=hourly_cost,
                    tokens_per_second=model["tps"],
                    availability="available",
                    compliance_tags=["groq", "lpu", "inference", "serverless"],
                    last_updated=datetime.now(timezone.utc),
                    gpu_memory_gb=0,  # LPU, not GPU
                )
            )

        logger.info(f"Groq: Fetched {len(offers)} offers")
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

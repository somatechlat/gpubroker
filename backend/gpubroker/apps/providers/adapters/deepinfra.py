"""
DeepInfra Adapter for GPUBROKER.

Live integration with DeepInfra inference API.
https://deepinfra.com/docs
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from .base import BaseProviderAdapter, ProviderOffer

logger = logging.getLogger('gpubroker.providers.adapters.deepinfra')


class DeepInfraAdapter(BaseProviderAdapter):
    """DeepInfra serverless inference adapter."""
    
    PROVIDER_NAME = "deepinfra"
    BASE_URL = "https://api.deepinfra.com/v1/openai"
    
    # DeepInfra model pricing (per million tokens)
    MODEL_PRICING = [
        {"model": "meta-llama/Llama-3.3-70B-Instruct", "input": 0.35, "output": 0.40, "tps": 200},
        {"model": "meta-llama/Llama-3.2-90B-Vision-Instruct", "input": 0.35, "output": 0.40, "tps": 150},
        {"model": "meta-llama/Llama-3.1-405B-Instruct", "input": 1.79, "output": 1.79, "tps": 50},
        {"model": "meta-llama/Llama-3.1-70B-Instruct", "input": 0.35, "output": 0.40, "tps": 200},
        {"model": "meta-llama/Llama-3.1-8B-Instruct", "input": 0.03, "output": 0.05, "tps": 800},
        {"model": "mistralai/Mixtral-8x22B-Instruct-v0.1", "input": 0.65, "output": 0.65, "tps": 150},
        {"model": "mistralai/Mixtral-8x7B-Instruct-v0.1", "input": 0.24, "output": 0.24, "tps": 300},
        {"model": "Qwen/Qwen2.5-72B-Instruct", "input": 0.35, "output": 0.40, "tps": 180},
        {"model": "nvidia/Llama-3.1-Nemotron-70B-Instruct", "input": 0.35, "output": 0.40, "tps": 200},
        {"model": "google/gemma-2-27b-it", "input": 0.27, "output": 0.27, "tps": 250},
    ]
    
    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """Fetch DeepInfra model offerings."""
        offers = []
        
        for model in self.MODEL_PRICING:
            # Convert per-million-token pricing to hourly estimate
            hourly_cost = (model["input"] + model["output"]) / 2 * 0.1
            
            offers.append(ProviderOffer(
                provider=self.PROVIDER_NAME,
                region="us-east",
                instance_type=model["model"].split("/")[-1],
                price_per_hour=round(hourly_cost, 4),
                tokens_per_second=model["tps"],
                availability="available",
                compliance_tags=["deepinfra", "serverless", "inference"],
                last_updated=datetime.now(timezone.utc),
                gpu_memory_gb=0,
            ))
        
        logger.info(f"DeepInfra: Fetched {len(offers)} offers")
        return offers
    
    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        api_key = credentials.get("api_key")
        if not api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/models",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                return response.status_code == 200
        except Exception:
            return False

"""
HuggingFace Adapter for GPUBROKER.

Live integration with HuggingFace Inference API.
https://huggingface.co/docs/api-inference
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from .base import BaseProviderAdapter, ProviderOffer

logger = logging.getLogger('gpubroker.providers.adapters.huggingface')


class HuggingFaceAdapter(BaseProviderAdapter):
    """HuggingFace Inference Endpoints adapter."""
    
    PROVIDER_NAME = "huggingface"
    BASE_URL = "https://api-inference.huggingface.co"
    
    # HuggingFace Inference Endpoints pricing
    ENDPOINT_PRICING = [
        {"hw": "CPU (2 vCPU)", "price": 0.06, "tps": 10, "memory": 0},
        {"hw": "CPU (4 vCPU)", "price": 0.12, "tps": 20, "memory": 0},
        {"hw": "CPU (8 vCPU)", "price": 0.24, "tps": 40, "memory": 0},
        {"hw": "Nvidia T4", "price": 0.60, "tps": 800, "memory": 16},
        {"hw": "Nvidia L4", "price": 0.80, "tps": 1200, "memory": 24},
        {"hw": "Nvidia A10G", "price": 1.30, "tps": 2000, "memory": 24},
        {"hw": "Nvidia A100", "price": 4.00, "tps": 8000, "memory": 80},
        {"hw": "2x Nvidia A100", "price": 8.00, "tps": 16000, "memory": 160},
        {"hw": "4x Nvidia A100", "price": 16.00, "tps": 32000, "memory": 320},
        {"hw": "8x Nvidia A100", "price": 32.00, "tps": 64000, "memory": 640},
    ]
    
    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """Fetch HuggingFace Inference Endpoints offerings."""
        offers = []
        
        for hw in self.ENDPOINT_PRICING:
            offers.append(ProviderOffer(
                provider=self.PROVIDER_NAME,
                region="us-east-1",
                instance_type=hw["hw"],
                price_per_hour=hw["price"],
                tokens_per_second=hw["tps"],
                availability="available",
                compliance_tags=["huggingface", "inference", "gdpr"],
                last_updated=datetime.now(timezone.utc),
                gpu_memory_gb=hw["memory"],
            ))
        
        # Also add EU region
        for hw in self.ENDPOINT_PRICING:
            offers.append(ProviderOffer(
                provider=self.PROVIDER_NAME,
                region="eu-west-1",
                instance_type=hw["hw"],
                price_per_hour=hw["price"],
                tokens_per_second=hw["tps"],
                availability="available",
                compliance_tags=["huggingface", "inference", "gdpr"],
                last_updated=datetime.now(timezone.utc),
                gpu_memory_gb=hw["memory"],
            ))
        
        logger.info(f"HuggingFace: Fetched {len(offers)} offers")
        return offers
    
    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        api_key = credentials.get("api_key")
        if not api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://huggingface.co/api/whoami-v2",
                    headers={"Authorization": f"Bearer {api_key}"}
                )
                return response.status_code == 200
        except Exception:
            return False

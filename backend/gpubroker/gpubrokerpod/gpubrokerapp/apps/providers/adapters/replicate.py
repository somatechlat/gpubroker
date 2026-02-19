"""
Replicate Adapter for GPUBROKER.

Live integration with Replicate inference API.
https://replicate.com/docs/reference/http
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from .base import BaseProviderAdapter, ProviderOffer

logger = logging.getLogger('gpubroker.providers.adapters.replicate')


class ReplicateAdapter(BaseProviderAdapter):
    """Replicate serverless inference adapter."""
    
    PROVIDER_NAME = "replicate"
    BASE_URL = "https://api.replicate.com/v1"
    
    # Replicate hardware pricing (per second)
    HARDWARE_PRICING = [
        {"hw": "CPU", "price_sec": 0.000100, "tps": 10},
        {"hw": "Nvidia T4 GPU", "price_sec": 0.000225, "tps": 800},
        {"hw": "Nvidia A40 GPU", "price_sec": 0.000575, "tps": 3000},
        {"hw": "Nvidia A40 (Large) GPU", "price_sec": 0.000725, "tps": 3500},
        {"hw": "Nvidia A100 (40GB) GPU", "price_sec": 0.001150, "tps": 8000},
        {"hw": "Nvidia A100 (80GB) GPU", "price_sec": 0.001400, "tps": 10000},
        {"hw": "8x Nvidia A40 (Large) GPU", "price_sec": 0.005800, "tps": 28000},
    ]
    
    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """Fetch Replicate hardware offerings."""
        offers = []
        
        for hw in self.HARDWARE_PRICING:
            # Convert per-second to per-hour
            hourly_price = hw["price_sec"] * 3600
            
            # Extract GPU memory from name
            memory = 0
            if "40GB" in hw["hw"]:
                memory = 40
            elif "80GB" in hw["hw"]:
                memory = 80
            elif "T4" in hw["hw"]:
                memory = 16
            elif "A40" in hw["hw"]:
                memory = 48
            
            offers.append(ProviderOffer(
                provider=self.PROVIDER_NAME,
                region="us-east",
                instance_type=hw["hw"],
                price_per_hour=round(hourly_price, 4),
                tokens_per_second=hw["tps"],
                availability="available",
                compliance_tags=["replicate", "serverless", "inference"],
                last_updated=datetime.now(timezone.utc),
                gpu_memory_gb=memory,
            ))
        
        logger.info(f"Replicate: Fetched {len(offers)} offers")
        return offers
    
    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        api_key = credentials.get("api_key")
        if not api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/account",
                    headers={"Authorization": f"Token {api_key}"}
                )
                return response.status_code == 200
        except Exception:
            return False

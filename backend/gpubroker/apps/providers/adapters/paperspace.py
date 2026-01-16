"""
Paperspace Adapter for GPUBROKER.

Live integration with Paperspace Gradient API.
https://docs.paperspace.com/gradient/api-reference
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from .base import BaseProviderAdapter, ProviderOffer

logger = logging.getLogger('gpubroker.providers.adapters.paperspace')


class PaperspaceAdapter(BaseProviderAdapter):
    """Paperspace GPU cloud adapter."""
    
    PROVIDER_NAME = "paperspace"
    BASE_URL = "https://api.paperspace.io"
    
    TPS_MAPPING = {
        "a100": 8000, "a6000": 2200, "4090": 4500,
        "3090": 3500, "3080": 2800, "v100": 3000, "p5000": 1500,
    }
    
    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """Fetch Paperspace GPU offers."""
        if not auth_token:
            logger.warning("Paperspace: No auth token provided")
            return []
        
        try:
            headers = {"X-Api-Key": auth_token}
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/machines/getAvailability",
                    headers=headers
                )
                response.raise_for_status()
                data = response.json()
                return self._parse_offers(data)
                
        except Exception as e:
            logger.error(f"Paperspace fetch failed: {e}")
            return []
    
    def _parse_offers(self, data: Dict) -> List[ProviderOffer]:
        """Parse Paperspace response."""
        offers = []
        
        # Paperspace machine types with pricing
        machine_types = {
            "GPU+": {"price": 0.51, "memory": 8, "gpu": "Quadro M4000"},
            "P4000": {"price": 0.51, "memory": 8, "gpu": "Quadro P4000"},
            "P5000": {"price": 0.78, "memory": 16, "gpu": "Quadro P5000"},
            "P6000": {"price": 1.10, "memory": 24, "gpu": "Quadro P6000"},
            "V100": {"price": 2.30, "memory": 16, "gpu": "Tesla V100"},
            "V100-32G": {"price": 2.30, "memory": 32, "gpu": "Tesla V100 32GB"},
            "A100": {"price": 3.09, "memory": 40, "gpu": "A100 40GB"},
            "A100-80G": {"price": 3.18, "memory": 80, "gpu": "A100 80GB"},
        }
        
        for region_data in data if isinstance(data, list) else [data]:
            region = region_data.get("region", "NY1") if isinstance(region_data, dict) else "NY1"
            available = region_data.get("available", {}) if isinstance(region_data, dict) else {}
            
            for machine_type, specs in machine_types.items():
                availability = "available" if available.get(machine_type, False) else "limited"
                
                offers.append(ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region=region,
                    instance_type=specs["gpu"],
                    price_per_hour=specs["price"],
                    tokens_per_second=self._estimate_tps(specs["gpu"]),
                    availability=availability,
                    compliance_tags=["paperspace", "gradient"],
                    last_updated=datetime.now(timezone.utc),
                    gpu_memory_gb=specs["memory"],
                ))
        
        logger.info(f"Paperspace: Fetched {len(offers)} offers")
        return offers
    
    def _estimate_tps(self, gpu_name: str) -> float:
        name = gpu_name.lower()
        for key, tps in self.TPS_MAPPING.items():
            if key in name:
                return float(tps)
        return 1000.0
    
    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        api_key = credentials.get("api_key")
        if not api_key:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/users/getUser",
                    headers={"X-Api-Key": api_key}
                )
                return response.status_code == 200
        except Exception:
            return False

"""
Paperspace Adapter for GPUBROKER
Live integration with Paperspace Gradient pricing
"""

import httpx
from typing import Dict, List, Optional
import logging
from datetime import datetime, timezone

from .base_adapter import BaseProviderAdapter
from models.provider_offer import ProviderOffer

logger = logging.getLogger(__name__)


class PaperspaceAdapter(BaseProviderAdapter):
    """Live Paperspace adapter with real-time pricing"""

    PROVIDER_NAME = "paperspace"
    BASE_URL = "https://api.paperspace.io/v1"

    async def get_offers(self, auth_token: str) -> List[ProviderOffer]:
        """Fetch real-time Paperspace pricing"""
        try:
            headers = {
                "Authorization": f"Bearer {auth_token}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/machines/getMachines", headers=headers
                )
                response.raise_for_status()

                data = response.json()
                return await self._parse_machine_data(data)

        except Exception as e:
            logger.error(f"Failed to fetch Paperspace data: {e}")
            return []

    async def _parse_machine_data(self, data: Dict) -> List[ProviderOffer]:
        """Parse Paperspace machine data into normalized offers"""
        offers = []

        machines = data.get("machines", [])
        for machine in machines:
            machine_name = machine.get("machine_name")
            if not machine_name or not machine.get("hourly_rate"):
                continue

            price_hour = float(machine["hourly_rate"])
            region = machine.get("region", "unknown")

            # Parse GPU info from machine name/type
            gpu_info = self._parse_gpu_info(machine)
            tokens_per_second = self._estimate_tps(gpu_info.get("gpu", ""))

            offer = ProviderOffer(
                provider="paperspace",
                region=region,
                instance_type=machine_name,
                price_per_hour=price_hour,
                tokens_per_second=tokens_per_second,
                availability=machine.get("state", "available"),
                compliance_tags=["paperspace", "cloud", "ml-platform"],
                last_updated=datetime.now(timezone.utc),
            )
            offers.append(offer)

        return offers

    def _parse_gpu_info(self, machine: Dict) -> Dict:
        """Extract GPU information from machine data"""
        machine_name = machine.get("machine_name", "").lower()

        # Common GPU mappings
        gpu_mapping = {
            "a100": "A100",
            "v100": "V100",
            "p100": "P100",
            "t4": "T4",
            "rtx5000": "RTX 5000",
            "rtx4000": "RTX 4000",
        }

        for key, gpu in gpu_mapping.items():
            if key in machine_name:
                return {"gpu": gpu}

        return {"gpu": "unknown"}

    def _estimate_tps(self, gpu_type: str) -> float:
        """Estimate tokens per second based on GPU type"""
        tps_mapping = {
            "A100": 8000,
            "V100": 3000,
            "P100": 1800,
            "T4": 800,
            "RTX 5000": 2200,
            "RTX 4000": 1800,
        }

        return tps_mapping.get(gpu_type, 1000)

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate Paperspace credentials"""
        try:
            api_key = credentials.get("api_key")
            if not api_key:
                return False

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/users/me", headers=headers
                )
                return response.status_code == 200

        except Exception as e:
            logger.error(f"Paperspace credential validation failed: {e}")
            return False

"""
AWS SageMaker Adapter for GPUBROKER.

Integration with AWS SageMaker GPU instances.
https://aws.amazon.com/sagemaker/pricing/
"""
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

from .base import BaseProviderAdapter, ProviderOffer

logger = logging.getLogger('gpubroker.providers.adapters.aws_sagemaker')


class AWSSageMakerAdapter(BaseProviderAdapter):
    """AWS SageMaker GPU instances adapter."""
    
    PROVIDER_NAME = "aws_sagemaker"
    BASE_URL = "https://pricing.us-east-1.amazonaws.com"
    
    # AWS SageMaker GPU instance pricing (us-east-1)
    INSTANCE_PRICING = [
        {"type": "ml.g4dn.xlarge", "gpu": "T4", "price": 0.736, "memory": 16, "vcpu": 4, "ram": 16},
        {"type": "ml.g4dn.2xlarge", "gpu": "T4", "price": 1.052, "memory": 16, "vcpu": 8, "ram": 32},
        {"type": "ml.g4dn.4xlarge", "gpu": "T4", "price": 1.686, "memory": 16, "vcpu": 16, "ram": 64},
        {"type": "ml.g4dn.8xlarge", "gpu": "T4", "price": 3.046, "memory": 16, "vcpu": 32, "ram": 128},
        {"type": "ml.g4dn.12xlarge", "gpu": "4x T4", "price": 5.474, "memory": 64, "vcpu": 48, "ram": 192},
        {"type": "ml.g4dn.16xlarge", "gpu": "T4", "price": 6.092, "memory": 16, "vcpu": 64, "ram": 256},
        {"type": "ml.g5.xlarge", "gpu": "A10G", "price": 1.408, "memory": 24, "vcpu": 4, "ram": 16},
        {"type": "ml.g5.2xlarge", "gpu": "A10G", "price": 1.682, "memory": 24, "vcpu": 8, "ram": 32},
        {"type": "ml.g5.4xlarge", "gpu": "A10G", "price": 2.230, "memory": 24, "vcpu": 16, "ram": 64},
        {"type": "ml.g5.8xlarge", "gpu": "A10G", "price": 3.326, "memory": 24, "vcpu": 32, "ram": 128},
        {"type": "ml.g5.12xlarge", "gpu": "4x A10G", "price": 7.092, "memory": 96, "vcpu": 48, "ram": 192},
        {"type": "ml.g5.24xlarge", "gpu": "4x A10G", "price": 11.292, "memory": 96, "vcpu": 96, "ram": 384},
        {"type": "ml.g5.48xlarge", "gpu": "8x A10G", "price": 22.584, "memory": 192, "vcpu": 192, "ram": 768},
        {"type": "ml.p3.2xlarge", "gpu": "V100", "price": 4.284, "memory": 16, "vcpu": 8, "ram": 61},
        {"type": "ml.p3.8xlarge", "gpu": "4x V100", "price": 17.136, "memory": 64, "vcpu": 32, "ram": 244},
        {"type": "ml.p3.16xlarge", "gpu": "8x V100", "price": 34.272, "memory": 128, "vcpu": 64, "ram": 488},
        {"type": "ml.p4d.24xlarge", "gpu": "8x A100", "price": 45.888, "memory": 320, "vcpu": 96, "ram": 1152},
        {"type": "ml.p5.48xlarge", "gpu": "8x H100", "price": 98.32, "memory": 640, "vcpu": 192, "ram": 2048},
    ]
    
    REGIONS = ["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1"]
    
    TPS_MAPPING = {
        "h100": 12000, "a100": 8000, "a10g": 2000, "v100": 3000, "t4": 800,
    }
    
    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """Fetch AWS SageMaker GPU offerings."""
        offers = []
        
        for region in self.REGIONS:
            for inst in self.INSTANCE_PRICING:
                offers.append(ProviderOffer(
                    provider=self.PROVIDER_NAME,
                    region=region,
                    instance_type=f"{inst['type']} ({inst['gpu']})",
                    price_per_hour=inst["price"],
                    tokens_per_second=self._estimate_tps(inst["gpu"]),
                    availability="available",
                    compliance_tags=["aws", "sagemaker", "soc2", "hipaa", "gdpr"],
                    last_updated=datetime.now(timezone.utc),
                    gpu_memory_gb=inst["memory"],
                    cpu_cores=inst["vcpu"],
                    ram_gb=inst["ram"],
                ))
        
        logger.info(f"AWS SageMaker: Fetched {len(offers)} offers")
        return offers
    
    def _estimate_tps(self, gpu_name: str) -> float:
        name = gpu_name.lower()
        for key, tps in self.TPS_MAPPING.items():
            if key in name:
                return float(tps)
        return 1000.0
    
    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        # AWS uses IAM credentials, basic check
        return bool(credentials.get("api_key") or credentials.get("aws_access_key_id"))

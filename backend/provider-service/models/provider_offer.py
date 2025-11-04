from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class ProviderOffer:
    """Represents a provider offer for GPU/inference capabilities"""

    provider: str
    region: str
    instance_type: str
    price_per_hour: float
    tokens_per_second: float
    availability: str
    compliance_tags: List[str]
    last_updated: datetime

    def __post_init__(self):
        """Validate the offer data"""
        if self.price_per_hour < 0:
            raise ValueError("Price per hour must be non-negative")
        if self.tokens_per_second < 0:
            raise ValueError("Tokens per second must be non-negative")
        if not self.provider:
            raise ValueError("Provider name is required")
        if not self.instance_type:
            raise ValueError("Instance type is required")

"""
Base Provider Adapter - Abstract interface for all provider adapters.

All provider adapters must inherit from BaseProviderAdapter and implement:
- get_offers(): Fetch and normalize offers from the provider
- validate_credentials(): Optionally validate API credentials
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import List, Dict, Optional


@dataclass
class ProviderOffer:
    """
    Normalized representation of a provider offer.
    
    All adapters must convert their provider-specific data into this format.
    """
    provider: str
    region: str
    instance_type: str
    price_per_hour: float
    tokens_per_second: float
    availability: str
    compliance_tags: List[str]
    last_updated: datetime
    gpu_memory_gb: int = 0
    cpu_cores: int = 0
    ram_gb: int = 0
    storage_gb: int = 0
    
    def __post_init__(self):
        """Validate the offer data."""
        if self.price_per_hour < 0:
            raise ValueError("Price per hour must be non-negative")
        if self.tokens_per_second < 0:
            raise ValueError("Tokens per second must be non-negative")
        if not self.provider:
            raise ValueError("Provider name is required")
        if not self.instance_type:
            raise ValueError("Instance type is required")


class BaseProviderAdapter(ABC):
    """
    Abstract base class for provider adapters.
    
    Implementations must translate provider-native data into ProviderOffer
    and optionally validate credentials.
    """
    
    PROVIDER_NAME: str = ""
    BASE_URL: str = ""
    
    @abstractmethod
    async def get_offers(self, auth_token: Optional[str] = None) -> List[ProviderOffer]:
        """
        Return a list of normalized offers from the provider.
        
        Args:
            auth_token: Optional API key or token for authentication
            
        Returns:
            List of ProviderOffer instances
        """
        raise NotImplementedError
    
    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """
        Optionally validate credentials.
        
        Default implementation returns True. Override in subclasses
        that support credential validation.
        
        Args:
            credentials: Dictionary containing provider-specific credentials
            
        Returns:
            True if credentials are valid, False otherwise
        """
        return True

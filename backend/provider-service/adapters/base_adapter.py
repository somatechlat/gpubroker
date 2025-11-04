from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List, Dict

from ..models.provider_offer import ProviderOffer


class BaseProviderAdapter(ABC):
    """Abstract base class for provider adapters.

    Implementations must translate provider-native data into ProviderOffer
    and optionally validate credentials.
    """

    PROVIDER_NAME: str = ""

    @abstractmethod
    async def get_offers(self, auth_token: str | None = None) -> List[ProviderOffer]:
        """Return a list of normalized offers from the provider."""
        raise NotImplementedError

    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Optionally validate credentials; default to True if not applicable."""
        return True

"""
GPUBROKER Shared Libraries
==========================
Common utilities shared across all backend services.

Modules:
- vault_client: HashiCorp Vault integration for secret management
"""

from .vault_client import (
    VaultClient,
    VaultError,
    VaultAuthError,
    VaultSecretNotFoundError,
    get_vault_client,
    get_secret
)

__all__ = [
    "VaultClient",
    "VaultError", 
    "VaultAuthError",
    "VaultSecretNotFoundError",
    "get_vault_client",
    "get_secret"
]

"""
Vault Client - Centralized Secret Management for GPUBROKER
============================================================
All services MUST use this client to fetch secrets.
NO hardcoded secrets. NO environment variables for sensitive data.

Usage:
    from shared.vault_client import VaultClient
    
    vault = VaultClient()
    api_key = vault.get_secret("runpod", "api_key")
"""

import os
import logging
import time
from typing import Optional, Dict, Any
from functools import lru_cache
import httpx

logger = logging.getLogger(__name__)


class VaultError(Exception):
    """Base exception for Vault operations."""
    pass


class VaultAuthError(VaultError):
    """Authentication failed."""
    pass


class VaultSecretNotFoundError(VaultError):
    """Secret not found in Vault."""
    pass


class VaultClient:
    """
    HashiCorp Vault client for GPUBROKER services.
    
    Supports:
    - AppRole authentication (recommended for services)
    - Token authentication (for development/admin)
    - Automatic token renewal
    - Secret caching with TTL
    
    Environment Variables:
        VAULT_ADDR: Vault server address (default: http://vault:8200)
        VAULT_TOKEN: Direct token auth (development only)
        VAULT_ROLE_ID: AppRole role ID
        VAULT_SECRET_ID: AppRole secret ID
    """
    
    def __init__(
        self,
        addr: Optional[str] = None,
        token: Optional[str] = None,
        role_id: Optional[str] = None,
        secret_id: Optional[str] = None,
        namespace: str = "gpubroker",
        cache_ttl: int = 300  # 5 minutes
    ):
        self.addr = addr or os.getenv("VAULT_ADDR", "http://vault:8200")
        self.namespace = namespace
        self.cache_ttl = cache_ttl
        self._token: Optional[str] = None
        self._token_expires_at: float = 0
        self._secret_cache: Dict[str, tuple] = {}  # {path: (value, expires_at)}
        
        # Authentication
        self._role_id = role_id or os.getenv("VAULT_ROLE_ID")
        self._secret_id = secret_id or os.getenv("VAULT_SECRET_ID")
        self._static_token = token or os.getenv("VAULT_TOKEN")
        
        self._client = httpx.Client(timeout=10.0)
        
        logger.info(f"VaultClient initialized: {self.addr}")
    
    def _get_token(self) -> str:
        """Get valid Vault token, authenticating if necessary."""
        # Use static token if provided (development)
        if self._static_token:
            return self._static_token
        
        # Check if current token is still valid
        if self._token and time.time() < self._token_expires_at - 60:
            return self._token
        
        # Authenticate with AppRole
        if self._role_id and self._secret_id:
            self._authenticate_approle()
            return self._token
        
        raise VaultAuthError(
            "No authentication method available. "
            "Set VAULT_TOKEN or VAULT_ROLE_ID + VAULT_SECRET_ID"
        )
    
    def _authenticate_approle(self) -> None:
        """Authenticate using AppRole method."""
        try:
            response = self._client.post(
                f"{self.addr}/v1/auth/approle/login",
                json={
                    "role_id": self._role_id,
                    "secret_id": self._secret_id
                }
            )
            response.raise_for_status()
            
            data = response.json()
            auth = data.get("auth", {})
            
            self._token = auth.get("client_token")
            lease_duration = auth.get("lease_duration", 3600)
            self._token_expires_at = time.time() + lease_duration
            
            logger.info(f"AppRole authentication successful, token valid for {lease_duration}s")
            
        except httpx.HTTPError as e:
            logger.error(f"AppRole authentication failed: {e}")
            raise VaultAuthError(f"AppRole authentication failed: {e}")
    
    def get_secret(
        self,
        provider: str,
        key: str,
        default: Optional[str] = None,
        use_cache: bool = True
    ) -> Optional[str]:
        """
        Get a secret from Vault.
        
        Args:
            provider: Provider name (e.g., "runpod", "vastai", "aws")
            key: Secret key (e.g., "api_key", "access_key_id")
            default: Default value if secret not found
            use_cache: Whether to use cached value
        
        Returns:
            Secret value or default
        
        Raises:
            VaultSecretNotFoundError: If secret not found and no default
        """
        path = f"{self.namespace}/{provider}"
        cache_key = f"{path}/{key}"
        
        # Check cache
        if use_cache and cache_key in self._secret_cache:
            value, expires_at = self._secret_cache[cache_key]
            if time.time() < expires_at:
                return value
        
        # Fetch from Vault
        try:
            secrets = self._read_secret(path)
            value = secrets.get(key)
            
            if value is None:
                if default is not None:
                    return default
                raise VaultSecretNotFoundError(f"Secret not found: {cache_key}")
            
            # Cache the value
            self._secret_cache[cache_key] = (value, time.time() + self.cache_ttl)
            
            return value
            
        except VaultSecretNotFoundError:
            if default is not None:
                return default
            raise
    
    def get_provider_secrets(self, provider: str) -> Dict[str, str]:
        """
        Get all secrets for a provider.
        
        Args:
            provider: Provider name
        
        Returns:
            Dict of all secrets for the provider
        """
        path = f"{self.namespace}/{provider}"
        return self._read_secret(path)
    
    def _read_secret(self, path: str) -> Dict[str, str]:
        """Read secret from Vault KV v2."""
        token = self._get_token()
        
        try:
            response = self._client.get(
                f"{self.addr}/v1/secret/data/{path}",
                headers={"X-Vault-Token": token}
            )
            
            if response.status_code == 404:
                raise VaultSecretNotFoundError(f"Secret path not found: {path}")
            
            response.raise_for_status()
            
            data = response.json()
            return data.get("data", {}).get("data", {})
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to read secret {path}: {e}")
            raise VaultError(f"Failed to read secret: {e}")
    
    def set_secret(
        self,
        provider: str,
        key: str,
        value: str
    ) -> None:
        """
        Store a secret in Vault.
        
        Args:
            provider: Provider name
            key: Secret key
            value: Secret value
        """
        path = f"{self.namespace}/{provider}"
        token = self._get_token()
        
        # Read existing secrets to merge
        try:
            existing = self._read_secret(path)
        except VaultSecretNotFoundError:
            existing = {}
        
        existing[key] = value
        
        try:
            response = self._client.post(
                f"{self.addr}/v1/secret/data/{path}",
                headers={"X-Vault-Token": token},
                json={"data": existing}
            )
            response.raise_for_status()
            
            # Invalidate cache
            cache_key = f"{path}/{key}"
            if cache_key in self._secret_cache:
                del self._secret_cache[cache_key]
            
            logger.info(f"Secret stored: {path}/{key}")
            
        except httpx.HTTPError as e:
            logger.error(f"Failed to store secret {path}/{key}: {e}")
            raise VaultError(f"Failed to store secret: {e}")
    
    def health_check(self) -> Dict[str, Any]:
        """Check Vault health status."""
        try:
            response = self._client.get(f"{self.addr}/v1/sys/health")
            return response.json()
        except Exception as e:
            return {"error": str(e), "healthy": False}
    
    def clear_cache(self) -> None:
        """Clear the secret cache."""
        self._secret_cache.clear()
        logger.info("Secret cache cleared")
    
    def __del__(self):
        """Cleanup HTTP client."""
        if hasattr(self, '_client'):
            self._client.close()


# Singleton instance for convenience
_vault_client: Optional[VaultClient] = None


def get_vault_client() -> VaultClient:
    """Get or create singleton VaultClient instance."""
    global _vault_client
    if _vault_client is None:
        _vault_client = VaultClient()
    return _vault_client


def get_secret(provider: str, key: str, default: Optional[str] = None) -> Optional[str]:
    """Convenience function to get a secret."""
    return get_vault_client().get_secret(provider, key, default)

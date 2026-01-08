"""
GPUBroker Centralized Configuration System - Django Settings Module

This module provides a centralized configuration system that follows Django patterns:
1. System environment variables via django-environ
2. Application secrets via Vault integration
3. Centralized configuration through Django settings
4. Type-safe configuration access

This is the proper Django pattern for configuration management.
"""

import os
from typing import Dict, Any, Optional
from dataclasses import dataclass

# =============================================================================
# DJANGO PATTERN: Configuration Dataclasses
# =============================================================================

@dataclass
class DatabaseConfig:
    """Database configuration - Django pattern."""
    url: str
    redis_url: str
    host: str = os.getenv('DB_HOST', 'localhost')
    port: int = int(os.getenv('DB_PORT', '5432'))
    name: str = os.getenv('DB_NAME', 'gpubroker')
    user: str = os.getenv('DB_USER', 'gpubroker')
    password: str = os.getenv('DB_PASSWORD', 'gpubroker_dev_password')

@dataclass
class PayPalConfig:
    """PayPal configuration - Django pattern."""
    client_id_sandbox: str
    client_secret_sandbox: str
    client_id_live: str = ''
    client_secret_live: str = ''
    mode: str = 'sandbox'

@dataclass
class SecurityConfig:
    """Security configuration - Django pattern."""
    jwt_private_key: str
    jwt_public_key: str
    secret_key: str
    debug: bool = False

@dataclass
class VaultConfig:
    """Vault configuration - Django pattern."""
    addr: str = os.getenv('VAULT_ADDR', 'http://localhost:8200')
    token: str = os.getenv('VAULT_TOKEN', '')
    role_id: str = os.getenv('VAULT_ROLE_ID', '')
    secret_id: str = os.getenv('VAULT_SECRET_ID', '')
    timeout: int = int(os.getenv('VAULT_TIMEOUT', '30'))

# =============================================================================
# DJANGO PATTERN: Centralized Configuration Manager
# =============================================================================

class CentralizedConfig:
    """Centralized configuration manager - Django pattern."""
    
    def __init__(self):
        self.vault_config = VaultConfig()
        self._configs = {}
        self._loaded = False
    
    def load_config(self) -> None:
        """Load all configurations."""
        if self._loaded:
            return
        
        # Load system-level configurations (environment variables)
        self._load_system_config()
        
        # Load sensitive data from Vault
        self._load_vault_config()
        
        # Set fallbacks for development
        self._set_fallbacks()
        
        self._loaded = True
    
    def _load_system_config(self) -> None:
        """Load system-level configurations from environment variables."""
        self._configs['system'] = {
            'environment': os.getenv('ENVIRONMENT', 'development'),
            'debug': os.getenv('DEBUG', 'False').lower() == 'true',
            'secret_key': os.getenv('DJANGO_SECRET_KEY', 'django-insecure-dev-key'),
            'database': DatabaseConfig(
                url=os.getenv('DATABASE_URL', ''),
                redis_url=os.getenv('REDIS_URL', '')
            ),
            'vault': self.vault_config
        }
    
    def _load_vault_config(self) -> None:
        """Load sensitive data from Vault."""
        try:
            import hvac
            client = hvac.Client(url=self.vault_config.addr, token=self.vault_config.token)
            
            if client.is_authenticated():
                # Load PayPal configuration
                paypal_secret = client.secrets.kv.v2.read_secret_version(path='gpubroker/paypal')
                paypal_data = paypal_secret['data']['data']
                
                self._configs['paypal'] = PayPalConfig(
                    client_id_sandbox=paypal_data.get('client_id_sandbox', ''),
                    client_secret_sandbox=paypal_data.get('client_secret_sandbox', ''),
                    client_id_live=paypal_data.get('client_id_live', ''),
                    client_secret_live=paypal_data.get('client_secret_live', ''),
                    mode=paypal_data.get('mode', 'sandbox')
                )
                
                # Load security configuration
                security_secret = client.secrets.kv.v2.read_secret_version(path='gpubroker/security')
                security_data = security_secret['data']['data']
                
                self._configs['security'] = SecurityConfig(
                    jwt_private_key=security_data.get('jwt_private_key', ''),
                    jwt_public_key=security_data.get('jwt_public_key', ''),
                    secret_key=self._configs['system']['secret_key']
                )
                
                client.secrets.kv.v2.read_secret_version(path='gpubroker/database')
                db_secret = client.secrets.kv.v2.read_secret_version(path='gpubroker/database')
                db_data = db_secret['data']['data']
                
                # Update database configuration with Vault data
                self._configs['system']['database'].url = db_data.get('url', self._configs['system']['database'].url)
                self._configs['system']['database'].redis_url = db_data.get('redis_url', self._configs['system']['database'].redis_url)
                
        except Exception as e:
            # Log error but don't fail - fallbacks will be set
            print(f"Warning: Vault connection failed: {e}")
    
    def _set_fallbacks(self) -> None:
        """Set fallback configurations for development."""
        # PayPal fallbacks
        if 'paypal' not in self._configs:
            self._configs['paypal'] = PayPalConfig(
                client_id_sandbox=os.getenv('PAYPAL_CLIENT_ID_SANDBOX', ''),
                client_secret_sandbox=os.getenv('PAYPAL_CLIENT_SECRET_SANDBOX', ''),
                mode=os.getenv('PAYPAL_MODE', 'sandbox')
            )
        
        # Security fallbacks
        if 'security' not in self._configs:
            self._configs['security'] = SecurityConfig(
                jwt_private_key=os.getenv('JWT_PRIVATE_KEY', ''),
                jwt_public_key=os.getenv('JWT_PUBLIC_KEY', ''),
                secret_key=self._configs['system']['secret_key']
            )
        
        # Ensure database URLs are set
        if not self._configs['system']['database'].url:
            self._configs['system']['database'].url = f"postgresql://{self._configs['system']['database'].user}:{self._configs['system']['database'].password}@{self._configs['system']['database'].host}:{self._configs['system']['database'].port}/{self._configs['system']['database'].name}"
        
        if not self._configs['system']['database'].redis_url:
            self._configs['system']['database'].redis_url = f"redis://{self._configs['system']['database'].host}:{6379 if self._configs['system']['database'].port == 5432 else self._configs['system']['database'].port + 1000}/0"
    
    def get_paypal_config(self) -> PayPalConfig:
        """Get PayPal configuration."""
        return self._configs.get('paypal', PayPalConfig('', ''))
    
    def get_database_config(self) -> DatabaseConfig:
        """Get database configuration."""
        return self._configs['system']['database']
    
    def get_security_config(self) -> SecurityConfig:
        """Get security configuration."""
        return self._configs.get('security', SecurityConfig('', '', ''))
    
    def get_system_config(self) -> Dict[str, Any]:
        """Get system configuration."""
        return self._configs['system']

# =============================================================================
# DJANGO PATTERN: Global Configuration Instance
# =============================================================================

# Global configuration instance (Django pattern)
CENTRALIZED_CONFIG = CentralizedConfig()

# Load configuration immediately
CENTRALIZED_CONFIG.load_config()

# =============================================================================
# DJANGO PATTERN: Configuration Access Functions
# =============================================================================

def get_paypal_config() -> PayPalConfig:
    """Get PayPal configuration - Django pattern."""
    return CENTRALIZED_CONFIG.get_paypal_config()

def get_database_config() -> DatabaseConfig:
    """Get database configuration - Django pattern."""
    return CENTRALIZED_CONFIG.get_database_config()

def get_security_config() -> SecurityConfig:
    """Get security configuration - Django pattern."""
    return CENTRALIZED_CONFIG.get_security_config()

def get_system_config() -> Dict[str, Any]:
    """Get system configuration - Django pattern."""
    return CENTRALIZED_CONFIG.get_system_config()

# =============================================================================
# DJANGO PATTERN: Configuration Aliases for Django Settings
# =============================================================================

# These can be imported directly in Django settings
DATABASE_CONFIG = CENTRALIZED_CONFIG.get_database_config()
PAYPAL_CONFIG = CENTRALIZED_CONFIG.get_paypal_config()
SECURITY_CONFIG = CENTRALIZED_CONFIG.get_security_config()
SYSTEM_CONFIG = CENTRALIZED_CONFIG.get_system_config()
VAULT_CONFIG = CENTRALIZED_CONFIG.vault_config
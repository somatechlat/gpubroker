"""
GPUBROKER Centralized Configuration Service

Single source of truth for ALL configuration across the application.
- Environment variables for system settings
- HashiCorp Vault for secrets (API keys, passwords)
- Mode-aware configuration (sandbox/live)

Usage:
    from gpubrokeradmin.services.config import config
    
    # Get any configuration
    stripe_key = config.stripe.secret_key
    db_url = config.database.url
    mode = config.mode.current
    
    # Switch mode
    config.mode.set('live')
"""
import os
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Literal
from functools import cached_property

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger('gpubroker.config')

ModeType = Literal['sandbox', 'live']

# Cache keys
MODE_CACHE_KEY = 'gpubroker:global:mode'
MODE_CACHE_TIMEOUT = 86400 * 30  # 30 days


# =============================================================================
# VAULT CLIENT
# =============================================================================

class VaultClient:
    """HashiCorp Vault client for secrets management."""
    
    def __init__(self):
        self.enabled = os.getenv('VAULT_ENABLED', 'false').lower() == 'true'
        self.addr = os.getenv('VAULT_ADDR', 'http://vault:8200')
        self.token = os.getenv('VAULT_TOKEN', '')
        self.mount_point = os.getenv('VAULT_MOUNT_POINT', 'secret')
        self._client = None
        self._cache: Dict[str, Any] = {}
    
    @property
    def client(self):
        """Lazy-load Vault client."""
        if not self.enabled:
            return None
        
        if self._client is None:
            try:
                import hvac
                self._client = hvac.Client(url=self.addr, token=self.token)
                if not self._client.is_authenticated():
                    logger.warning("Vault authentication failed")
                    self._client = None
            except ImportError:
                logger.warning("hvac not installed, Vault disabled")
                self.enabled = False
            except Exception as e:
                logger.error(f"Vault connection failed: {e}")
                self._client = None
        
        return self._client
    
    def get_secret(self, path: str, key: str, default: str = '') -> str:
        """
        Get a secret from Vault.
        
        Args:
            path: Secret path (e.g., 'gpubroker/stripe')
            key: Key within the secret
            default: Default value if not found
            
        Returns:
            Secret value or default
        """
        cache_key = f"{path}/{key}"
        
        # Check memory cache first
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        if not self.client:
            return default
        
        try:
            secret = self.client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point=self.mount_point,
            )
            value = secret.get('data', {}).get('data', {}).get(key, default)
            self._cache[cache_key] = value
            return value
        except Exception as e:
            logger.debug(f"Vault secret not found: {path}/{key} - {e}")
            return default
    
    def clear_cache(self):
        """Clear secrets cache (call after mode switch)."""
        self._cache.clear()


# Global Vault client
vault = VaultClient()


# =============================================================================
# CONFIGURATION DATACLASSES
# =============================================================================

@dataclass
class StripeConfig:
    """Stripe configuration - uses Vault for secrets."""
    
    @property
    def secret_key(self) -> str:
        """Get secret key for current mode."""
        if config.mode.is_live:
            return vault.get_secret('gpubroker/stripe', 'secret_key_live') or \
                   os.getenv('STRIPE_SECRET_KEY_LIVE', '')
        return vault.get_secret('gpubroker/stripe', 'secret_key_test') or \
               os.getenv('STRIPE_SECRET_KEY_TEST', '')
    
    @property
    def publishable_key(self) -> str:
        """Get publishable key for current mode."""
        if config.mode.is_live:
            return os.getenv('STRIPE_PUBLISHABLE_KEY_LIVE', '')
        return os.getenv('STRIPE_PUBLISHABLE_KEY_TEST', '')
    
    @property
    def webhook_secret(self) -> str:
        """Get webhook secret."""
        return vault.get_secret('gpubroker/stripe', 'webhook_secret') or \
               os.getenv('STRIPE_WEBHOOK_SECRET', '')
    
    @property
    def is_configured(self) -> bool:
        return bool(self.secret_key)


@dataclass
class PayPalConfig:
    """PayPal configuration - uses Vault for secrets."""
    
    @property
    def client_id(self) -> str:
        if config.mode.is_live:
            return vault.get_secret('gpubroker/paypal', 'client_id_live') or \
                   os.getenv('PAYPAL_CLIENT_ID_LIVE', '')
        return vault.get_secret('gpubroker/paypal', 'client_id_sandbox') or \
               os.getenv('PAYPAL_CLIENT_ID_SANDBOX', '')
    
    @property
    def client_secret(self) -> str:
        if config.mode.is_live:
            return vault.get_secret('gpubroker/paypal', 'client_secret_live') or \
                   os.getenv('PAYPAL_CLIENT_SECRET_LIVE', '')
        return vault.get_secret('gpubroker/paypal', 'client_secret_sandbox') or \
               os.getenv('PAYPAL_CLIENT_SECRET_SANDBOX', '')
    
    @property
    def api_base(self) -> str:
        if config.mode.is_live:
            return 'https://api-m.paypal.com'
        return 'https://api-m.sandbox.paypal.com'
    
    @property
    def is_configured(self) -> bool:
        return bool(self.client_id and self.client_secret)


@dataclass  
class DatabaseConfig:
    """Database configuration."""
    
    @property
    def url(self) -> str:
        return vault.get_secret('gpubroker/database', 'url') or \
               os.getenv('DATABASE_URL', '')
    
    @property
    def redis_url(self) -> str:
        return os.getenv('REDIS_URL', 'redis://redis:6379/0')
    
    @property
    def clickhouse_url(self) -> str:
        return os.getenv('CLICKHOUSE_URL', 'http://clickhouse:8123')


@dataclass
class AWSConfig:
    """AWS configuration."""
    
    @property
    def region(self) -> str:
        return os.getenv('AWS_REGION', 'us-east-1')
    
    @property
    def account_id(self) -> str:
        return os.getenv('AWS_ACCOUNT_ID', '')
    
    @property
    def access_key_id(self) -> str:
        return vault.get_secret('gpubroker/aws', 'access_key_id') or \
               os.getenv('AWS_ACCESS_KEY_ID', '')
    
    @property
    def secret_access_key(self) -> str:
        return vault.get_secret('gpubroker/aws', 'secret_access_key') or \
               os.getenv('AWS_SECRET_ACCESS_KEY', '')


@dataclass
class GPUProviderConfig:
    """GPU provider configuration."""
    
    @property
    def mock_data(self) -> bool:
        if config.mode.is_live:
            return False
        return os.getenv('MOCK_GPU_PROVISIONING', 'true').lower() == 'true'
    
    @property
    def runpod_api_key(self) -> str:
        return vault.get_secret('gpubroker/gpu', 'runpod_api_key') or \
               os.getenv('RUNPOD_API_KEY', '')
    
    @property
    def vastai_api_key(self) -> str:
        return vault.get_secret('gpubroker/gpu', 'vastai_api_key') or \
               os.getenv('VASTAI_API_KEY', '')
    
    @property
    def lambda_api_key(self) -> str:
        return vault.get_secret('gpubroker/gpu', 'lambda_api_key') or \
               os.getenv('LAMBDA_API_KEY', '')
    
    @property
    def cache_ttl(self) -> int:
        return 300 if config.mode.is_live else 30


@dataclass
class EmailConfig:
    """Email configuration."""
    
    @property
    def backend(self) -> str:
        if config.mode.is_live:
            return 'django_ses.SESBackend'
        return 'django.core.mail.backends.console.EmailBackend'
    
    @property
    def from_email(self) -> str:
        domain = config.domain.base
        if config.mode.is_live:
            return f'noreply@{domain}'
        return f'sandbox-noreply@{domain}'
    
    @property
    def use_ses(self) -> bool:
        return config.mode.is_live


@dataclass
class DomainConfig:
    """Domain and URL configuration."""
    
    @property
    def base(self) -> str:
        return os.getenv('GPUBROKER_DOMAIN', 'gpubroker.site')
    
    @property
    def base_url(self) -> str:
        return os.getenv('GPUBROKER_BASE_URL', f'https://{self.base}')
    
    @property
    def admin_url(self) -> str:
        return os.getenv('GPUBROKER_ADMIN_URL', f'https://admin.{self.base}')
    
    @property
    def api_url(self) -> str:
        if config.mode.is_live:
            return os.getenv('GPUBROKER_API_URL', f'https://api.{self.base}')
        return 'http://localhost:10355/api/v2'


@dataclass
class FeatureFlagsConfig:
    """Feature flags configuration."""
    
    @property
    def auto_confirm_email(self) -> bool:
        if config.mode.is_live:
            return False
        return os.getenv('AUTO_CONFIRM_EMAIL', 'true').lower() == 'true'
    
    @property
    def log_webhook_payloads(self) -> bool:
        if config.mode.is_live:
            return False
        return os.getenv('LOG_WEBHOOK_PAYLOADS', 'true').lower() == 'true'
    
    @property
    def verify_webhook_signatures(self) -> bool:
        return config.mode.is_live
    
    @property
    def track_analytics(self) -> bool:
        return config.mode.is_live


@dataclass
class GeoConfig:
    """Geographic and regional configuration."""
    
    @property
    def force_country(self) -> str:
        """Force specific country code for testing. Empty = auto-detect."""
        return os.getenv('GPUBROKER_FORCE_COUNTRY', '')
    
    @property
    def default_region(self) -> str:
        """Default region if geo-detection fails."""
        return os.getenv('GPUBROKER_DEFAULT_REGION', 'US')
    
    @property
    def deployment_region(self) -> str:
        """Deployment region: GLOBAL, LATAM, EC, US, EU."""
        return os.getenv('GPUBROKER_DEPLOYMENT_REGION', 'GLOBAL')
    
    @property
    def is_ecuador_deployment(self) -> bool:
        """Check if this is an Ecuador-specific deployment."""
        return self.deployment_region == 'EC' or self.force_country == 'EC'
    
    @property
    def is_latam_deployment(self) -> bool:
        """Check if this is a LATAM deployment."""
        return self.deployment_region in ('LATAM', 'EC')
    
    @property
    def s3_knowledge_bucket(self) -> str:
        """S3 bucket for Ecuador RUC/Cedula validation data."""
        return os.getenv('S3_KNOWLEDGE_BUCKET', 'yachaq-lex-raw-0017472631')


class ModeConfig:
    """Mode management (sandbox/live)."""
    
    def __init__(self):
        self._default = os.getenv('GPUBROKER_MODE', 'sandbox')
    
    @property
    def current(self) -> ModeType:
        """Get current mode (checks cache first)."""
        cached = cache.get(MODE_CACHE_KEY)
        if cached in ('sandbox', 'live'):
            return cached
        return self._default
    
    @property
    def is_sandbox(self) -> bool:
        return self.current == 'sandbox'
    
    @property
    def is_live(self) -> bool:
        return self.current == 'live'
    
    def set(self, mode: ModeType) -> bool:
        """Switch mode (persisted to cache)."""
        if mode not in ('sandbox', 'live'):
            raise ValueError(f"Invalid mode: {mode}")
        
        old_mode = self.current
        cache.set(MODE_CACHE_KEY, mode, timeout=MODE_CACHE_TIMEOUT)
        vault.clear_cache()  # Clear vault cache on mode switch
        
        logger.warning(f"Mode switched: {old_mode} -> {mode}")
        return True


# =============================================================================
# CENTRAL CONFIGURATION SINGLETON
# =============================================================================

class Config:
    """
    Central configuration singleton.
    
    Access all configuration through this single object.
    """
    
    def __init__(self):
        self._mode = ModeConfig()
        self._stripe = StripeConfig()
        self._paypal = PayPalConfig()
        self._database = DatabaseConfig()
        self._aws = AWSConfig()
        self._gpu = GPUProviderConfig()
        self._email = EmailConfig()
        self._domain = DomainConfig()
        self._features = FeatureFlagsConfig()
        self._geo = GeoConfig()
    
    @property
    def mode(self) -> ModeConfig:
        return self._mode
    
    @property
    def stripe(self) -> StripeConfig:
        return self._stripe
    
    @property
    def paypal(self) -> PayPalConfig:
        return self._paypal
    
    @property
    def database(self) -> DatabaseConfig:
        return self._database
    
    @property
    def aws(self) -> AWSConfig:
        return self._aws
    
    @property
    def gpu(self) -> GPUProviderConfig:
        return self._gpu
    
    @property
    def email(self) -> EmailConfig:
        return self._email
    
    @property
    def domain(self) -> DomainConfig:
        return self._domain
    
    @property
    def features(self) -> FeatureFlagsConfig:
        return self._features
    
    @property
    def geo(self) -> GeoConfig:
        return self._geo
    
    def get_status(self) -> Dict[str, Any]:
        """Get configuration status for admin dashboard."""
        return {
            'mode': self.mode.current,
            'is_live': self.mode.is_live,
            'vault_enabled': vault.enabled,
            'stripe_configured': self.stripe.is_configured,
            'paypal_configured': self.paypal.is_configured,
            'mock_gpu': self.gpu.mock_data,
            'email_backend': self.email.backend,
            'domain': self.domain.base,
            'geo': {
                'force_country': self.geo.force_country,
                'deployment_region': self.geo.deployment_region,
                'is_ecuador': self.geo.is_ecuador_deployment,
            },
        }
    
    def get_all(self) -> Dict[str, Any]:
        """Get all configuration (for debugging)."""
        return {
            'mode': self.mode.current,
            'vault': {'enabled': vault.enabled, 'addr': vault.addr},
            'stripe': {'configured': self.stripe.is_configured},
            'paypal': {'configured': self.paypal.is_configured, 'api_base': self.paypal.api_base},
            'gpu': {'mock': self.gpu.mock_data, 'cache_ttl': self.gpu.cache_ttl},
            'email': {'backend': self.email.backend, 'use_ses': self.email.use_ses},
            'domain': {'base': self.domain.base, 'api': self.domain.api_url},
            'features': {
                'auto_confirm': self.features.auto_confirm_email,
                'log_webhooks': self.features.log_webhook_payloads,
                'track_analytics': self.features.track_analytics,
            },
        }


# Global singleton
config = Config()

# Legacy compatibility alias
mode_service = config.mode

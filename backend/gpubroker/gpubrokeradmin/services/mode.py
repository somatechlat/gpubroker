"""
GPUBROKER Mode Service - Centralized Environment Mode Management

This module provides a single source of truth for Sandbox/Live mode switching.
Import this ANYWHERE in the codebase to get mode-aware configuration.

Usage:
    from gpubrokeradmin.services.mode import mode_service
    
    # Check current mode
    if mode_service.is_live:
        # Production behavior
    
    # Get mode-aware credentials
    stripe_key = mode_service.stripe.secret_key
    paypal_config = mode_service.paypal
    gpu_mock = mode_service.gpu_providers.mock_data
    
    # Switch mode (admin only)
    mode_service.set_mode('live')
"""
import logging
from dataclasses import dataclass
from typing import Literal, Optional, Dict, Any
from functools import cached_property

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

ModeType = Literal['sandbox', 'live']

# Cache key for persisted mode (allows runtime switching)
MODE_CACHE_KEY = 'gpubroker:global:mode'
MODE_CACHE_TIMEOUT = 86400 * 30  # 30 days


@dataclass
class StripeConfig:
    """Stripe configuration for current mode"""
    secret_key: str
    publishable_key: str
    webhook_secret: str
    mode: ModeType


@dataclass
class PayPalConfig:
    """PayPal configuration for current mode"""
    client_id: str
    client_secret: str
    mode: ModeType
    api_base: str


@dataclass
class EmailConfig:
    """Email configuration for current mode"""
    from_email: str
    support_email: str
    billing_email: str
    use_ses: bool
    backend: str  # Console or SES


@dataclass
class GPUProviderConfig:
    """GPU Provider configuration for current mode"""
    mock_data: bool  # Use mock GPU offers in sandbox
    runpod_api_key: str
    vastai_api_key: str
    lambda_api_key: str
    cache_ttl: int  # Shorter in sandbox for testing


@dataclass
class PodProvisioningConfig:
    """Pod provisioning configuration for current mode"""
    mock_provisioning: bool  # Skip real provisioning in sandbox
    auto_confirm: bool  # Auto-confirm pods in sandbox
    deployment_delay: int  # Seconds to simulate deployment


@dataclass
class AnalyticsConfig:
    """Analytics configuration for current mode"""
    track_events: bool  # Only track in live
    clickhouse_enabled: bool
    sample_rate: float  # 100% in sandbox, configurable in live


@dataclass
class WebhookConfig:
    """Webhook configuration for current mode"""
    verify_signatures: bool  # Strict in live, optional in sandbox
    retry_failed: bool
    log_payloads: bool  # Log full payloads in sandbox for debugging


class ModeService:
    """
    Centralized mode management service.
    
    Provides mode-aware configuration for ALL services:
    - Payments (Stripe, PayPal)
    - GPU Providers (RunPod, Vast.ai, Lambda)
    - Email (SES vs Console)
    - Pod Provisioning (Real vs Mock)
    - Analytics (ClickHouse)
    - Webhooks
    - URLs
    
    Mode can be set via:
    1. Environment variable GPUBROKER_MODE (default)
    2. Runtime switch via set_mode() (persisted to cache/db)
    """
    
    def __init__(self):
        self._default_mode: ModeType = getattr(settings, 'GPUBROKER_MODE', 'sandbox')
    
    @property
    def current_mode(self) -> ModeType:
        """Get current mode (checks cache first, then settings)"""
        cached_mode = cache.get(MODE_CACHE_KEY)
        if cached_mode in ('sandbox', 'live'):
            return cached_mode
        return self._default_mode
    
    @property
    def is_sandbox(self) -> bool:
        """Check if currently in sandbox mode"""
        return self.current_mode == 'sandbox'
    
    @property
    def is_live(self) -> bool:
        """Check if currently in live/production mode"""
        return self.current_mode == 'live'
    
    def set_mode(self, mode: ModeType) -> bool:
        """
        Switch global mode (requires admin privileges).
        Persists to cache so it survives restarts.
        """
        if mode not in ('sandbox', 'live'):
            raise ValueError(f"Invalid mode: {mode}. Must be 'sandbox' or 'live'")
        
        old_mode = self.current_mode
        cache.set(MODE_CACHE_KEY, mode, timeout=MODE_CACHE_TIMEOUT)
        
        logger.warning(
            f"GPUBROKER Mode switched: {old_mode} -> {mode}",
            extra={'old_mode': old_mode, 'new_mode': mode}
        )
        return True
    
    # =========================================================================
    # STRIPE CONFIGURATION
    # =========================================================================
    @property
    def stripe(self) -> StripeConfig:
        """Get Stripe configuration for current mode"""
        if self.is_live:
            return StripeConfig(
                secret_key=getattr(settings, 'STRIPE_SECRET_KEY_LIVE', '') or getattr(settings, 'STRIPE_SECRET_KEY', ''),
                publishable_key=getattr(settings, 'STRIPE_PUBLISHABLE_KEY_LIVE', ''),
                webhook_secret=getattr(settings, 'STRIPE_WEBHOOK_SECRET', ''),
                mode='live',
            )
        return StripeConfig(
            secret_key=getattr(settings, 'STRIPE_SECRET_KEY_TEST', '') or getattr(settings, 'STRIPE_SECRET_KEY', ''),
            publishable_key=getattr(settings, 'STRIPE_PUBLISHABLE_KEY_TEST', ''),
            webhook_secret=getattr(settings, 'STRIPE_WEBHOOK_SECRET', ''),
            mode='sandbox',
        )
    
    # =========================================================================
    # PAYPAL CONFIGURATION
    # =========================================================================
    @property
    def paypal(self) -> PayPalConfig:
        """Get PayPal configuration for current mode"""
        if self.is_live:
            return PayPalConfig(
                client_id=getattr(settings, 'PAYPAL_CLIENT_ID_LIVE', '') or getattr(settings, 'PAYPAL_CLIENT_ID', ''),
                client_secret=getattr(settings, 'PAYPAL_CLIENT_SECRET_LIVE', '') or getattr(settings, 'PAYPAL_CLIENT_SECRET', ''),
                mode='live',
                api_base='https://api-m.paypal.com',
            )
        return PayPalConfig(
            client_id=getattr(settings, 'PAYPAL_CLIENT_ID_SANDBOX', '') or getattr(settings, 'PAYPAL_CLIENT_ID', ''),
            client_secret=getattr(settings, 'PAYPAL_CLIENT_SECRET_SANDBOX', '') or getattr(settings, 'PAYPAL_CLIENT_SECRET', ''),
            mode='sandbox',
            api_base='https://api-m.sandbox.paypal.com',
        )
    
    # =========================================================================
    # GPU PROVIDER CONFIGURATION
    # =========================================================================
    @property
    def gpu_providers(self) -> GPUProviderConfig:
        """Get GPU provider configuration for current mode"""
        if self.is_live:
            return GPUProviderConfig(
                mock_data=False,
                runpod_api_key=getattr(settings, 'RUNPOD_API_KEY', ''),
                vastai_api_key=getattr(settings, 'VASTAI_API_KEY', ''),
                lambda_api_key=getattr(settings, 'LAMBDA_API_KEY', ''),
                cache_ttl=300,  # 5 min cache in live
            )
        return GPUProviderConfig(
            mock_data=getattr(settings, 'MOCK_GPU_PROVISIONING', True),
            runpod_api_key=getattr(settings, 'RUNPOD_API_KEY_TEST', '') or getattr(settings, 'RUNPOD_API_KEY', ''),
            vastai_api_key=getattr(settings, 'VASTAI_API_KEY_TEST', '') or getattr(settings, 'VASTAI_API_KEY', ''),
            lambda_api_key=getattr(settings, 'LAMBDA_API_KEY_TEST', '') or getattr(settings, 'LAMBDA_API_KEY', ''),
            cache_ttl=30,  # Short cache in sandbox for testing
        )
    
    # =========================================================================
    # POD PROVISIONING CONFIGURATION
    # =========================================================================
    @property
    def pod_provisioning(self) -> PodProvisioningConfig:
        """Get pod provisioning configuration for current mode"""
        if self.is_live:
            return PodProvisioningConfig(
                mock_provisioning=False,
                auto_confirm=False,
                deployment_delay=0,
            )
        return PodProvisioningConfig(
            mock_provisioning=getattr(settings, 'MOCK_GPU_PROVISIONING', True),
            auto_confirm=getattr(settings, 'AUTO_CONFIRM_EMAIL', True),
            deployment_delay=5,  # Simulate 5 second deployment
        )
    
    # =========================================================================
    # EMAIL CONFIGURATION
    # =========================================================================
    @property
    def email(self) -> EmailConfig:
        """Get email configuration for current mode"""
        domain = getattr(settings, 'GPUBROKER_DOMAIN', 'gpubroker.site')
        
        if self.is_live:
            return EmailConfig(
                from_email=f'noreply@{domain}',
                support_email=f'support@{domain}',
                billing_email=f'billing@{domain}',
                use_ses=True,
                backend='django_ses.SESBackend',
            )
        return EmailConfig(
            from_email=f'sandbox-noreply@{domain}',
            support_email=f'sandbox-support@{domain}',
            billing_email=f'sandbox-billing@{domain}',
            use_ses=False,
            backend='django.core.mail.backends.console.EmailBackend',
        )
    
    # =========================================================================
    # ANALYTICS CONFIGURATION
    # =========================================================================
    @property
    def analytics(self) -> AnalyticsConfig:
        """Get analytics configuration for current mode"""
        if self.is_live:
            return AnalyticsConfig(
                track_events=True,
                clickhouse_enabled=True,
                sample_rate=1.0,
            )
        return AnalyticsConfig(
            track_events=False,  # Don't pollute analytics with test data
            clickhouse_enabled=True,  # Still works but no tracking
            sample_rate=1.0,
        )
    
    # =========================================================================
    # WEBHOOK CONFIGURATION
    # =========================================================================
    @property
    def webhooks(self) -> WebhookConfig:
        """Get webhook configuration for current mode"""
        if self.is_live:
            return WebhookConfig(
                verify_signatures=True,  # Strict signature verification
                retry_failed=True,
                log_payloads=False,  # Don't log sensitive data
            )
        return WebhookConfig(
            verify_signatures=False,  # Allow testing without valid signatures
            retry_failed=False,
            log_payloads=True,  # Full logging for debugging
        )
    
    # =========================================================================
    # URL CONFIGURATION
    # =========================================================================
    @property
    def base_url(self) -> str:
        """Get base URL for current mode"""
        domain = getattr(settings, 'GPUBROKER_DOMAIN', 'gpubroker.site')
        if self.is_live:
            return f'https://{domain}'
        return getattr(settings, 'GPUBROKER_ADMIN_URL', 'http://localhost:28080')
    
    @property
    def api_url(self) -> str:
        """Get API URL for current mode"""
        if self.is_live:
            return getattr(settings, 'GPUBROKER_API_URL', '')
        return 'http://localhost:28080/api/v2'
    
    @property
    def webhook_base_url(self) -> str:
        """Get webhook callback base URL for current mode"""
        if self.is_live:
            domain = getattr(settings, 'GPUBROKER_DOMAIN', 'gpubroker.site')
            return f'https://api.{domain}/webhooks'
        return 'http://localhost:28080/api/v2/webhooks'
    
    # =========================================================================
    # STATUS & INFO
    # =========================================================================
    def get_status(self) -> dict:
        """Get current mode status for admin dashboard"""
        return {
            'mode': self.current_mode,
            'is_live': self.is_live,
            'is_sandbox': self.is_sandbox,
            'stripe_configured': bool(self.stripe.secret_key),
            'paypal_configured': bool(self.paypal.client_id),
            'mock_gpu': self.gpu_providers.mock_data,
            'mock_pods': self.pod_provisioning.mock_provisioning,
            'email_backend': self.email.backend,
            'domain': getattr(settings, 'GPUBROKER_DOMAIN', 'gpubroker.site'),
        }
    
    def get_all_configs(self) -> Dict[str, Any]:
        """Get all configuration for debugging/admin display"""
        return {
            'mode': self.current_mode,
            'stripe': {
                'mode': self.stripe.mode,
                'configured': bool(self.stripe.secret_key),
            },
            'paypal': {
                'mode': self.paypal.mode,
                'configured': bool(self.paypal.client_id),
                'api_base': self.paypal.api_base,
            },
            'gpu_providers': {
                'mock_data': self.gpu_providers.mock_data,
                'cache_ttl': self.gpu_providers.cache_ttl,
            },
            'pod_provisioning': {
                'mock': self.pod_provisioning.mock_provisioning,
                'auto_confirm': self.pod_provisioning.auto_confirm,
            },
            'email': {
                'backend': self.email.backend,
                'use_ses': self.email.use_ses,
            },
            'analytics': {
                'track_events': self.analytics.track_events,
            },
            'webhooks': {
                'verify_signatures': self.webhooks.verify_signatures,
                'log_payloads': self.webhooks.log_payloads,
            },
            'urls': {
                'base': self.base_url,
                'api': self.api_url,
                'webhooks': self.webhook_base_url,
            },
        }


# Global singleton instance - import this everywhere
mode_service = ModeService()

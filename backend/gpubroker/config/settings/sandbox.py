"""
Django sandbox settings for GPUBROKER.

Sandbox mode - testing environment with NO real charges.
Uses test API keys for all providers.
"""
from .base import *

# Force sandbox mode
GPUBROKER_MODE = 'sandbox'

DEBUG = True

# Sandbox-specific settings
ALLOWED_HOSTS = ['*']

# CORS - allow all in sandbox
CORS_ALLOW_ALL_ORIGINS = True

# Email backend - console in sandbox (no real emails)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Stripe - use test keys
STRIPE_SECRET_KEY = env('STRIPE_TEST_SECRET_KEY', default='sk_test_xxx')
STRIPE_WEBHOOK_SECRET = env('STRIPE_TEST_WEBHOOK_SECRET', default='whsec_test_xxx')

# Provider API mode - sandbox
PROVIDER_API_MODE = 'sandbox'

# Auto-confirm email verification in sandbox
AUTO_CONFIRM_EMAIL = True

# Mock GPU provisioning in sandbox
MOCK_GPU_PROVISIONING = True

# Logging
LOGGING['loggers']['gpubroker']['level'] = 'DEBUG'
LOGGING['loggers']['gpubrokeradmin']['level'] = 'DEBUG'
LOGGING['loggers']['gpubrokerpod']['level'] = 'DEBUG'

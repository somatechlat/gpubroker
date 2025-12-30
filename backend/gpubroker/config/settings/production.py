"""
Django production settings for GPUBROKER.

Production environment - 100% AWS Serverless.
Uses live API keys for all providers.
"""
from .base import *

# Force live mode
GPUBROKER_MODE = 'live'

DEBUG = False

# Security settings for production
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# CORS - restrict in production
CORS_ALLOW_ALL_ORIGINS = False

# Email backend - AWS SES in production
EMAIL_BACKEND = 'django_ses.SESBackend'
AWS_SES_REGION_NAME = env('AWS_REGION', default='us-east-1')
AWS_SES_REGION_ENDPOINT = f'email.{AWS_SES_REGION_NAME}.amazonaws.com'

# Stripe - use live keys
STRIPE_SECRET_KEY = env('STRIPE_LIVE_SECRET_KEY', default='')
STRIPE_WEBHOOK_SECRET = env('STRIPE_LIVE_WEBHOOK_SECRET', default='')

# Provider API mode - production
PROVIDER_API_MODE = 'production'

# Real email verification required
AUTO_CONFIRM_EMAIL = False

# Real GPU provisioning
MOCK_GPU_PROVISIONING = False

# Logging - less verbose in production
LOGGING['loggers']['gpubroker']['level'] = 'INFO'
LOGGING['loggers']['gpubrokeradmin']['level'] = 'INFO'
LOGGING['loggers']['gpubrokerpod']['level'] = 'INFO'

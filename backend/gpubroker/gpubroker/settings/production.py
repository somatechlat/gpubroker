"""
Django production settings for GPUBROKER project.
"""
from .base import *  # noqa: F401, F403

DEBUG = False

# Security settings for production
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Ensure SECRET_KEY is set in production
import os
if os.environ.get('SECRET_KEY') is None:
    raise ValueError('SECRET_KEY environment variable must be set in production')

# Ensure ALLOWED_HOSTS is properly configured
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['localhost', '127.0.0.1']:  # noqa: F405
    raise ValueError('ALLOWED_HOSTS must be properly configured in production')

# Production logging - less verbose
LOGGING['root']['level'] = 'WARNING'  # noqa: F405
LOGGING['loggers']['django']['level'] = 'WARNING'  # noqa: F405
LOGGING['loggers']['gpubroker']['level'] = 'INFO'  # noqa: F405

# Enable rate limiting in production
RATELIMIT_ENABLE = True

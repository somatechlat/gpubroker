"""
Django development settings for GPUBROKER project.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

# Development-specific allowed hosts
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# CORS - allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Disable SSL redirect in development
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# More verbose logging in development
LOGGING['root']['level'] = 'DEBUG'  # noqa: F405
LOGGING['loggers']['django']['level'] = 'DEBUG'  # noqa: F405

# Disable rate limiting in development (optional)
RATELIMIT_ENABLE = False

"""
Django development settings for GPUBROKER.

Development environment with debug enabled.
"""
from .base import *

DEBUG = True

# Development-specific settings
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# CORS - allow all in development
CORS_ALLOW_ALL_ORIGINS = True

# Email backend - console in development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Logging - more verbose in development
LOGGING['loggers']['gpubroker']['level'] = 'DEBUG'
LOGGING['loggers']['gpubrokeradmin']['level'] = 'DEBUG'
LOGGING['loggers']['gpubrokerpod']['level'] = 'DEBUG'

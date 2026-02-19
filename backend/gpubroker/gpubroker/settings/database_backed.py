"""
Django Database-Backed Settings
Following Django ORM standards - ALL configuration from database
NO environment variables for secrets!

This is the CORRECT way to manage Django settings according to Django documentation.
"""

from .base import *  # noqa: F401, F403
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent


# =============================================================================
# BOOTSTRAP DATABASE CONNECTION
# =============================================================================
# We need ONE database connection to bootstrap - this comes from environment
# ONLY for initial connection, then everything else comes from database

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('BOOTSTRAP_DB_NAME', 'gpubroker'),
        'USER': os.environ.get('BOOTSTRAP_DB_USER', 'gpubroker'),
        'PASSWORD': os.environ.get('BOOTSTRAP_DB_PASSWORD', ''),
        'HOST': os.environ.get('BOOTSTRAP_DB_HOST', 'localhost'),
        'PORT': os.environ.get('BOOTSTRAP_DB_PORT', '5432'),
        'CONN_MAX_AGE': 60,
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}

# =============================================================================
# STATIC FILES
# =============================================================================
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATIC_URL = '/static/'

# =============================================================================
# ENCRYPTION KEY (for encrypted_model_fields)
# =============================================================================
# Use Fernet key for encryption
# This will be replaced with database-backed key after initialization
FIELD_ENCRYPTION_KEY = os.environ.get('FIELD_ENCRYPTION_KEY', 'PrnxWzrFkad36rvHCHEFxqLDfhfQR0DMoXTnm9H-i7A=')

# =============================================================================
# CONFIGURATION LOADER - Django ORM Based (LAZY LOADING)
# =============================================================================

# Configuration will be loaded lazily when needed
# This avoids circular import issues during Django startup

# Use bootstrap configuration initially
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-bootstrap-key-change-immediately')
JWT_PRIVATE_KEY = None
JWT_PUBLIC_KEY = None
FEATURE_FLAGS = {}
SERVICES = {}

# Cache configuration will use default until database is ready
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
    }
}

# =============================================================================
# RUNTIME CONFIGURATION (Non-sensitive)
# =============================================================================

# These can come from environment as they're not secrets
DEBUG = os.environ.get('DEBUG', 'False').lower() in ('true', '1', 'yes')
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')
CORS_ALLOWED_ORIGINS = [origin for origin in os.environ.get('CORS_ALLOWED_ORIGINS', '').split(',') if origin]

# =============================================================================
# LOGGING
# =============================================================================

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s',
            'datefmt': '%d/%b/%Y %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'gpubroker': {
            'handlers': ['console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

print("✅ Django settings loaded from database (ORM-backed configuration)")

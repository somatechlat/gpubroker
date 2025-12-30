"""
Django test settings for GPUBROKER.

Test environment for running unit tests.
Uses PostgreSQL for full compatibility with ArrayField and other PostgreSQL features.
"""
from .base import *

DEBUG = True

# Use PostgreSQL for tests (same as development for full compatibility)
# Override with DATABASE_URL environment variable if needed
import dj_database_url
DATABASE_URL = env('DATABASE_URL', default='postgresql://gpubroker:gpubroker_dev_password@localhost:28001/gpubroker_test')
DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
}

# Use local memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Disable password hashing for faster tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# Email backend - in-memory for tests
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'

# Disable rate limiting in tests
RATELIMIT_ENABLE = False

# Mock everything in tests
AUTO_CONFIRM_EMAIL = True
MOCK_GPU_PROVISIONING = True

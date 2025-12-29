"""
Django test settings for GPUBROKER project.

Uses PostgreSQL for testing to ensure full compatibility with production
features like ArrayField. Connects to Docker container on port 28001.
"""
import os
from .base import *  # noqa: F401, F403

# Test-specific settings
DEBUG = False
SECRET_KEY = 'test-secret-key-not-for-production'

# Force all models to be managed for testing (creates tables via migrations)
# This is critical because production models use managed=False
TESTING = True

# Use PostgreSQL for tests (real infrastructure per Vibe Coding Rules)
# Docker container: gpubroker-postgres-1 on port 28001
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('TEST_DATABASE_NAME', 'gpubroker_test'),
        'USER': os.getenv('DATABASE_USER', 'gpubroker'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD', 'gpubroker_dev_password'),
        'HOST': os.getenv('DATABASE_HOST', 'localhost'),
        'PORT': os.getenv('DATABASE_PORT', '28001'),
        'TEST': {
            'NAME': 'gpubroker_test',
        },
    }
}

# Use local memory cache for tests
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'test-cache',
    }
}

# Use in-memory channel layer for tests
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    },
}

# Faster password hashing for tests
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.MD5PasswordHasher',
]

# JWT test keys (RSA 2048-bit for testing only)
# Generated fresh using cryptography library
JWT_PRIVATE_KEY = '-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEA0TrmmA9OY5ZsCjxoJ0YhFC4K7lYnhtw+RvFqqMnYJN+kGqTl\nWzrCwrtPqVE3ep8Mn30rbrA26MX92cyivbWxe7TNzJa63a9Cux88NUseSd01Mm0o\n0s/KbEG/UazyTtMMITukkxX8VFpBIbEhL9JK8kOMcVKg4SjuTGQQY/DMA8FZd6LM\nPj26lsiMsL+Vm9kxRfzEJUc7N5tyHWLADpoUue1yw1lfyo4NTOIqwWQhITlIP+YA\n+ARkyH1EBbNXOB7oRJkKxqDKE2/k+AaPzBjTGh+HH1IGvSeDnpRkwcal7XKFu0l7\nxEwPfRbPQUtFj2bzcGq5LCB/TNqPgX4qSLijSwIDAQABAoIBAARaPf3KeQ5SohYR\nwkuUMTqi5+X5Xi0iBnGiCAlRhEY6w3EtHlBS3UZWcIZ3LWOcTL5B86tZIxXzOHVV\nb8qT2F4DGYeOAyklbN/zpbmowbfg+tWntlexrDuq9SM/08fsAAPuTQgk8ZuCR88+\n82UenMyEDIyMSX3QRNTLUsP2zb0DjlQAlsgT6wx9v249JHt03kIEs27tfTxiEKhU\nab8xFB6WBlQbXaZSabRyCwun79JymWHyIFTExI/qzCBnT6N6LsgZKvQ90k07IkFq\nbMzYON15PooPreMkRMWsh+DTUT/kzVOb/YiaMLJDoAfewxVrVlVqd0r6p85SdHWZ\nt7LUdCECgYEA//mwctrElKGtuFB3hWr2t5qxMn/TvPkCLlKhOT6GNORWfVSOPeyN\nenTc5fdaVlySfgJMEyE31/RYlkDvsq164DKI1NtxhYPuQHQ5H/yXjaE9hEcVuO4k\n6cq9FMlJiwCoYZfmNCBKAEB3q+RnFQ0lGi66piZ0ZHTzcwJPNgD3duMCgYEA0UAP\nHo1nSS6qLeJ9YZKmUNFr2BGvzQJEMfEchUJ3JiAL9Wh3bimZ6w/mUZ1J29iaDZy1\nKsKwQldUnaUSwC8qTf7LaZrr8T2+E9MqiFvEzLo1QXELHdWdmBXxj08kNfzNquIr\nm+cof1DXSkO0sOm0cBYZWHpaVn9ZYdaHNwaBZnkCgYEAjNr6JImLiPpa3MSysGEG\nuEvQXCiI/EDN2W2wuA5WzX4ktby0tRCZXZw2/fiZ5lH0bpCXCiPKVfRoVu4OuHTL\n29kTAIZstnq9vQv3b0mQn+ftMP/ozSWGfHwKhgiphmrrPSDYFTD7Z54R/C2oJ6Zf\nF0RFgy4/+BN+73eC3QW1Jt8CgYBnGBma4u4tZzlfTAScKyWYEeYBWY11AxXYSUPV\nAA82EHnz2hllhEeaQYYnVchK8afM5xV3UN6IgQBmfysC1voP3WYYzMRMYjAhElwV\nPKl0eJW+fVSNyW5QvRb7lXFwy/IErFPyBuyz9X9sznja5PoKc0jfh8C0dx/xjUGn\nQaRFeQKBgEfQtuXDVnc2QJUveYzxk73rdW9XUFxn/DlHVjW9fyClGMkAcWhXChO3\neqjsQF7YcUPk7hE/bH0tMPwZ7qYTgIAK4jIvNK5Q+gbE8qt4ZXPhp7Rt9NIIQwA4\nr4O7ovsL0c4+VTlRVM86n3tHdWQjEuolmUoF8ddUBFCi+/EPANi+\n-----END RSA PRIVATE KEY-----\n'

JWT_PUBLIC_KEY = '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0TrmmA9OY5ZsCjxoJ0Yh\nFC4K7lYnhtw+RvFqqMnYJN+kGqTlWzrCwrtPqVE3ep8Mn30rbrA26MX92cyivbWx\ne7TNzJa63a9Cux88NUseSd01Mm0o0s/KbEG/UazyTtMMITukkxX8VFpBIbEhL9JK\n8kOMcVKg4SjuTGQQY/DMA8FZd6LMPj26lsiMsL+Vm9kxRfzEJUc7N5tyHWLADpoU\nue1yw1lfyo4NTOIqwWQhITlIP+YA+ARkyH1EBbNXOB7oRJkKxqDKE2/k+AaPzBjT\nGh+HH1IGvSeDnpRkwcal7XKFu0l7xEwPfRbPQUtFj2bzcGq5LCB/TNqPgX4qSLij\nSwIDAQAB\n-----END PUBLIC KEY-----\n'

# Disable rate limiting for tests
RATELIMIT_ENABLE = False

# Logging - minimal for tests
LOGGING = {
    'version': 1,
    'disable_existing_loggers': True,
    'handlers': {
        'null': {
            'class': 'logging.NullHandler',
        },
    },
    'root': {
        'handlers': ['null'],
        'level': 'CRITICAL',
    },
}


# Custom test runner that enables managed=True for all models
TEST_RUNNER = 'gpubroker.test_runner.ManagedModelTestRunner'

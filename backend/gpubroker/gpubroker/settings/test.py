"""
Django test settings for GPUBROKER project.

Uses PostgreSQL database for testing to ensure full compatibility
with production features like ArrayField.
"""
import os
from .base import *  # noqa: F401, F403

# Test-specific settings
DEBUG = False
SECRET_KEY = 'test-secret-key-not-for-production'

# Use PostgreSQL for tests (same as production)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('TEST_DATABASE_NAME', 'gpubroker_test'),
        'USER': os.getenv('DATABASE_USER', 'postgres'),
        'PASSWORD': os.getenv('DATABASE_PASSWORD', 'postgres'),
        'HOST': os.getenv('DATABASE_HOST', 'localhost'),
        'PORT': os.getenv('DATABASE_PORT', '5432'),
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
JWT_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA0Z3VS5JJcds3xfn/ygWyF8PbnGy0AHB7MvXNkFCTqXnPOS0V
OMni9gfp7jqU6ygGj1YLMSMWICHtchLpq1dWdqzYbVPqllCTNXYlVwJjN5E8gCaw
rU9bFTTJlGSBFwlZDXVAorJUwlDVcAM8u6PkLPnPqGNO+YLfZEkFnkzKdOjWjyKn
FbIgNmBURPpRqaKJEHBSP7xKxT8Ixi4lNwJDt7fjqFGPqdaTdQiFcGYXlSP8YeYB
LZD3fMxWRPU6AgjtPiJNLFK1FZDfWMnmHfDgCb2e3j4x2mcNBJdFYwQKlqHPMMFj
LaxLfwWlHsOxmjMPz8z8Pj2mFaUMCz6KM+ALtwIDAQABAoIBAFGpNeUEhTBUYXlb
E3NBreI0vJmVOBIkWqdHxMiiNgJhPjPE6uyKH/dEe4A5F/PrBjkqpWgkma+Lrlqx
Va6bpIEqSOgctvLq2tnVDphMZb0qsRtvqTnF8gsPgWAn6FCQW0T1ITHSE7PxGjkp
5LinzNhmYCqzNqWJzkWvMcovilc/ah+WC/6BPQN/AN7Xp3Y1cxOk8gZfwBPT/bpQ
Ia7eL9fAm1DQXN8Fzsea0kxbT/7yQDqsj0VJlfKo4hn5pgHqXSKj8heRMdCe7t8E
PfVflYn/s7qqZGILMYvqr9pKqc7h3xWfOSBLI6pR/2U0QkYXqZDgJb+qLap440yz
yqWAQYECgYEA7z3vSKrCzaYDBFGr1V5S0hT1j9j0YCzCsnmCPkLmPRFMt85v+ymF
zlGbQYG3EINhMbJ4RvcWr5GBNh4A8H7tm9hJqfT1GfCsRmHxpbklBxHIYSCjHfCr
5ij5LneKRaYKzbQUWdPMmZgfAeVJh1vPTrihqvSsBl9Mv0j5xvYNFycCgYEA37+X
mBCLmfN50HIxUgODqXwK8jJbMYRbxUEVwNDlLqpnPvPqJHn0M5L5z3GrRf1bHjHC
0CS5WCkpR6ADPFlAJloXWPgLgKCfYOyMIjlP4VCG7bFH+Wd2LkiNxwCbVJ5EKumP
e8LIvPb4JGrNtPpzDXmE8ySLzPmCdCLPSRFcGMECgYEAqkdMvPaUrGpKmFKJd4eR
xdCYk0FFDP/OcTfPNynBMgdKLfKM8xqv7P545JEfns0MPG0CYmDLpaNjqz5yPpvN
BoLfpWpN6NbPigPQ9Xi7Z8EGSQF1h8KlRtjxK/dq1rCnGws0fQlo79CRifLiCS8D
AVmLePHENwrvAFwfVnCn0ysCgYAJu+BoNlRfgfT1fDpNog3ffy5fXrpSgMU5xraL
nhBPrNIgPpFTUFGHpNaqdSIdzjhHN+f5EXkEjFJhEB21pwI/ctpgBuM1XpMHlDTL
lFsz7br5gQ1xgJAFz8BL3xPdKrwBxNdLYqFdpRMcvFdxPLzp8lkfRcD5z5X8xk5I
3E6AAQKBgC5ChK0De6lvJkXXqqav0l4W7tYpnDvqfTrJsrbbJ0Vn5OKlGPEinN5D
LP9G7WF8q0z4H+Yp3xGdK/FHqz0lKL5Ash4MXCQ2jMXCVjBhPHJqKVuAFqo6/JRk
rYYqXdMBevBV+zP+M/bBPcLPwSj6CqfMgHsohwfnswPprgx5uGUi
-----END RSA PRIVATE KEY-----"""

JWT_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA0Z3VS5JJcds3xfn/ygWy
F8PbnGy0AHB7MvXNkFCTqXnPOS0VOMni9gfp7jqU6ygGj1YLMSMWICHtchLpq1dW
dqzYbVPqllCTNXYlVwJjN5E8gCawrU9bFTTJlGSBFwlZDXVAorJUwlDVcAM8u6Pk
LPnPqGNO+YLfZEkFnkzKdOjWjyKnFbIgNmBURPpRqaKJEHBSP7xKxT8Ixi4lNwJD
t7fjqFGPqdaTdQiFcGYXlSP8YeYBLZD3fMxWRPU6AgjtPiJNLFK1FZDfWMnmHfDg
Cb2e3j4x2mcNBJdFYwQKlqHPMMFjLaxLfwWlHsOxmjMPz8z8Pj2mFaUMCz6KM+AL
twIDAQAB
-----END PUBLIC KEY-----"""

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

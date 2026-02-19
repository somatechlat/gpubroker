"""
Django production settings for GPUBROKER project.

Uses validated configuration system with Pydantic for production reliability.
Implements security best practices and performance optimizations.
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# =============================================================================
# VALIDATED CONFIGURATION SYSTEM
# =============================================================================
import sys

sys.path.append(str(BASE_DIR / "config"))

from validated_config import CONFIG

# =============================================================================
# DJANGO CORE SETTINGS
# =============================================================================

# Security
SECRET_KEY = CONFIG.security.secret_key
DEBUG = CONFIG.security.debug
ALLOWED_HOSTS = CONFIG.security.allowed_hosts

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party apps
    "corsheaders",
    "channels",
    "django_prometheus",
    # Local apps
    "apps.auth_app",
    "apps.providers",
    "apps.kpi",
    "apps.math_core",
    "apps.ai_assistant",
    "apps.websocket_gateway",
]

MIDDLEWARE = [
    "django_prometheus.middleware.PrometheusBeforeMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Custom middleware for security
    "shared.middleware.security.SecurityMiddleware",
    # Prometheus
    "django_prometheus.middleware.PrometheusAfterMiddleware",
]

ROOT_URLCONF = "gpubroker.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "gpubroker.wsgi.application"

# =============================================================================
# DATABASE SETTINGS
# =============================================================================

DATABASES = {
    "default": {
        "ENGINE": f"django.db.backends.{CONFIG.database.engine.value}",
        "NAME": CONFIG.database.name,
        "USER": CONFIG.database.user,
        "PASSWORD": CONFIG.database.password.get_secret_value(),
        "HOST": CONFIG.database.host,
        "PORT": CONFIG.database.port,
        "OPTIONS": {
            "connect_timeout": CONFIG.database.connect_timeout,
        },
        "CONN_MAX_AGE": 60,
    }
}

# =============================================================================
# CACHING SETTINGS
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": CONFIG.database.redis_url,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "MAX_CONNECTIONS": CONFIG.database.redis_max_connections,
        },
        "KEY_PREFIX": CONFIG.application.cache_key_prefix,
        "TIMEOUT": CONFIG.application.cache_timeout,
    }
}

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC FILES AND MEDIA
# =============================================================================

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =============================================================================
# AUTHENTICATION
# =============================================================================

AUTH_USER_MODEL = "auth_app.User"

# Session configuration
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_SECURE = not CONFIG.is_development
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {
            "min_length": 12,
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# =============================================================================
# CORS SETTINGS
# =============================================================================

CORS_ALLOWED_ORIGINS = CONFIG.security.cors_allowed_origins
CORS_ALLOW_CREDENTIALS = CONFIG.security.cors_allow_credentials
CORS_ALLOWED_METHODS = CONFIG.security.cors_allowed_methods

# =============================================================================
# JWT AUTHENTICATION SETTINGS
# =============================================================================

import jwt
from datetime import timedelta

JWT_AUTH = {
    "JWT_SECRET_KEY": CONFIG.security.secret_key,
    "JWT_ALGORITHM": CONFIG.security.jwt_algorithm,
    "JWT_ACCESS_TOKEN_LIFETIME": timedelta(
        seconds=CONFIG.security.jwt_access_token_lifetime
    ),
    "JWT_REFRESH_TOKEN_LIFETIME": timedelta(
        seconds=CONFIG.security.jwt_refresh_token_lifetime
    ),
    "JWT_AUTH_HEADER_TYPES": ["Bearer"],
    "JWT_AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
}

# Custom JWT settings
if CONFIG.security.jwt_private_key and CONFIG.security.jwt_public_key:
    JWT_AUTH.update(
        {
            "JWT_PRIVATE_KEY": CONFIG.security.jwt_private_key,
            "JWT_PUBLIC_KEY": CONFIG.security.jwt_public_key,
        }
    )

# =============================================================================
# LOGGING SETTINGS
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": CONFIG.logging.format,
        },
        "simple": {
            "format": "%(levelname)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": CONFIG.logging.level.value,
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "file": {
            "level": CONFIG.logging.level.value,
            "class": "logging.handlers.RotatingFileHandler",
            "filename": CONFIG.logging.file_path or "/var/log/gpubroker/django.log",
            "maxBytes": CONFIG.logging.max_file_size,
            "backupCount": CONFIG.logging.backup_count,
            "formatter": "verbose",
        }
        if CONFIG.logging.file_path
        else None,
    },
    "root": {
        "handlers": ["console"] + (["file"] if CONFIG.logging.file_path else []),
        "level": CONFIG.logging.level.value,
    },
    "loggers": {
        "django": {
            "handlers": ["console"] + (["file"] if CONFIG.logging.file_path else []),
            "level": "INFO",
            "propagate": False,
        },
        "gpubroker": {
            "handlers": ["console"] + (["file"] if CONFIG.logging.file_path else []),
            "level": CONFIG.logging.level.value,
            "propagate": False,
        },
    },
}

# =============================================================================
# EXTERNAL SERVICES
# =============================================================================

# PayPal settings
PAYPAL = {
    "CLIENT_ID_SANDBOX": CONFIG.external_services.paypal_client_id_sandbox or "",
    "CLIENT_SECRET_SANDBOX": (
        CONFIG.external_services.paypal_client_secret_sandbox.get_secret_value()
        if CONFIG.external_services.paypal_client_secret_sandbox
        else ""
    ),
    "CLIENT_ID_LIVE": CONFIG.external_services.paypal_client_id_live or "",
    "CLIENT_SECRET_LIVE": (
        CONFIG.external_services.paypal_client_secret_live.get_secret_value()
        if CONFIG.external_services.paypal_client_secret_live
        else ""
    ),
    "MODE": CONFIG.external_services.paypal_mode,
    "WEBHOOK_ID": CONFIG.external_services.paypal_webhook_id,
}

# Email settings
EMAIL_BACKEND = CONFIG.external_services.email_backend
EMAIL_HOST = CONFIG.external_services.email_host
EMAIL_PORT = CONFIG.external_services.email_port
EMAIL_USE_TLS = CONFIG.external_services.email_use_tls
EMAIL_HOST_USER = CONFIG.external_services.email_host_user
EMAIL_HOST_PASSWORD = (
    CONFIG.external_services.email_host_password.get_secret_value()
    if CONFIG.external_services.email_host_password
    else ""
)

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000 if CONFIG.is_production else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = CONFIG.is_production
SECURE_HSTS_PRELOAD = CONFIG.is_production
SECURE_REDIRECT_EXEMPT = []
SECURE_SSL_REDIRECT = CONFIG.is_production

# CSRF settings
CSRF_TRUSTED_ORIGINS = CONFIG.security.csrf_trusted_origins
CSRF_COOKIE_SECURE = CONFIG.is_production
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"

# =============================================================================
# DJANGO CHANNELS (WEBSOCKETS)
# =============================================================================

ASGI_APPLICATION = "gpubroker.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [CONFIG.database.redis_url],
            "capacity": 1500,
            "expiry": 60,
        },
    },
}

# =============================================================================
# MONITORING AND METRICS
# =============================================================================

# Prometheus
if CONFIG.external_services.prometheus_enabled:
    INSTALLED_APPS.append("django_prometheus")
    PROMETHEUS_EXPORT_MIGRATIONS = False

# Health checks
HEALTH_CHECK = {
    "BACKEND": "health_check.db.DatabaseCheck",
}

# =============================================================================
# RATE LIMITING
# =============================================================================

if CONFIG.security.rate_limit_enabled:
    RATELIMIT_ENABLE = True
    RATELIMIT_USE_CACHE = "default"
    RATELIMIT_VIEW = "shared.middleware.rate_limit.get_rate_limit_key"

# =============================================================================
# API SETTINGS
# =============================================================================

# Django Ninja API
API_PREFIX = CONFIG.application.api_prefix
API_VERSION = CONFIG.application.api_version

# Pagination
REST_FRAMEWORK = {
    "DEFAULT_PAGINATION_CLASS": "shared.pagination.StandardResultsSetPagination",
    "PAGE_SIZE": CONFIG.application.default_page_size,
    "PAGE_SIZE_QUERY_PARAM": "page_size",
    "MAX_PAGE_SIZE": CONFIG.application.max_page_size,
}

# =============================================================================
# PERFORMANCE SETTINGS
# =============================================================================

# Database connection pooling
DATABASE_POOL_ARGS = {
    "max_overflow": 10,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}

# File uploads
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# =============================================================================
# DEVELOPMENT-SPECIFIC SETTINGS
# =============================================================================

if CONFIG.is_development:
    # Debug toolbar
    INSTALLED_APPS.append("debug_toolbar")
    MIDDLEWARE.insert(0, "debug_toolbar.middleware.DebugToolbarMiddleware")
    INTERNAL_IPS = ["127.0.0.1", "localhost"]

    # CORS for development
    CORS_ALLOWED_ORIGINS.extend(
        [
            "http://localhost:3000",
            "http://localhost:8080",
            "http://127.0.0.1:3000",
            "http://127.0.0.1:8080",
        ]
    )

# =============================================================================
# CUSTOM SETTINGS
# =============================================================================

# Feature flags
FEATURE_FLAGS = {
    "AI_ASSISTANT": CONFIG.application.enable_ai_assistant,
    "REAL_TIME_UPDATES": CONFIG.application.enable_real_time_updates,
    "ADVANCED_ANALYTICS": CONFIG.application.enable_advanced_analytics,
}

# Application info
APP_INFO = {
    "NAME": CONFIG.application.name,
    "VERSION": CONFIG.application.version,
    "ENVIRONMENT": CONFIG.application.environment.value,
}

# Vault configuration (for services that need direct access)
VAULT_CONFIG = {
    "ADDR": CONFIG.external_services.vault_addr,
    "TOKEN": (
        CONFIG.external_services.vault_token.get_secret_value()
        if CONFIG.external_services.vault_token
        else ""
    ),
    "TIMEOUT": CONFIG.external_services.vault_timeout,
    "AVAILABLE": CONFIG.vault_available,
}

# =============================================================================
# TESTING SETTINGS
# =============================================================================

if "test" in sys.argv:
    # Override for testing
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }

    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        }
    }

    PASSWORD_HASHERS = [
        "django.contrib.auth.hashers.MD5PasswordHasher",
    ]

    LOGGING["loggers"] = {}
    LOGGING["root"]["level"] = "WARNING"

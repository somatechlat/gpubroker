"""
Django production settings for GPUBROKER project.
Production-Grade Infrastructure with Vault Integration
Following VIBE CODING RULES - NO HARDCODED SECRETS
"""

import os
import socket
from .base import *  # noqa: F401, F403

DEBUG = False

# =============================================================================
# VAULT INTEGRATION - SECRETS MANAGEMENT ONLY
# =============================================================================
# According to HashiCorp Vault docs at https://www.vaultproject.io/docs/configuration
# All secrets MUST be retrieved from Vault, NO environment variables for secrets

import requests
import json
from django.core.exceptions import ImproperlyConfigured


class VaultSecretsManager:
    """Production-grade Vault secrets manager following security best practices."""

    def __init__(self):
        self.vault_addr = os.environ.get("VAULT_ADDR")
        self.vault_role_id = os.environ.get("VAULT_ROLE_ID")
        self.vault_secret_id = os.environ.get("VAULT_SECRET_ID")

        if not all([self.vault_addr, self.vault_role_id, self.vault_secret_id]):
            raise ImproperlyConfigured(
                "VAULT_ADDR, VAULT_ROLE_ID, and VAULT_SECRET_ID must be set for production"
            )

        self.token = None
        self._authenticate()

    def _authenticate(self):
        """Establish secure connection to Vault."""
        try:
            auth_url = f"{self.vault_addr}/v1/auth/approle/login"
            auth_payload = {
                "role_id": self.vault_role_id,
                "secret_id": self.vault_secret_id,
            }

            response = requests.post(auth_url, json=auth_payload, timeout=10)
            response.raise_for_status()

            auth_data = response.json()
            if "auth" not in auth_data:
                raise ImproperlyConfigured("Vault authentication failed")

            self.token = auth_data["auth"]["client_token"]

        except Exception as e:
            raise ImproperlyConfigured(f"Failed to connect to Vault: {e}")

    def get_secret(self, path, field=None):
        """Retrieve secret from Vault with automatic token refresh."""
        try:
            if not self.token:
                self._authenticate()

            headers = {"X-Vault-Token": self.token}
            secret_url = f"{self.vault_addr}/v1/secret/data/{path}"

            response = requests.get(secret_url, headers=headers, timeout=10)
            response.raise_for_status()

            secret_data = response.json()

            if field:
                return secret_data["data"]["data"][field]
            return secret_data["data"]["data"]

        except Exception as e:
            raise ImproperlyConfigured(f"Failed to retrieve secret {path}: {e}")


# Initialize Vault manager
vault = VaultSecretsManager()

# =============================================================================
# CRITICAL SECURITY SETTINGS - VAULT ONLY
# =============================================================================

# SECRET_KEY from Vault - NO environment variables for secrets
SECRET_KEY = vault.get_secret("gpubroker/django", "secret_key")
if SECRET_KEY in [
    "CHANGE_THIS_TO_DJANGO_SECRET_KEY",
    "change-this-to-a-secure-random-string",
]:
    raise ValueError(
        "SECRET_KEY from Vault must be set to a secure value in production"
    )

# ALLOWED_HOSTS from environment (runtime variables are acceptable)
ALLOWED_HOSTS = os.environ.get("ALLOWED_HOSTS", "").split(",")
if not ALLOWED_HOSTS or ALLOWED_HOSTS == ["localhost", "127.0.0.1"]:
    raise ValueError("ALLOWED_HOSTS must be properly configured for production domain")

# HTTPS and SSL Security
SECURE_SSL_REDIRECT = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Session Security
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_AGE = 3600  # 1 hour
SESSION_SAVE_EVERY_REQUEST = True

# CSRF Protection
CSRF_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]
CSRF_FAILURE_VIEW = "django.views.csrf.csrf_failure"

# =============================================================================
# DATABASE SECURITY - VAULT INTEGRATION
# =============================================================================

# Database configuration from Vault - NO hardcoded secrets
try:
    db_config = vault.get_secret("gpubroker/database")
    DATABASE_URL = db_config["url"]

    # Validate database URL doesn't contain default passwords
    if "gpubroker_dev_password" in DATABASE_URL or "CHANGE_THIS" in DATABASE_URL:
        raise ValueError(
            "Database URL from Vault contains default/placeholder passwords - change immediately!"
        )

    # Override database settings with secure configuration from Vault
    import dj_database_url

    DATABASES = {"default": dj_database_url.parse(DATABASE_URL)}

    # Basic connection settings
    db_config_parsed = DATABASES["default"]
    db_config_parsed["CONN_MAX_AGE"] = db_config.get("conn_max_age", 60)
    db_config_parsed["OPTIONS"] = {
        "sslmode": db_config.get("sslmode", "require"),
        "sslcert": db_config.get("sslcert"),
        "sslkey": db_config.get("sslkey"),
        "sslrootcert": db_config.get("sslrootcert"),
        "connect_timeout": db_config.get("connect_timeout", 60),
        "options": "-c default_transaction_isolation=serializable",
    }

    # Production connection options
    db_config_parsed["OPTIONS"]["connect_timeout"] = db_config.get(
        "connect_timeout", 60
    )
    db_config_parsed["OPTIONS"]["application_name"] = "gpubroker_production"

    # Django batch size settings
    DEFAULT_BATCH_SIZE = 1000
    DEFAULT_MAX_BATCH_SIZE = 5000

    DATABASES = {"default": db_config_parsed}

except Exception as e:
    raise ImproperlyConfigured(f"Failed to load database configuration from Vault: {e}")

# =============================================================================
# REDIS CONFIGURATION - VAULT INTEGRATION
# =============================================================================

try:
    redis_config = vault.get_secret("gpubroker/redis")

    # Django Cache configuration
    CACHES = {
        "default": {
            "BACKEND": "django_redis.cache.RedisCache",
            "LOCATION": redis_config["url"],
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": redis_config.get("max_connections", 50),
                    "retry_on_timeout": True,
                    "socket_connect_timeout": redis_config.get("connect_timeout", 5),
                    "socket_timeout": redis_config.get("socket_timeout", 5),
                    "health_check_interval": redis_config.get(
                        "health_check_interval", 30
                    ),
                },
                "PARSER_CLASS": "django_redis.parsers.JSONParser",
                "COMPRESSOR": "django_redis.compressors.zlib.ZlibCompressor",
                "IGNORE_EXCEPTIONS": True,
                "LOG_IGNORED_EXCEPTIONS": True,
            },
            "KEY_PREFIX": redis_config.get("key_prefix", "gpubroker"),
            "TIMEOUT": redis_config.get("timeout", 300),
            "VERSION": redis_config.get("version", 1),
        }
    }

    # Session configuration
    SESSION_ENGINE = "django.contrib.sessions.backends.cache"
    SESSION_CACHE_ALIAS = "default"
    SESSION_COOKIE_AGE = redis_config.get("session_age", 3600)

    # Celery configuration (if using Celery)
    CELERY_BROKER_URL = redis_config["url"]
    CELERY_RESULT_BACKEND = redis_config["url"]

    # WebSocket Channels configuration
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [{"url": redis_config["url"]}],
                "capacity": redis_config.get("channel_capacity", 1500),
                "expiry": redis_config.get("channel_expiry", 60),
            },
        },
    }

except Exception as e:
    raise ImproperlyConfigured(f"Failed to load Redis configuration from Vault: {e}")

# =============================================================================
# RATE LIMITING AND THROTTLING
# =============================================================================

# Rate limiting configuration
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = "default"

# Django REST Framework throttling (if used)
REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "login": "5/minute",
        "password_reset": "3/hour",
    },
}

# =============================================================================
# INPUT VALIDATION AND SECURITY
# =============================================================================

# File upload security
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Form security
FORMS_URL_FIELD_ASSUME_HTTPS = True

# =============================================================================
# ERROR HANDLING AND LOGGING
# =============================================================================

# Secure error handling
ADMINS = [
    admin.strip() for admin in os.environ.get("ADMINS", "").split(",") if admin.strip()
]
MANAGERS = ADMINS

# Production logging - secure and detailed
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "secure": {
            "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
            "datefmt": "%d/%b/%Y %H:%M:%S",
        },
    },
    "handlers": {
        "file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/gpubroker/django.log",
            "maxBytes": 1024 * 1024 * 10,  # 10MB
            "backupCount": 5,
            "formatter": "secure",
        },
        "security": {
            "level": "WARNING",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/gpubroker/security.log",
            "maxBytes": 1024 * 1024 * 10,  # 10MB
            "backupCount": 10,
            "formatter": "secure",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["file", "security"],
            "level": "WARNING",
            "propagate": True,
        },
        "gpubroker": {
            "handlers": ["file", "security"],
            "level": "INFO",
            "propagate": True,
        },
        "django.security": {
            "handlers": ["security"],
            "level": "WARNING",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["file"],
        "level": "WARNING",
    },
}

# =============================================================================
# API SECURITY - VAULT INTEGRATION
# =============================================================================

try:
    jwt_config = vault.get_secret("gpubroker/jwt")

    # JWT Security from Vault
    JWT_SECRET_KEY = jwt_config.get("secret_key", SECRET_KEY)
    JWT_ACCESS_TOKEN_LIFETIME = jwt_config.get(
        "access_token_lifetime", 900
    )  # 15 minutes
    JWT_REFRESH_TOKEN_LIFETIME = jwt_config.get(
        "refresh_token_lifetime", 86400
    )  # 24 hours
    JWT_ALGORITHM = jwt_config.get("algorithm", "HS256")

    # JWT audience and issuer for enhanced security
    JWT_AUDIENCE = jwt_config.get("audience", "gpubroker-api")
    JWT_ISSUER = jwt_config.get("issuer", "gpubroker-auth")

    # API Key Security
    API_KEY_LENGTH = jwt_config.get("api_key_length", 32)
    API_KEY_PREFIX = jwt_config.get("api_key_prefix", "gpb_")

    # Django REST Framework with enhanced security
    REST_FRAMEWORK = {
        "DEFAULT_AUTHENTICATION_CLASSES": [
            "apps.security.auth.VaultBackedJWTAuthentication",
            "apps.security.auth.APIKeyAuthentication",
        ],
        "DEFAULT_PERMISSION_CLASSES": [
            "rest_framework.permissions.IsAuthenticated",
        ],
        "DEFAULT_RENDERER_CLASSES": [
            "rest_framework.renderers.JSONRenderer",
        ],
        "DEFAULT_PARSER_CLASSES": [
            "rest_framework.parsers.JSONParser",
            "rest_framework.parsers.MultiPartParser",
        ],
        "DEFAULT_THROTTLE_CLASSES": [
            "rest_framework.throttling.AnonRateThrottle",
            "rest_framework.throttling.UserRateThrottle",
        ],
        "DEFAULT_THROTTLE_RATES": {
            "anon": jwt_config.get("anon_rate_limit", "100/hour"),
            "user": jwt_config.get("user_rate_limit", "1000/hour"),
            "login": jwt_config.get("login_rate_limit", "5/minute"),
            "password_reset": jwt_config.get("password_reset_rate_limit", "3/hour"),
            "api": jwt_config.get("api_rate_limit", "5000/hour"),
        },
        "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
        "PAGE_SIZE": jwt_config.get("page_size", 50),
        "DEFAULT_FILTER_BACKENDS": [
            "django_filters.rest_framework.DjangoFilterBackend",
        ],
    }

except Exception as e:
    raise ImproperlyConfigured(f"Failed to load JWT configuration from Vault: {e}")

# =============================================================================
# EXTERNAL SERVICES - VAULT INTEGRATION
# =============================================================================

try:
    services_config = vault.get_secret("gpubroker/services")

    # Stripe configuration
    STRIPE_PUBLISHABLE_KEY = services_config.get("stripe_publishable_key")
    STRIPE_SECRET_KEY = services_config.get("stripe_secret_key")
    STRIPE_WEBHOOK_SECRET = services_config.get("stripe_webhook_secret")

    # AWS configuration (if needed)
    AWS_ACCESS_KEY_ID = services_config.get("aws_access_key_id")
    AWS_SECRET_ACCESS_KEY = services_config.get("aws_secret_access_key")
    AWS_DEFAULT_REGION = services_config.get("aws_default_region", "us-east-1")

    # Email configuration (SMTP)
    EMAIL_HOST = services_config.get("email_host")
    EMAIL_PORT = services_config.get("email_port", 587)
    EMAIL_HOST_USER = services_config.get("email_host_user")
    EMAIL_HOST_PASSWORD = services_config.get("email_host_password")
    EMAIL_USE_TLS = services_config.get("email_use_tls", True)

    # Monitoring configuration
    SENTRY_DSN = services_config.get("sentry_dsn")
    PROMETHEUS_PUSHGATEWAY = services_config.get("prometheus_pushgateway")

    # External API configurations
    GPU_PROVIDER_API_KEYS = services_config.get("gpu_provider_api_keys", {})

    # CORS configuration from Vault
    CORS_ALLOWED_ORIGINS = services_config.get("cors_allowed_origins", [])
    CORS_ALLOW_CREDENTIALS = services_config.get("cors_allow_credentials", True)
    CORS_ALLOWED_HEADERS = services_config.get(
        "cors_allowed_headers",
        [
            "accept",
            "accept-language",
            "content-language",
            "authorization",
            "content-type",
            "x-requested-with",
        ],
    )

except Exception as e:
    raise ImproperlyConfigured(f"Failed to load services configuration from Vault: {e}")

# =============================================================================
# ADDITIONAL SECURITY MIDDLEWARE - ENHANCED
# =============================================================================

# Add security middleware to existing list
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.http.ConditionalGetMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    "apps.security.middleware.VaultAuthenticatedMiddleware",
    "apps.security.middleware.RateLimitMiddleware",
    "apps.security.middleware.SecurityHeadersMiddleware",
    "apps.security.middleware.InputValidationMiddleware",
    "apps.security.middleware.AuditLoggingMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# =============================================================================
# MONITORING AND ALERTS - VAULT INTEGRATION
# =============================================================================

try:
    monitoring_config = vault.get_secret("gpubroker/monitoring")

    # Security monitoring configuration
    SECURITY_MONITORING_ENABLED = monitoring_config.get(
        "security_monitoring_enabled", True
    )
    SUSPICIOUS_LOGIN_THRESHOLD = monitoring_config.get("suspicious_login_threshold", 5)
    FAILED_LOGIN_ATTEMPT_LIMIT = monitoring_config.get("failed_login_attempt_limit", 10)
    ACCOUNT_LOCKOUT_DURATION = monitoring_config.get(
        "account_lockout_duration", 900
    )  # 15 minutes

    # Email alerts for security events from Vault
    SECURITY_EMAIL_RECIPIENTS = monitoring_config.get("security_email_recipients", [])

    # Prometheus integration
    PROMETHEUS_ENABLED = monitoring_config.get("prometheus_enabled", True)
    PROMETHEUS_PORT = monitoring_config.get("prometheus_port", 8001)
    PROMETHEUS_MULTIPROCESS_DIR = "/tmp/prometheus_multiproc_dir"

    # Logging configuration with enhanced security
    LOGGING = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "secure": {
                "format": "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
                "datefmt": "%d/%b/%Y %H:%M:%S",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "level": "INFO",
                "class": "logging.StreamHandler",
                "formatter": "json",
            },
            "file": {
                "level": "INFO",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": monitoring_config.get(
                    "log_file_path", "/var/log/gpubroker/django.log"
                ),
                "maxBytes": 1024 * 1024 * 50,  # 50MB
                "backupCount": 10,
                "formatter": "secure",
            },
            "security": {
                "level": "WARNING",
                "class": "logging.handlers.RotatingFileHandler",
                "filename": monitoring_config.get(
                    "security_log_file_path", "/var/log/gpubroker/security.log"
                ),
                "maxBytes": 1024 * 1024 * 20,  # 20MB
                "backupCount": 15,
                "formatter": "secure",
            },
            "prometheus": {
                "level": "INFO",
                "class": "prometheus_client.logging.MetricsHandler",
            },
        },
        "loggers": {
            "django": {
                "handlers": ["console", "file", "security", "prometheus"],
                "level": "WARNING",
                "propagate": True,
            },
            "gpubroker": {
                "handlers": ["console", "file", "security", "prometheus"],
                "level": "INFO",
                "propagate": True,
            },
            "django.security": {
                "handlers": ["console", "security"],
                "level": "WARNING",
                "propagate": False,
            },
            "apps.security": {
                "handlers": ["console", "security"],
                "level": "INFO",
                "propagate": False,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": "WARNING",
        },
    }

    # OpenTelemetry configuration
    OPENTELEMETRY_ENABLED = monitoring_config.get("opentelemetry_enabled", True)
    OTEL_SERVICE_NAME = "gpubroker-django"
    OTEL_RESOURCE_ATTRIBUTES = {
        "service.name": "gpubroker-django",
        "service.version": "1.0.0",
        "deployment.environment": "production",
    }
    OTEL_EXPORTER_OTLP_ENDPOINT = monitoring_config.get("otel_exporter_endpoint")
    OTEL_EXPORTER_OTLP_HEADERS = monitoring_config.get("otel_exporter_headers", {})

except Exception as e:
    raise ImproperlyConfigured(
        f"Failed to load monitoring configuration from Vault: {e}"
    )

# =============================================================================
# ENVIRONMENT VALIDATION - VAULT ONLY
# =============================================================================

# Validate critical Vault environment variables (not secrets)
REQUIRED_VAULT_VARS = ["VAULT_ADDR", "VAULT_ROLE_ID", "VAULT_SECRET_ID"]

for var in REQUIRED_VAULT_VARS:
    if not os.environ.get(var):
        raise ValueError(
            f"Required Vault environment variable {var} is not set in production"
        )

# =============================================================================
# PRODUCTION PERFORMANCE SETTINGS
# =============================================================================

# Django performance optimizations
USE_TZ = True
TIME_ZONE = "UTC"

# Session security settings
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Strict"
SESSION_SAVE_EVERY_REQUEST = True

# File upload security
FILE_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 5242880  # 5MB
DATA_UPLOAD_MAX_NUMBER_FIELDS = 1000

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# CSRF protection
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in ALLOWED_HOSTS]
CSRF_FAILURE_VIEW = "django.views.csrf.csrf_failure"

# Rate limiting (django-ratelimit)
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = "default"

# Health check configuration
HEALTH_CHECK_PATH = "/health/"
HEALTH_CHECK_TIMEOUT = 30

# Static files configuration (using whitenoise for production)
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"
STATIC_ROOT = "/app/staticfiles"
MEDIA_ROOT = "/app/media"

# Email backend for production
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"

# Set default permissions
DEFAULT_AUTO_FIELD = "id"

# =============================================================================
# VAULT CONNECTION HEALTH CHECK
# =============================================================================


def check_vault_health():
    """Verify Vault connectivity on startup."""
    try:
        vault.get_secret("gpubroker/health", "status")
        return True
    except Exception:
        return False


# Verify Vault is accessible on startup
if not check_vault_health():
    raise ImproperlyConfigured(
        "Vault is not accessible - cannot start production without secrets management"
    )

print("✅ Production configuration loaded successfully from Vault")

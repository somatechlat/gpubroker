"""
Django simplified settings for GPUBROKER project.

Uses simple configuration system that works with existing setup.
"""

from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# =============================================================================
# SIMPLIFIED CONFIGURATION SYSTEM
# =============================================================================
import sys

sys.path.append(str(BASE_DIR / "config"))

from simple_config import CONFIG

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
        "ENGINE": "django.db.backends.postgresql",
        "NAME": CONFIG.database.name,
        "USER": CONFIG.database.user,
        "PASSWORD": CONFIG.database.password,
        "HOST": CONFIG.database.host,
        "PORT": CONFIG.database.port,
        "OPTIONS": {
            "connect_timeout": CONFIG.database.connect_timeout,
        },
    }
}

# =============================================================================
# CACHING SETTINGS
# =============================================================================

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "unique-snowflake",
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

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# =============================================================================
# AUTHENTICATION
# =============================================================================

AUTH_USER_MODEL = "auth_app.User"

# Session configuration
SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"
SESSION_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True

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
# LOGGING SETTINGS
# =============================================================================

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG" if DEBUG else "INFO",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "DEBUG" if DEBUG else "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "gpubroker": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}

# =============================================================================
# SECURITY SETTINGS
# =============================================================================

# Security headers
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_SSL_REDIRECT = not DEBUG

# CSRF settings
CSRF_TRUSTED_ORIGINS = CONFIG.security.csrf_trusted_origins
CSRF_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_HTTPONLY = True

# =============================================================================
# DJANGO CHANNELS (WEBSOCKETS)
# =============================================================================

ASGI_APPLICATION = "gpubroker.asgi.application"

CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels.layers.InMemoryChannelLayer",
    },
}

# =============================================================================
# API SETTINGS
# =============================================================================

# Django Ninja API
API_PREFIX = CONFIG.app.api_prefix
API_VERSION = CONFIG.app.api_version

# =============================================================================
# DEVELOPMENT-SPECIFIC SETTINGS
# =============================================================================

if DEBUG:
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

# Application info
APP_INFO = {
    "NAME": CONFIG.app.name,
    "VERSION": CONFIG.app.version,
    "ENVIRONMENT": CONFIG.app.environment,
}

# PayPal configuration (simple version)
PAYPAL_CONFIG = {
    "CLIENT_ID_SANDBOX": CONFIG.external_services.paypal_client_id_sandbox or "",
    "CLIENT_SECRET_SANDBOX": CONFIG.external_services.paypal_client_secret_sandbox
    or "",
    "MODE": CONFIG.external_services.paypal_mode,
}

# Vault configuration
VAULT_CONFIG = {
    "ADDR": CONFIG.external_services.vault_addr,
    "TOKEN": CONFIG.external_services.vault_token or "",
    "TIMEOUT": CONFIG.external_services.vault_timeout,
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

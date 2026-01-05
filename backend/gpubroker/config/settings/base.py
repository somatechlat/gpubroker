"""
Django base settings for GPUBROKER project.

Common settings shared between all environments.
Follows Django 5 best practices.
"""
from pathlib import Path

import dj_database_url
import environ

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Initialize django-environ
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ['localhost', '127.0.0.1']),
    CORS_ALLOWED_ORIGINS=(list, ['http://localhost:3000']),
    GPUBROKER_MODE=(str, 'sandbox'),  # sandbox or live
)

# Read .env file if it exists
env_file = BASE_DIR / '.env'
if env_file.exists():
    environ.Env.read_env(str(env_file))

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env('DEBUG')

ALLOWED_HOSTS = env('ALLOWED_HOSTS')

# GPUBROKER Mode: sandbox or live
GPUBROKER_MODE = env('GPUBROKER_MODE')

# =============================================================================
# APPLICATION DEFINITION
# =============================================================================

INSTALLED_APPS = [
    # Django core
    'apps.core',  # Core Infrastructure (Apache Signals)
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third-party apps
    'corsheaders',
    'channels',
    'django_prometheus',
    
    # ---------------------------------------------------------------------
    # GPUBROKERADMIN - Control Plane
    # ---------------------------------------------------------------------
    'gpubrokeradmin',
    'gpubrokeradmin.apps.auth',
    'gpubrokeradmin.apps.subscriptions',
    'gpubrokeradmin.apps.pod_management',
    'gpubrokeradmin.apps.access_control',
    'gpubrokeradmin.apps.notifications',
    'gpubrokeradmin.apps.monitoring',
    
    # ---------------------------------------------------------------------
    # GPUBROKERPOD - Data Plane
    # ---------------------------------------------------------------------
    # GPUBROKERAPP - User-facing apps
    'gpubrokerpod.gpubrokerapp.apps.auth_app',
    'gpubrokerpod.gpubrokerapp.apps.providers',
    'gpubrokerpod.gpubrokerapp.apps.kpi',
    'gpubrokerpod.gpubrokerapp.apps.math_core',
    'gpubrokerpod.gpubrokerapp.apps.ai_assistant',
    'gpubrokerpod.gpubrokerapp.apps.websocket_gateway',
    
    # GPUBROKERAGENT - Agentic layer (ADMIN ONLY)
    'gpubrokerpod.gpubrokeragent.apps.agent_core',
    'gpubrokerpod.gpubrokeragent.apps.decisions',
    'gpubrokerpod.gpubrokeragent.apps.budgets',
    
    # POD Configuration (SANDBOX/LIVE modes)
    'gpubrokerpod.gpubrokerapp.apps.pod_config',
    
    # Billing & Subscriptions
    'gpubrokerpod.gpubrokerapp.apps.billing',
    
    # Dashboard
    'gpubrokerpod.gpubrokerapp.apps.dashboard',
    
    # Deployment (Configure Pod, Deploy, Activate)
    'gpubrokerpod.gpubrokerapp.apps.deployment',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'gpubrokerpod.gpubrokerapp.apps.auth_app.middleware.JWTAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / 'gpubrokeradmin' / 'templates',
        ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ASGI application for Channels support
ASGI_APPLICATION = 'config.asgi.application'
WSGI_APPLICATION = 'config.wsgi.application'

# =============================================================================
# DATABASE
# =============================================================================
DATABASE_URL = env('DATABASE_URL', default='postgresql://postgres:postgres@localhost:5432/gpubroker')
DATABASES = {
    'default': dj_database_url.parse(DATABASE_URL, conn_max_age=600)
}

# =============================================================================
# REDIS & CACHING
# =============================================================================
REDIS_URL = env('REDIS_URL', default='redis://localhost:6379/0')

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# =============================================================================
# APACHE KAFKA
# =============================================================================
KAFKA_BROKERS = env('KAFKA_BROKERS', default='kafka:9092')

# Channels layer configuration
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
        },
    },
}

# =============================================================================
# PASSWORD VALIDATION
# =============================================================================
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# Custom user model
AUTH_USER_MODEL = 'auth_app.User'

# =============================================================================
# INTERNATIONALIZATION
# =============================================================================
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

# =============================================================================
# STATIC FILES
# =============================================================================
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'gpubrokeradmin' / 'static',
]
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# =============================================================================
# CORS
# =============================================================================
CORS_ALLOWED_ORIGINS = env('CORS_ALLOWED_ORIGINS')
CORS_ALLOW_CREDENTIALS = True

# =============================================================================
# JWT CONFIGURATION
# =============================================================================
JWT_PRIVATE_KEY = env('JWT_PRIVATE_KEY', default='')
JWT_PUBLIC_KEY = env('JWT_PUBLIC_KEY', default='')
JWT_ALGORITHM = 'RS256'
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 15
JWT_REFRESH_TOKEN_EXPIRE_DAYS = 7

# =============================================================================
# EXTERNAL SERVICES
# =============================================================================
VAULT_ADDR = env('VAULT_ADDR', default='http://localhost:8200')
SOMA_AGENT_BASE = env('SOMA_AGENT_BASE', default='http://localhost:8080')

# AWS Configuration
AWS_REGION = env('AWS_REGION', default='us-east-1')
AWS_ACCOUNT_ID = env('AWS_ACCOUNT_ID', default='')

# Stripe Configuration (mode-dependent)
# Test keys for sandbox mode
STRIPE_SECRET_KEY_TEST = env('STRIPE_SECRET_KEY_TEST', default='')
STRIPE_PUBLISHABLE_KEY_TEST = env('STRIPE_PUBLISHABLE_KEY_TEST', default='')
# Live keys for production mode
STRIPE_SECRET_KEY_LIVE = env('STRIPE_SECRET_KEY_LIVE', default='')
STRIPE_PUBLISHABLE_KEY_LIVE = env('STRIPE_PUBLISHABLE_KEY_LIVE', default='')
# Webhook secret (same for both modes typically)
STRIPE_WEBHOOK_SECRET = env('STRIPE_WEBHOOK_SECRET', default='')
# Legacy single key (deprecated, use mode-specific keys)
STRIPE_SECRET_KEY = env('STRIPE_SECRET_KEY', default='')

# PayPal Configuration (mode-dependent)
# Sandbox credentials
PAYPAL_CLIENT_ID_SANDBOX = env('PAYPAL_CLIENT_ID_SANDBOX', default='')
PAYPAL_CLIENT_SECRET_SANDBOX = env('PAYPAL_CLIENT_SECRET_SANDBOX', default='')
# Live credentials
PAYPAL_CLIENT_ID_LIVE = env('PAYPAL_CLIENT_ID_LIVE', default='')
PAYPAL_CLIENT_SECRET_LIVE = env('PAYPAL_CLIENT_SECRET_LIVE', default='')
# Legacy single key (deprecated)
PAYPAL_CLIENT_ID = env('PAYPAL_CLIENT_ID', default='')
PAYPAL_CLIENT_SECRET = env('PAYPAL_CLIENT_SECRET', default='')


# =============================================================================
# MODE-AWARE CREDENTIAL HELPERS
# =============================================================================
def get_stripe_keys():
    """Return appropriate Stripe keys based on GPUBROKER_MODE"""
    if GPUBROKER_MODE == 'live':
        return {
            'secret_key': STRIPE_SECRET_KEY_LIVE or STRIPE_SECRET_KEY,
            'publishable_key': STRIPE_PUBLISHABLE_KEY_LIVE,
        }
    return {
        'secret_key': STRIPE_SECRET_KEY_TEST or STRIPE_SECRET_KEY,
        'publishable_key': STRIPE_PUBLISHABLE_KEY_TEST,
    }


def get_paypal_config():
    """Return appropriate PayPal config based on GPUBROKER_MODE"""
    if GPUBROKER_MODE == 'live':
        return {
            'client_id': PAYPAL_CLIENT_ID_LIVE or PAYPAL_CLIENT_ID,
            'client_secret': PAYPAL_CLIENT_SECRET_LIVE or PAYPAL_CLIENT_SECRET,
            'mode': 'live',
            'api_base': 'https://api-m.paypal.com',
        }
    return {
        'client_id': PAYPAL_CLIENT_ID_SANDBOX or PAYPAL_CLIENT_ID,
        'client_secret': PAYPAL_CLIENT_SECRET_SANDBOX or PAYPAL_CLIENT_SECRET,
        'mode': 'sandbox',
        'api_base': 'https://api-m.sandbox.paypal.com',
    }

# =============================================================================
# GPUBROKER DOMAIN CONFIGURATION (CENTRALIZED - CHANGE HERE ONLY)
# =============================================================================
# Base domain for the entire GPUBROKER platform
GPUBROKER_DOMAIN = env('GPUBROKER_DOMAIN', default='gpubroker.site')

# Derived URLs (use these in code, not hardcoded domains)
GPUBROKER_BASE_URL = env('GPUBROKER_BASE_URL', default=f'https://{GPUBROKER_DOMAIN}')
GPUBROKER_ADMIN_URL = env('GPUBROKER_ADMIN_URL', default=f'https://admin.{GPUBROKER_DOMAIN}')
GPUBROKER_API_URL = env('GPUBROKER_API_URL', default=f'https://api.{GPUBROKER_DOMAIN}')
GPUBROKER_APP_URL = env('GPUBROKER_APP_URL', default=f'https://app.{GPUBROKER_DOMAIN}')

# Email addresses (derived from domain)
GPUBROKER_SUPPORT_EMAIL = f'support@{GPUBROKER_DOMAIN}'
GPUBROKER_BILLING_EMAIL = f'billing@{GPUBROKER_DOMAIN}'
GPUBROKER_NOREPLY_EMAIL = f'noreply@{GPUBROKER_DOMAIN}'

# =============================================================================
# GPUBROKER REGIONAL CONFIGURATION
# =============================================================================
# Default region for geo-detection fallback (ISO 3166-1 alpha-2)
GPUBROKER_DEFAULT_REGION = env('GPUBROKER_DEFAULT_REGION', default='US')

# Deployment region - determines which country-specific validations apply
# Options: 'GLOBAL', 'LATAM', 'EC', 'US', 'EU', etc.
GPUBROKER_DEPLOYMENT_REGION = env('GPUBROKER_DEPLOYMENT_REGION', default='GLOBAL')

# Force specific country validation (for testing or single-country deployments)
# Set to country code (e.g., 'EC') to always require that country's validation
# Set to empty string for geo-detection
GPUBROKER_FORCE_COUNTRY = env('GPUBROKER_FORCE_COUNTRY', default='')

# =============================================================================
# LOGGING
# =============================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'json': {
            '()': 'pythonjsonlogger.jsonlogger.JsonFormatter',
            'format': '%(asctime)s %(levelname)s %(name)s %(message)s',
        },
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': env('DJANGO_LOG_LEVEL', default='INFO'),
            'propagate': False,
        },
        'gpubroker': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'gpubrokeradmin': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'gpubrokerpod': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# =============================================================================
# RATE LIMITING
# =============================================================================
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_KEY_PREFIX = 'rl:'

# Rate limits per plan (requests per second)
RATE_LIMITS = {
    'free': 10,
    'pro': 100,
    'enterprise': 1000,
}

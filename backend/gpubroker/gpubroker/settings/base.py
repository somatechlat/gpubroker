"""
GPUBroker Base Settings

Shared settings for all environments.
"""

from pathlib import Path

# Build paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Application definition
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    # POD SaaS Architecture - gpubrokerapp apps
    "gpubrokerpod.gpubrokerapp.apps.auth_app",
    "gpubrokerpod.gpubrokerapp.apps.providers",
    "gpubrokerpod.gpubrokerapp.apps.billing",
    "gpubrokerpod.gpubrokerapp.apps.deployment",
    "gpubrokerpod.gpubrokerapp.apps.dashboard",
    "gpubrokerpod.gpubrokerapp.apps.websocket_gateway",
    "gpubrokerpod.gpubrokerapp.apps.pod_config",
    "gpubrokerpod.gpubrokerapp.apps.kpi",
    "gpubrokerpod.gpubrokerapp.apps.ai_assistant",
    "gpubrokerpod.gpubrokerapp.apps.math_core",
    # Shared utilities
    "shared",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "gpubroker.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(BASE_DIR / "templates")],
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

# Internationalization
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# Authentication
AUTH_USER_MODEL = "auth_app.User"

# Static and media files
STATIC_URL = "/static/"
MEDIA_URL = "/media/"

# Default settings
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Enhanced security settings
SECURE_SSL_REDIRECT = False  # Will be overridden in production
SESSION_COOKIE_SECURE = False  # Will be overridden in production
CSRF_COOKIE_SECURE = False  # Will be overridden in production

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

# Security middleware configuration
SECURITY_MIDDLEWARE_ENABLED = True
RATE_LIMITING_ENABLED = True
INPUT_VALIDATION_ENABLED = True
SECURITY_MONITORING_ENABLED = True

# Security configuration
SECURITY_EMAIL_RECIPIENTS = []  # Configure in production
MAX_LOGIN_ATTEMPTS = 5
ACCOUNT_LOCKOUT_TIME = 900  # 15 minutes
JWT_ACCESS_TOKEN_LIFETIME = 900  # 15 minutes
JWT_REFRESH_TOKEN_LIFETIME = 86400  # 24 hours

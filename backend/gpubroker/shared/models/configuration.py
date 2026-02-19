"""
Django ORM-based Configuration Management
Following Django standards - ALL configuration stored in database
NO hardcoded secrets, NO environment variables for secrets
"""

import json

from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.db import models
from encrypted_model_fields.fields import EncryptedCharField, EncryptedTextField


class ConfigurationManager(models.Manager):
    """Manager for configuration with caching."""

    def get_value(self, key, default=None, decrypt=False):
        """Get configuration value with caching."""
        cache_key = f"config:{key}"
        value = cache.get(cache_key)

        if value is None:
            try:
                config = self.get(key=key, is_active=True)
                value = config.get_value(decrypt=decrypt)
                cache.set(cache_key, value, timeout=300)  # 5 minutes
            except Configuration.DoesNotExist:
                value = default

        return value

    def set_value(self, key, value, is_secret=False, description=""):
        """Set configuration value."""
        config, created = self.update_or_create(
            key=key,
            defaults={
                "value": value if not is_secret else None,
                "encrypted_value": value if is_secret else None,
                "is_secret": is_secret,
                "description": description,
                "is_active": True,
            },
        )

        # Invalidate cache
        cache.delete(f"config:{key}")

        return config


class Configuration(models.Model):
    """
    Centralized configuration storage following Django ORM standards.

    ALL application configuration stored here:
    - Database credentials (encrypted)
    - API keys (encrypted)
    - Feature flags
    - System settings
    - Service endpoints

    NO environment variables for secrets!
    """

    # Configuration categories
    CATEGORY_DATABASE = "database"
    CATEGORY_CACHE = "cache"
    CATEGORY_SECURITY = "security"
    CATEGORY_API = "api"
    CATEGORY_FEATURE = "feature"
    CATEGORY_SERVICE = "service"
    CATEGORY_MONITORING = "monitoring"

    CATEGORY_CHOICES = [
        (CATEGORY_DATABASE, "Database"),
        (CATEGORY_CACHE, "Cache"),
        (CATEGORY_SECURITY, "Security"),
        (CATEGORY_API, "API"),
        (CATEGORY_FEATURE, "Feature Flag"),
        (CATEGORY_SERVICE, "External Service"),
        (CATEGORY_MONITORING, "Monitoring"),
    ]

    key = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="Configuration key (e.g., 'database.postgres.host')",
    )

    category = models.CharField(
        max_length=50,
        choices=CATEGORY_CHOICES,
        default=CATEGORY_FEATURE,
        db_index=True,
        help_text="Configuration category",
    )

    value = models.TextField(
        null=True, blank=True, help_text="Plain text value (for non-sensitive data)"
    )

    encrypted_value = EncryptedTextField(
        null=True,
        blank=True,
        help_text="Encrypted value (for sensitive data like passwords, API keys)",
    )

    is_secret = models.BooleanField(
        default=False, help_text="Whether this is a secret (uses encrypted_value)"
    )

    description = models.TextField(
        blank=True, help_text="Human-readable description of this configuration"
    )

    is_active = models.BooleanField(
        default=True, db_index=True, help_text="Whether this configuration is active"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = ConfigurationManager()

    class Meta:
        db_table = "configuration"
        verbose_name = "Configuration"
        verbose_name_plural = "Configurations"
        ordering = ["category", "key"]
        indexes = [
            models.Index(fields=["key", "is_active"]),
            models.Index(fields=["category", "is_active"]),
        ]

    def __str__(self):
        return f"{self.key} ({self.category})"

    def get_value(self, decrypt=False):
        """Get the configuration value."""
        if self.is_secret:
            if decrypt:
                return self.encrypted_value
            return "***ENCRYPTED***"

        # Try to parse as JSON for complex types
        try:
            return json.loads(self.value)
        except (json.JSONDecodeError, TypeError):
            return self.value

    def set_value(self, value, is_secret=False):
        """Set the configuration value."""
        self.is_secret = is_secret

        if is_secret:
            self.encrypted_value = value
            self.value = None
        else:
            # Store complex types as JSON
            if isinstance(value, (dict, list)):
                self.value = json.dumps(value)
            else:
                self.value = str(value)
            self.encrypted_value = None

        self.save()

        # Invalidate cache
        cache.delete(f"config:{self.key}")

    def clean(self):
        """Validate configuration."""
        if self.is_secret and not self.encrypted_value:
            raise ValidationError("Secret configurations must have encrypted_value")

        if not self.is_secret and not self.value:
            raise ValidationError("Non-secret configurations must have value")


class DatabaseConfiguration(models.Model):
    """
    Database connection configuration stored in Django ORM.
    NO environment variables for database credentials!
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Database connection name (e.g., 'default', 'analytics')",
    )

    engine = models.CharField(
        max_length=200,
        default="django.db.backends.postgresql",
        help_text="Django database engine",
    )

    host = models.CharField(max_length=255)
    port = models.IntegerField(default=5432)
    database = models.CharField(max_length=255)
    username = models.CharField(max_length=255)

    password = EncryptedCharField(
        max_length=255, help_text="Encrypted database password"
    )

    # Connection options
    conn_max_age = models.IntegerField(
        default=60, help_text="Connection max age in seconds"
    )

    ssl_mode = models.CharField(
        max_length=50,
        default="require",
        help_text="SSL mode (disable, allow, prefer, require, verify-ca, verify-full)",
    )

    connect_timeout = models.IntegerField(
        default=60, help_text="Connection timeout in seconds"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "database_configuration"
        verbose_name = "Database Configuration"
        verbose_name_plural = "Database Configurations"

    def __str__(self):
        return f"{self.name} ({self.host}:{self.port}/{self.database})"

    def get_django_config(self):
        """Get Django DATABASES configuration dict."""
        return {
            "ENGINE": self.engine,
            "NAME": self.database,
            "USER": self.username,
            "PASSWORD": self.password,
            "HOST": self.host,
            "PORT": self.port,
            "CONN_MAX_AGE": self.conn_max_age,
            "OPTIONS": {
                "sslmode": self.ssl_mode,
                "connect_timeout": self.connect_timeout,
            },
        }


class CacheConfiguration(models.Model):
    """
    Cache configuration stored in Django ORM.
    NO environment variables for cache credentials!
    """

    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Cache connection name (e.g., 'default', 'sessions')",
    )

    backend = models.CharField(
        max_length=200,
        default="django_redis.cache.RedisCache",
        help_text="Django cache backend",
    )

    host = models.CharField(max_length=255)
    port = models.IntegerField(default=6379)
    db = models.IntegerField(default=0)

    password = EncryptedCharField(
        max_length=255, null=True, blank=True, help_text="Encrypted Redis password"
    )

    # Connection options
    max_connections = models.IntegerField(default=50)
    socket_timeout = models.IntegerField(default=5)
    socket_connect_timeout = models.IntegerField(default=5)

    key_prefix = models.CharField(
        max_length=100, default="gpubroker", help_text="Cache key prefix"
    )

    timeout = models.IntegerField(
        default=300, help_text="Default cache timeout in seconds"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "cache_configuration"
        verbose_name = "Cache Configuration"
        verbose_name_plural = "Cache Configurations"

    def __str__(self):
        return f"{self.name} ({self.host}:{self.port}/{self.db})"

    def get_django_config(self):
        """Get Django CACHES configuration dict."""
        location = (
            f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
            if self.password
            else f"redis://{self.host}:{self.port}/{self.db}"
        )

        return {
            "BACKEND": self.backend,
            "LOCATION": location,
            "OPTIONS": {
                "CLIENT_CLASS": "django_redis.client.DefaultClient",
                "CONNECTION_POOL_KWARGS": {
                    "max_connections": self.max_connections,
                    "retry_on_timeout": True,
                    "socket_connect_timeout": self.socket_connect_timeout,
                    "socket_timeout": self.socket_timeout,
                },
            },
            "KEY_PREFIX": self.key_prefix,
            "TIMEOUT": self.timeout,
        }


class ServiceConfiguration(models.Model):
    """
    External service configuration stored in Django ORM.
    NO environment variables for API keys!
    """

    SERVICE_STRIPE = "stripe"
    SERVICE_AWS = "aws"
    SERVICE_SENDGRID = "sendgrid"
    SERVICE_SENTRY = "sentry"
    SERVICE_PROMETHEUS = "prometheus"

    SERVICE_CHOICES = [
        (SERVICE_STRIPE, "Stripe"),
        (SERVICE_AWS, "AWS"),
        (SERVICE_SENDGRID, "SendGrid"),
        (SERVICE_SENTRY, "Sentry"),
        (SERVICE_PROMETHEUS, "Prometheus"),
    ]

    service_name = models.CharField(
        max_length=100,
        choices=SERVICE_CHOICES,
        unique=True,
        help_text="External service name",
    )

    api_key = EncryptedTextField(help_text="Encrypted API key")

    api_secret = EncryptedTextField(
        null=True, blank=True, help_text="Encrypted API secret (if required)"
    )

    endpoint_url = models.URLField(
        null=True, blank=True, help_text="Service endpoint URL"
    )

    config_json = models.JSONField(
        default=dict, help_text="Additional service-specific configuration"
    )

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "service_configuration"
        verbose_name = "Service Configuration"
        verbose_name_plural = "Service Configurations"

    def __str__(self):
        return f"{self.get_service_name_display()}"

"""
Auth App Models - User authentication and tenant management.

Maps to existing PostgreSQL tables:
- users
- user_sessions
- api_keys
- audit_log

Uses managed=False to prevent Django from altering existing schema.
"""

import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.contrib.postgres.fields import ArrayField
from django.db import models


class UserManager(BaseUserManager):
    """Custom user manager for email-based authentication."""

    def create_user(self, email, password=None, **extra_fields):
        """Create and save a regular user."""
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """Create and save a superuser."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom User model using email as the unique identifier.

    Maps to existing 'users' table in PostgreSQL.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, max_length=255)
    password_hash = models.CharField(max_length=255, db_column="password_hash")
    full_name = models.CharField(max_length=255)
    organization = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = models.DateTimeField(blank=True, null=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        db_table = "users"
        managed = False  # Don't alter existing schema
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email

    @property
    def password(self):
        """Return password_hash for Django compatibility."""
        return self.password_hash

    @password.setter
    def password(self, value):
        """Set password_hash for Django compatibility."""
        self.password_hash = value

    def set_password(self, raw_password):
        """Hash and set the password using Argon2."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
        self.password_hash = pwd_context.hash(raw_password)
        self._password = raw_password

    def check_password(self, raw_password):
        """Verify password against stored hash."""
        from passlib.context import CryptContext

        pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")
        return pwd_context.verify(raw_password, self.password_hash)


class UserSession(models.Model):
    """
    User session tracking for JWT refresh tokens.

    Maps to existing 'user_sessions' table.
    """

    jti = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sessions")
    refresh_token_hash = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)

    class Meta:
        db_table = "user_sessions"
        managed = False
        verbose_name = "User Session"
        verbose_name_plural = "User Sessions"

    def __str__(self):
        return f"Session {self.jti} for {self.user.email}"

    @property
    def is_valid(self):
        """Check if session is still valid."""
        from django.utils import timezone

        return self.revoked_at is None and self.expires_at > timezone.now()


class APIKey(models.Model):
    """
    API key management for programmatic access.

    Maps to existing 'api_keys' table.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="api_keys")
    key_hash = models.CharField(max_length=255)
    name = models.CharField(max_length=100)
    scopes = ArrayField(models.CharField(max_length=50), default=list, blank=True)
    last_used_at = models.DateTimeField(blank=True, null=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    revoked_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "api_keys"
        managed = False
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"

    def __str__(self):
        return f"{self.name} ({self.user.email})"

    @property
    def is_valid(self):
        """Check if API key is still valid."""
        from django.utils import timezone

        if self.revoked_at is not None:
            return False
        if self.expires_at and self.expires_at < timezone.now():
            return False
        return True


class AuditLog(models.Model):
    """
    Immutable audit log with hash chain for compliance.

    Maps to existing 'audit_log' table.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    event_type = models.CharField(max_length=50)
    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    resource_type = models.CharField(max_length=50, blank=True, null=True)
    resource_id = models.UUIDField(blank=True, null=True)
    event_data = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    previous_hash = models.CharField(max_length=64, blank=True, null=True)
    current_hash = models.CharField(max_length=64, blank=True, null=True)

    class Meta:
        db_table = "audit_log"
        managed = False
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.event_type} at {self.created_at}"


class UserPreference(models.Model):
    """
    User preferences and settings.

    Maps to existing 'user_preferences' table.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="preferences")
    preference_key = models.CharField(max_length=100)
    preference_value = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "user_preferences"
        managed = False
        unique_together = [["user", "preference_key"]]
        verbose_name = "User Preference"
        verbose_name_plural = "User Preferences"

    def __str__(self):
        return f"{self.user.email}: {self.preference_key}"


class SavedSearch(models.Model):
    """
    Saved search filters and alerts.

    Maps to existing 'saved_searches' table.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="saved_searches"
    )
    name = models.CharField(max_length=100)
    search_filters = models.JSONField()
    is_alert = models.BooleanField(default=False)
    alert_threshold = models.DecimalField(
        max_digits=8, decimal_places=4, blank=True, null=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "saved_searches"
        managed = False
        verbose_name = "Saved Search"
        verbose_name_plural = "Saved Searches"

    def __str__(self):
        return f"{self.name} ({self.user.email})"

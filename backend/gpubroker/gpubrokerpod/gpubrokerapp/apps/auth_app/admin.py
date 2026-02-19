"""
Auth App Admin Configuration.

Django admin interface for User and AuditLog models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import APIKey, AuditLog, SavedSearch, User, UserPreference, UserSession


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """Admin configuration for User model."""

    list_display = (
        "email",
        "full_name",
        "organization",
        "is_active",
        "is_staff",
        "created_at",
    )
    list_filter = ("is_active", "is_staff", "is_superuser", "is_verified")
    search_fields = ("email", "full_name", "organization")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("email", "password_hash")}),
        ("Personal Info", {"fields": ("full_name", "organization")}),
        (
            "Permissions",
            {
                "fields": ("is_active", "is_verified", "is_staff", "is_superuser"),
            },
        ),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "full_name", "password_hash"),
            },
        ),
    )

    readonly_fields = ("created_at", "updated_at", "last_login")


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """Admin configuration for AuditLog model."""

    list_display = (
        "event_type",
        "user",
        "resource_type",
        "resource_id",
        "ip_address",
        "created_at",
    )
    list_filter = ("event_type", "resource_type", "created_at")
    search_fields = ("user__email", "resource_id", "ip_address")
    ordering = ("-created_at",)
    date_hierarchy = "created_at"

    fieldsets = (
        (None, {"fields": ("user", "event_type")}),
        ("Resource", {"fields": ("resource_type", "resource_id")}),
        ("Details", {"fields": ("event_data", "ip_address", "user_agent")}),
        ("Hash Chain", {"fields": ("previous_hash", "current_hash")}),
        ("Timestamp", {"fields": ("created_at",)}),
    )

    readonly_fields = ("created_at", "previous_hash", "current_hash")

    def has_add_permission(self, request):
        """Audit logs should not be created manually."""
        return False

    def has_change_permission(self, request, obj=None):
        """Audit logs should not be modified."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Audit logs should not be deleted (except by superuser)."""
        return request.user.is_superuser


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    """Admin configuration for UserSession model."""

    list_display = ("jti", "user", "expires_at", "created_at", "revoked_at")
    list_filter = ("created_at", "revoked_at")
    search_fields = ("user__email", "ip_address")
    ordering = ("-created_at",)

    readonly_fields = ("jti", "created_at", "refresh_token_hash")


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    """Admin configuration for APIKey model."""

    list_display = (
        "name",
        "user",
        "last_used_at",
        "expires_at",
        "created_at",
        "revoked_at",
    )
    list_filter = ("created_at", "revoked_at")
    search_fields = ("name", "user__email")
    ordering = ("-created_at",)

    readonly_fields = ("id", "key_hash", "created_at")


@admin.register(UserPreference)
class UserPreferenceAdmin(admin.ModelAdmin):
    """Admin configuration for UserPreference model."""

    list_display = ("user", "preference_key", "updated_at")
    list_filter = ("preference_key",)
    search_fields = ("user__email", "preference_key")
    ordering = ("-updated_at",)


@admin.register(SavedSearch)
class SavedSearchAdmin(admin.ModelAdmin):
    """Admin configuration for SavedSearch model."""

    list_display = ("name", "user", "is_alert", "created_at", "updated_at")
    list_filter = ("is_alert", "created_at")
    search_fields = ("name", "user__email")
    ordering = ("-created_at",)

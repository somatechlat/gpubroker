"""
Deployment Admin.

Django admin configuration for deployment models.
"""

from django.contrib import admin

from .models import PodDeploymentConfig, PodDeploymentLog, ProviderLimits


@admin.register(PodDeploymentConfig)
class PodDeploymentConfigAdmin(admin.ModelAdmin):
    """Admin for PodDeploymentConfig."""

    list_display = [
        "name",
        "status",
        "gpu_type",
        "gpu_count",
        "provider",
        "region",
        "estimated_price_per_hour",
        "is_valid",
        "created_at",
    ]
    list_filter = [
        "status",
        "provider",
        "gpu_type",
        "region",
        "is_valid",
        "spot_instance",
    ]
    search_fields = ["name", "user_email", "gpu_type", "provider"]
    readonly_fields = [
        "id",
        "created_at",
        "updated_at",
        "deployment_started_at",
        "deployment_completed_at",
    ]

    fieldsets = (
        (
            "Basic Info",
            {
                "fields": (
                    "id",
                    "name",
                    "description",
                    "status",
                    "user_id",
                    "user_email",
                )
            },
        ),
        (
            "GPU Configuration",
            {"fields": ("gpu_type", "gpu_model", "gpu_count", "gpu_memory_gb")},
        ),
        (
            "Provider",
            {"fields": ("provider_selection_mode", "provider", "provider_offer_id")},
        ),
        (
            "Resources",
            {
                "fields": (
                    "vcpus",
                    "ram_gb",
                    "storage_gb",
                    "storage_type",
                    "network_speed_gbps",
                    "public_ip",
                )
            },
        ),
        ("Region", {"fields": ("region", "availability_zone")}),
        (
            "Pricing",
            {
                "fields": (
                    "spot_instance",
                    "max_spot_price",
                    "estimated_price_per_hour",
                    "estimated_price_per_day",
                    "estimated_price_per_month",
                    "currency",
                )
            },
        ),
        (
            "Validation",
            {"fields": ("is_valid", "validation_errors", "provider_limits")},
        ),
        (
            "Deployment",
            {
                "fields": (
                    "deployment_id",
                    "deployment_started_at",
                    "deployment_completed_at",
                    "activation_token",
                    "activation_token_expires_at",
                    "activated_at",
                )
            },
        ),
        (
            "Runtime",
            {
                "fields": (
                    "started_at",
                    "stopped_at",
                    "total_runtime_hours",
                    "total_cost",
                )
            },
        ),
        ("Connection", {"fields": ("connection_details",)}),
        ("Metadata", {"fields": ("tags", "metadata", "created_at", "updated_at")}),
    )


@admin.register(PodDeploymentLog)
class PodDeploymentLogAdmin(admin.ModelAdmin):
    """Admin for PodDeploymentLog."""

    list_display = [
        "deployment",
        "event_type",
        "message",
        "old_status",
        "new_status",
        "created_at",
    ]
    list_filter = ["event_type", "created_at"]
    search_fields = ["deployment__name", "message"]
    readonly_fields = ["id", "created_at"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(ProviderLimits)
class ProviderLimitsAdmin(admin.ModelAdmin):
    """Admin for ProviderLimits."""

    list_display = [
        "provider",
        "gpu_type",
        "max_gpu_count",
        "max_vcpus",
        "max_ram_gb",
        "base_price_per_hour",
        "spot_available",
        "last_updated",
    ]
    list_filter = ["provider", "spot_available"]
    search_fields = ["provider", "gpu_type"]
    readonly_fields = ["id", "last_updated"]

    fieldsets = (
        ("Provider & GPU", {"fields": ("id", "provider", "gpu_type")}),
        ("GPU Limits", {"fields": ("min_gpu_count", "max_gpu_count")}),
        ("CPU Limits", {"fields": ("min_vcpus", "max_vcpus", "vcpu_increments")}),
        ("RAM Limits", {"fields": ("min_ram_gb", "max_ram_gb", "ram_increments_gb")}),
        (
            "Storage Limits",
            {
                "fields": (
                    "min_storage_gb",
                    "max_storage_gb",
                    "storage_increments_gb",
                    "supported_storage_types",
                )
            },
        ),
        ("Rental Limits", {"fields": ("min_rental_hours", "max_rental_hours")}),
        (
            "Pricing",
            {
                "fields": (
                    "base_price_per_hour",
                    "cpu_price_per_hour",
                    "ram_price_per_gb_hour",
                    "storage_price_per_gb_hour",
                )
            },
        ),
        ("Availability", {"fields": ("regions", "spot_available")}),
        ("Metadata", {"fields": ("last_updated",)}),
    )

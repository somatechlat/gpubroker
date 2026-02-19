"""
Providers App Admin Configuration.

Django admin interface for Provider, GPUOffer, and PriceHistory models.
"""

from django.contrib import admin

from .models import (
    GPUOffer,
    KPICalculation,
    PriceHistory,
    Provider,
    ProviderHealthCheck,
)


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    """Admin configuration for Provider model."""

    list_display = ("name", "display_name", "status", "reliability_score", "created_at")
    list_filter = ("status",)
    search_fields = ("name", "display_name")
    ordering = ("display_name",)

    fieldsets = (
        (None, {"fields": ("name", "display_name")}),
        ("URLs", {"fields": ("website_url", "api_base_url", "documentation_url")}),
        ("Configuration", {"fields": ("supported_regions", "compliance_tags")}),
        ("Status", {"fields": ("status", "reliability_score")}),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )

    readonly_fields = ("created_at", "updated_at")


@admin.register(GPUOffer)
class GPUOfferAdmin(admin.ModelAdmin):
    """Admin configuration for GPUOffer model."""

    list_display = (
        "gpu_type",
        "provider",
        "price_per_hour",
        "gpu_memory_gb",
        "region",
        "availability_status",
        "updated_at",
    )
    list_filter = ("provider", "gpu_type", "region", "availability_status")
    search_fields = ("gpu_type", "provider__name", "region", "external_id")
    ordering = ("price_per_hour",)

    fieldsets = (
        (None, {"fields": ("provider", "external_id", "name", "gpu_type")}),
        (
            "Specifications",
            {
                "fields": (
                    "gpu_memory_gb",
                    "cpu_cores",
                    "ram_gb",
                    "storage_gb",
                    "storage_type",
                )
            },
        ),
        (
            "Pricing",
            {"fields": ("price_per_hour", "currency", "spot_pricing", "preemptible")},
        ),
        ("Location", {"fields": ("region", "availability_zone")}),
        (
            "Availability",
            {"fields": ("availability_status", "min_rental_time", "max_rental_time")},
        ),
        ("Performance", {"fields": ("sla_uptime", "network_speed_gbps")}),
        ("Compliance", {"fields": ("compliance_tags",)}),
        ("Timestamps", {"fields": ("created_at", "updated_at", "last_seen_at")}),
    )

    readonly_fields = ("created_at", "updated_at", "last_seen_at")
    list_per_page = 50

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("provider")


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    """Admin configuration for PriceHistory model."""

    list_display = ("offer", "price_per_hour", "availability_status", "recorded_at")
    list_filter = ("offer__provider", "offer__gpu_type", "recorded_at")
    search_fields = ("offer__gpu_type", "offer__provider__name")
    ordering = ("-recorded_at",)
    date_hierarchy = "recorded_at"

    fieldsets = (
        (None, {"fields": ("offer",)}),
        ("Pricing", {"fields": ("price_per_hour", "availability_status")}),
        ("Timestamp", {"fields": ("recorded_at",)}),
    )

    readonly_fields = ("recorded_at",)
    list_per_page = 100

    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related("offer", "offer__provider")

    def has_add_permission(self, request):
        """Price history is recorded automatically."""
        return False

    def has_change_permission(self, request, obj=None):
        """Price history should not be modified."""
        return False


@admin.register(KPICalculation)
class KPICalculationAdmin(admin.ModelAdmin):
    """Admin configuration for KPICalculation model."""

    list_display = ("offer", "calculation_type", "value", "calculated_at")
    list_filter = ("calculation_type", "calculated_at")
    search_fields = ("offer__gpu_type", "offer__provider__name")
    ordering = ("-calculated_at",)

    readonly_fields = ("calculated_at",)

    def has_add_permission(self, request):
        """KPI calculations are computed automatically."""
        return False

    def has_change_permission(self, request, obj=None):
        """KPI calculations should not be modified."""
        return False


@admin.register(ProviderHealthCheck)
class ProviderHealthCheckAdmin(admin.ModelAdmin):
    """Admin configuration for ProviderHealthCheck model."""

    list_display = ("provider", "status", "response_time_ms", "checked_at")
    list_filter = ("status", "provider", "checked_at")
    search_fields = ("provider__name", "error_message")
    ordering = ("-checked_at",)
    date_hierarchy = "checked_at"

    readonly_fields = ("checked_at",)

    def has_add_permission(self, request):
        """Health checks are recorded automatically."""
        return False

    def has_change_permission(self, request, obj=None):
        """Health checks should not be modified."""
        return False

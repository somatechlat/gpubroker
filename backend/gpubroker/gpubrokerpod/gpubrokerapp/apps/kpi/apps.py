"""KPI App configuration - GPUBROKERAPP."""

from django.apps import AppConfig


class KpiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gpubrokerpod.gpubrokerapp.apps.kpi"
    label = "kpi"
    verbose_name = "KPI Analytics"

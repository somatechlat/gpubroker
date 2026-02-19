"""Math Core App configuration - GPUBROKERAPP."""

from django.apps import AppConfig


class MathCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gpubrokerpod.gpubrokerapp.apps.math_core"
    label = "math_core"
    verbose_name = "Math Core"

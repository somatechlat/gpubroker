"""Math Core App configuration."""
from django.apps import AppConfig


class MathCoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.math_core'
    verbose_name = 'Math Core'

"""Auth App configuration - GPUBROKERAPP."""

from django.apps import AppConfig


class AuthAppConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gpubrokerpod.gpubrokerapp.apps.auth_app"
    label = "auth_app"
    verbose_name = "Authentication"

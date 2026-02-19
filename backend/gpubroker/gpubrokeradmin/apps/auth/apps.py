"""
GPUBROKER Admin Authentication App Configuration
"""

from django.apps import AppConfig


class AuthConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gpubrokeradmin.apps.auth"
    label = "gpubrokeradmin_auth"
    verbose_name = "GPUBROKER Admin Authentication"

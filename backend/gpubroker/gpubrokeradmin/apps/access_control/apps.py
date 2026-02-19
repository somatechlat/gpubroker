"""Access Control App configuration - GPUBROKERADMIN Control Plane."""
from django.apps import AppConfig


class AccessControlConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gpubrokeradmin.apps.access_control'
    label = 'access_control'
    verbose_name = 'Access Control'

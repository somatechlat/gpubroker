"""Pod Management App configuration - GPUBROKERADMIN Control Plane."""
from django.apps import AppConfig


class PodManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gpubrokeradmin.apps.pod_management'
    label = 'pod_management'
    verbose_name = 'POD Management'

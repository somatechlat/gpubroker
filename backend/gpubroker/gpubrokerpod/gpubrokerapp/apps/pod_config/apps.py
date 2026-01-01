"""
POD Configuration App Configuration.
"""
from django.apps import AppConfig


class PodConfigConfig(AppConfig):
    """Configuration for the POD Config app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gpubrokerpod.gpubrokerapp.apps.pod_config'
    label = 'pod_config'
    verbose_name = 'POD Configuration'
    
    def ready(self):
        """Initialize app when Django starts."""
        pass

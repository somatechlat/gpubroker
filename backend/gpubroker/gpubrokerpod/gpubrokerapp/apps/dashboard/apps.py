"""Dashboard app configuration."""
from django.apps import AppConfig


class DashboardConfig(AppConfig):
    """Dashboard app config."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gpubrokerpod.gpubrokerapp.apps.dashboard'
    label = 'dashboard'
    verbose_name = 'Dashboard'

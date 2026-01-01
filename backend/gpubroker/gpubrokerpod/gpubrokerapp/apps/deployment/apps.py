"""
Deployment App Configuration.
"""
from django.apps import AppConfig


class DeploymentConfig(AppConfig):
    """Configuration for the Deployment app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gpubrokerpod.gpubrokerapp.apps.deployment'
    label = 'deployment'
    verbose_name = 'GPU Pod Deployment'

"""Providers App configuration - GPUBROKERAPP."""
from django.apps import AppConfig


class ProvidersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gpubrokerpod.gpubrokerapp.apps.providers'
    label = 'providers'
    verbose_name = 'GPU Providers'

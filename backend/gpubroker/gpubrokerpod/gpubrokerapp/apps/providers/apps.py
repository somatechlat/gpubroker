"""Providers App configuration - GPUBROKERAPP."""
from django.apps import AppConfig


class ProvidersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gpubrokerpod.gpubrokerapp.apps.providers'
    label = 'providers'
    verbose_name = 'GPU Providers'

    def ready(self):
        """Load signals when the app is ready."""
        try:
            from . import signals  # noqa: F401
        except ImportError as e:
            # Signals are optional - don't fail if they can't be loaded
            import logging
            logger = logging.getLogger(__name__)
            logger.debug(f"Signals not loaded: {e}")


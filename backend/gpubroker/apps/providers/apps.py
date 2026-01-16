"""Providers App configuration."""

from django.apps import AppConfig

from .common.messages import get_message


class ProvidersConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.providers"
    verbose_name = "GPU Providers"

    def ready(self):
        """
        Called when the app is ready.
        Can be used to start background services if needed.

        According to Django docs: https://docs.djangoproject.com/en/5.0/ref/applications/#django.apps.AppConfig.ready
        """
        # Import here to avoid circular imports
        try:
            from .adapters.base import BaseProviderAdapter
            import asgiref.sync

            # Initialize shared client on app startup
            # Using sync_to_async to avoid event loop conflicts with Django
            asgiref.sync.async_to_sync(BaseProviderAdapter.get_client)()

        except Exception as e:
            # Log but don't fail startup
            import logging

            logger = logging.getLogger("gpubroker.providers.apps")
            logger.warning(get_message("client.init_failed", error=str(e)))

from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'

    def ready(self):
        """
        Core app ready method.
        
        NOTE: Core infrastructure signals have been moved to their respective apps
        following Django best practices:
        - Provider signals: gpubrokerpod.gpubrokerapp.apps.providers.signals
        
        This method is kept for future core infrastructure initialization if needed.
        """
        # Core infrastructure initialization can go here
        pass

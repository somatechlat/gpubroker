from django.apps import AppConfig

class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.core'

    def ready(self):
        # Signals import temporarily disabled to prevent module import errors
        # in local runs where apps.core.models is absent.
        return

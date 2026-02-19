"""
Billing App Configuration.
"""
from django.apps import AppConfig


class BillingConfig(AppConfig):
    """Configuration for the billing app."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gpubrokerpod.gpubrokerapp.apps.billing'
    label = 'billing'
    verbose_name = 'Billing & Subscriptions'
    
    def ready(self):
        """Initialize app when Django starts."""
        pass

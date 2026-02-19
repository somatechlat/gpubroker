"""
GPUBROKER Subscriptions App Configuration
"""

from django.apps import AppConfig


class SubscriptionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gpubrokeradmin.apps.subscriptions"
    label = "gpubrokeradmin_subscriptions"
    verbose_name = "GPUBROKER Subscriptions"

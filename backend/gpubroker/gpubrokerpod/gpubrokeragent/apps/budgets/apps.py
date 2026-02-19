"""Budgets App configuration - GPUBROKERAGENT (ADMIN ONLY)."""
from django.apps import AppConfig


class BudgetsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gpubrokerpod.gpubrokeragent.apps.budgets'
    label = 'budgets'
    verbose_name = 'Agent Budgets'

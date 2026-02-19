"""Decisions App configuration - GPUBROKERAGENT (ADMIN ONLY)."""

from django.apps import AppConfig


class DecisionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gpubrokerpod.gpubrokeragent.apps.decisions"
    label = "decisions"
    verbose_name = "Agent Decisions"

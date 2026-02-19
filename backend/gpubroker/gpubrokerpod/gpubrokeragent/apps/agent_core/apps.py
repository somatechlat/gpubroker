"""Agent Core App configuration - GPUBROKERAGENT (ADMIN ONLY)."""

from django.apps import AppConfig


class AgentCoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gpubrokerpod.gpubrokeragent.apps.agent_core"
    label = "agent_core"
    verbose_name = "Agent Core"

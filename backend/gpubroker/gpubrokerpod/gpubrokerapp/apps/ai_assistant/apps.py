"""AI Assistant App configuration - GPUBROKERAPP."""
from django.apps import AppConfig


class AiAssistantConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gpubrokerpod.gpubrokerapp.apps.ai_assistant'
    label = 'ai_assistant'
    verbose_name = 'AI Assistant'

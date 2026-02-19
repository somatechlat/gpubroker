"""WebSocket Gateway App configuration - GPUBROKERAPP."""

from django.apps import AppConfig


class WebsocketGatewayConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "gpubrokerpod.gpubrokerapp.apps.websocket_gateway"
    label = "websocket_gateway"
    verbose_name = "WebSocket Gateway"

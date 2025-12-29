"""WebSocket Gateway App configuration."""
from django.apps import AppConfig


class WebsocketGatewayConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.websocket_gateway'
    verbose_name = 'WebSocket Gateway'

"""
ASGI config for GPUBROKER project.

It exposes the ASGI callable as a module-level variable named ``application``.

This configuration supports:
- HTTP requests via Django
- WebSocket connections via Django Channels
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gpubroker.settings.development")

# Initialize Django ASGI application early to ensure the AppRegistry
# is populated before importing code that may import ORM models.
django_asgi_app = get_asgi_application()

# Import websocket routing after Django setup
from gpubrokerpod.gpubrokerapp.apps.websocket_gateway.routing import (
    websocket_urlpatterns,
)

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(websocket_urlpatterns))
        ),
    }
)

"""
WebSocket URL routing for the WebSocket Gateway app.

Routes:
- /ws/ - Price update WebSocket endpoint
- /ws/notifications/ - User notification WebSocket endpoint
"""
from django.urls import re_path

from .consumers import NotificationConsumer, PriceUpdateConsumer

websocket_urlpatterns = [
    re_path(r'^ws/$', PriceUpdateConsumer.as_asgi()),
    re_path(r'^ws/notifications/$', NotificationConsumer.as_asgi()),
]

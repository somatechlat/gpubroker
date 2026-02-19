"""
WebSocket URL routing for the WebSocket Gateway app.

Routes:
- /ws/ - Price update WebSocket endpoint
- /ws/notifications/ - User notification WebSocket endpoint
- /ws/dashboard/ - Dashboard real-time updates
- /ws/gpu-availability/ - GPU availability real-time updates (Task 13)
"""

from django.urls import re_path

from .consumers import (
    DashboardConsumer,
    GPUAvailabilityConsumer,
    NotificationConsumer,
    PriceUpdateConsumer,
)

websocket_urlpatterns = [
    re_path(r"^ws/$", PriceUpdateConsumer.as_asgi()),
    re_path(r"^ws/notifications/$", NotificationConsumer.as_asgi()),
    re_path(r"^ws/dashboard/$", DashboardConsumer.as_asgi()),
    re_path(r"^ws/gpu-availability/$", GPUAvailabilityConsumer.as_asgi()),
]

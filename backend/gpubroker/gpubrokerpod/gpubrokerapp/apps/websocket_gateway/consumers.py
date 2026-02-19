"""
WebSocket Consumers for real-time price updates.

Uses Django Channels for WebSocket handling.
Subscribes to Redis Pub/Sub channel "price_updates" and streams to clients.
Heartbeat ping every 30 seconds.

NO MOCKS. NO FAKE DATA. REAL IMPLEMENTATIONS ONLY.
"""
import asyncio
import json
import logging
import os
from typing import Optional

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger('gpubroker.websocket_gateway.consumers')

# Configuration
HEARTBEAT_SECONDS = int(os.getenv("WS_HEARTBEAT_SECONDS", "30"))
PRICE_UPDATES_GROUP = "price_updates"


class PriceUpdateConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time price updates.
    
    Features:
    - Joins price_updates channel group on connect
    - Broadcasts price updates to all connected clients
    - Sends heartbeat every 30 seconds
    - Handles graceful disconnection
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.group_name = PRICE_UPDATES_GROUP
    
    async def connect(self):
        """Handle WebSocket connection."""
        # Join price updates group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()
        logger.info(f"WebSocket connected: {self.channel_name}")
        
        # Start heartbeat task
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Cancel heartbeat task
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Leave price updates group
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )
        
        logger.info(f"WebSocket disconnected: {self.channel_name}, code: {close_code}")
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle incoming WebSocket messages.
        
        Clients can send messages to keep connection alive.
        """
        if text_data:
            try:
                data = json.loads(text_data)
                msg_type = data.get("type")
                
                if msg_type == "ping":
                    # Respond to ping with pong
                    await self.send(text_data=json.dumps({"type": "pong"}))
                elif msg_type == "subscribe":
                    # Client subscription acknowledgment
                    await self.send(text_data=json.dumps({
                        "type": "subscribed",
                        "channel": self.group_name
                    }))
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {text_data[:100]}")
    
    async def price_update(self, event):
        """
        Handle price update messages from channel layer.
        
        Called when a message is sent to the price_updates group.
        """
        message = event.get("message", {})
        
        await self.send(text_data=json.dumps({
            "type": "price_update",
            "data": message
        }))
    
    async def _heartbeat_loop(self):
        """Send heartbeat messages periodically."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_SECONDS)
                await self.send(text_data=json.dumps({"type": "heartbeat"}))
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.warning(f"Heartbeat error: {e}")


class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for user-specific notifications.
    
    Joins a user-specific group based on user_id from scope.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_group: Optional[str] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
    
    async def connect(self):
        """Handle WebSocket connection."""
        # Get user from scope (set by auth middleware)
        user = self.scope.get("user")
        
        if user and hasattr(user, "id") and user.id:
            self.user_group = f"user_{user.id}"
            
            await self.channel_layer.group_add(
                self.user_group,
                self.channel_name
            )
        
        await self.accept()
        
        # Start heartbeat
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        if self.user_group:
            await self.channel_layer.group_discard(
                self.user_group,
                self.channel_name
            )
    
    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming messages."""
        if text_data:
            try:
                data = json.loads(text_data)
                if data.get("type") == "ping":
                    await self.send(text_data=json.dumps({"type": "pong"}))
            except json.JSONDecodeError:
                pass
    
    async def notification(self, event):
        """Handle notification messages."""
        await self.send(text_data=json.dumps({
            "type": "notification",
            "data": event.get("message", {})
        }))
    
    async def _heartbeat_loop(self):
        """Send heartbeat messages periodically."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_SECONDS)
                await self.send(text_data=json.dumps({"type": "heartbeat"}))
        except asyncio.CancelledError:
            pass


class DashboardConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for dashboard real-time updates.
    
    Provides:
    - Pod status updates
    - Usage metrics updates
    - Provider health updates
    - Activity feed updates
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_group: Optional[str] = None
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.subscriptions: set = set()
    
    async def connect(self):
        """Handle WebSocket connection."""
        user = self.scope.get("user")
        
        if user and hasattr(user, "id") and user.id:
            self.user_group = f"dashboard_{user.id}"
            
            # Join user-specific dashboard group
            await self.channel_layer.group_add(
                self.user_group,
                self.channel_name
            )
            
            # Join global provider health group
            await self.channel_layer.group_add(
                "provider_health",
                self.channel_name
            )
            
            self.subscriptions.add(self.user_group)
            self.subscriptions.add("provider_health")
        
        await self.accept()
        logger.info(f"Dashboard WebSocket connected: {self.channel_name}")
        
        # Start heartbeat
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # Send initial connection confirmation
        await self.send(text_data=json.dumps({
            "type": "connected",
            "subscriptions": list(self.subscriptions),
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Leave all subscribed groups
        for group in self.subscriptions:
            await self.channel_layer.group_discard(
                group,
                self.channel_name
            )
        
        logger.info(f"Dashboard WebSocket disconnected: {self.channel_name}")
    
    async def receive(self, text_data=None, bytes_data=None):
        """Handle incoming messages."""
        if text_data:
            try:
                data = json.loads(text_data)
                msg_type = data.get("type")
                
                if msg_type == "ping":
                    await self.send(text_data=json.dumps({"type": "pong"}))
                
                elif msg_type == "subscribe_pod":
                    # Subscribe to specific pod updates
                    pod_id = data.get("pod_id")
                    if pod_id:
                        group = f"pod_{pod_id}"
                        await self.channel_layer.group_add(group, self.channel_name)
                        self.subscriptions.add(group)
                        await self.send(text_data=json.dumps({
                            "type": "subscribed",
                            "channel": group,
                        }))
                
                elif msg_type == "unsubscribe_pod":
                    # Unsubscribe from pod updates
                    pod_id = data.get("pod_id")
                    if pod_id:
                        group = f"pod_{pod_id}"
                        await self.channel_layer.group_discard(group, self.channel_name)
                        self.subscriptions.discard(group)
                        await self.send(text_data=json.dumps({
                            "type": "unsubscribed",
                            "channel": group,
                        }))
                
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {text_data[:100]}")
    
    async def pod_status(self, event):
        """Handle pod status update messages."""
        await self.send(text_data=json.dumps({
            "type": "pod_status",
            "data": event.get("message", {}),
        }))
    
    async def usage_update(self, event):
        """Handle usage metrics update messages."""
        await self.send(text_data=json.dumps({
            "type": "usage_update",
            "data": event.get("message", {}),
        }))
    
    async def provider_health_update(self, event):
        """Handle provider health update messages."""
        await self.send(text_data=json.dumps({
            "type": "provider_health",
            "data": event.get("message", {}),
        }))
    
    async def activity_update(self, event):
        """Handle activity feed update messages."""
        await self.send(text_data=json.dumps({
            "type": "activity",
            "data": event.get("message", {}),
        }))
    
    async def _heartbeat_loop(self):
        """Send heartbeat messages periodically."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_SECONDS)
                await self.send(text_data=json.dumps({"type": "heartbeat"}))
        except asyncio.CancelledError:
            pass



# ============================================
# Browse GPU Real-Time Updates (Task 13)
# ============================================

GPU_AVAILABILITY_GROUP = "gpu_availability"


class GPUAvailabilityConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer for real-time GPU availability updates.
    
    Provides:
    - Real-time availability status changes
    - Price updates for GPU offers
    - New offer notifications
    - Offer removal notifications
    
    Clients can subscribe to:
    - All GPU updates (default)
    - Specific provider updates
    - Specific GPU type updates
    - Specific region updates
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.subscriptions: set = set()
        self.filters: dict = {}
    
    async def connect(self):
        """Handle WebSocket connection."""
        # Join global GPU availability group
        await self.channel_layer.group_add(
            GPU_AVAILABILITY_GROUP,
            self.channel_name
        )
        self.subscriptions.add(GPU_AVAILABILITY_GROUP)
        
        await self.accept()
        logger.info(f"GPU Availability WebSocket connected: {self.channel_name}")
        
        # Start heartbeat
        self.heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        
        # Send connection confirmation
        await self.send(text_data=json.dumps({
            "type": "connected",
            "channel": GPU_AVAILABILITY_GROUP,
            "message": "Subscribed to GPU availability updates",
        }))
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            try:
                await self.heartbeat_task
            except asyncio.CancelledError:
                pass
        
        # Leave all subscribed groups
        for group in self.subscriptions:
            await self.channel_layer.group_discard(
                group,
                self.channel_name
            )
        
        logger.info(f"GPU Availability WebSocket disconnected: {self.channel_name}")
    
    async def receive(self, text_data=None, bytes_data=None):
        """
        Handle incoming messages.
        
        Supported message types:
        - ping: Keep-alive ping
        - subscribe_provider: Subscribe to specific provider updates
        - subscribe_gpu_type: Subscribe to specific GPU type updates
        - subscribe_region: Subscribe to specific region updates
        - unsubscribe: Unsubscribe from a channel
        - set_filters: Set client-side filters for updates
        """
        if text_data:
            try:
                data = json.loads(text_data)
                msg_type = data.get("type")
                
                if msg_type == "ping":
                    await self.send(text_data=json.dumps({"type": "pong"}))
                
                elif msg_type == "subscribe_provider":
                    provider = data.get("provider")
                    if provider:
                        group = f"gpu_provider_{provider.lower()}"
                        await self.channel_layer.group_add(group, self.channel_name)
                        self.subscriptions.add(group)
                        await self.send(text_data=json.dumps({
                            "type": "subscribed",
                            "channel": group,
                            "filter": {"provider": provider},
                        }))
                
                elif msg_type == "subscribe_gpu_type":
                    gpu_type = data.get("gpu_type")
                    if gpu_type:
                        # Normalize GPU type for group name
                        normalized = gpu_type.lower().replace(" ", "_")
                        group = f"gpu_type_{normalized}"
                        await self.channel_layer.group_add(group, self.channel_name)
                        self.subscriptions.add(group)
                        await self.send(text_data=json.dumps({
                            "type": "subscribed",
                            "channel": group,
                            "filter": {"gpu_type": gpu_type},
                        }))
                
                elif msg_type == "subscribe_region":
                    region = data.get("region")
                    if region:
                        group = f"gpu_region_{region.lower()}"
                        await self.channel_layer.group_add(group, self.channel_name)
                        self.subscriptions.add(group)
                        await self.send(text_data=json.dumps({
                            "type": "subscribed",
                            "channel": group,
                            "filter": {"region": region},
                        }))
                
                elif msg_type == "unsubscribe":
                    channel = data.get("channel")
                    if channel and channel in self.subscriptions:
                        await self.channel_layer.group_discard(channel, self.channel_name)
                        self.subscriptions.discard(channel)
                        await self.send(text_data=json.dumps({
                            "type": "unsubscribed",
                            "channel": channel,
                        }))
                
                elif msg_type == "set_filters":
                    # Set client-side filters for updates
                    self.filters = {
                        "providers": data.get("providers", []),
                        "gpu_types": data.get("gpu_types", []),
                        "regions": data.get("regions", []),
                        "price_max": data.get("price_max"),
                        "available_only": data.get("available_only", False),
                    }
                    await self.send(text_data=json.dumps({
                        "type": "filters_set",
                        "filters": self.filters,
                    }))
                
            except json.JSONDecodeError:
                logger.warning(f"Invalid JSON received: {text_data[:100]}")
    
    async def availability_update(self, event):
        """
        Handle GPU availability update messages.
        
        Message format:
        {
            "type": "availability_update",
            "offer_id": "...",
            "provider": "...",
            "gpu_type": "...",
            "region": "...",
            "old_availability": "available",
            "new_availability": "limited",
            "old_price": 1.50,
            "new_price": 1.75,
            "timestamp": "..."
        }
        """
        message = event.get("message", {})
        
        # Apply client-side filters if set
        if self.filters:
            if self.filters.get("providers"):
                if message.get("provider") not in self.filters["providers"]:
                    return
            
            if self.filters.get("gpu_types"):
                if message.get("gpu_type") not in self.filters["gpu_types"]:
                    return
            
            if self.filters.get("regions"):
                if message.get("region") not in self.filters["regions"]:
                    return
            
            if self.filters.get("price_max"):
                if message.get("new_price", 0) > self.filters["price_max"]:
                    return
            
            if self.filters.get("available_only"):
                if message.get("new_availability") not in ["available", "limited"]:
                    return
        
        await self.send(text_data=json.dumps({
            "type": "availability_update",
            "data": message,
        }))
    
    async def price_update(self, event):
        """Handle GPU price update messages."""
        message = event.get("message", {})
        
        # Apply filters
        if self.filters:
            if self.filters.get("price_max"):
                if message.get("new_price", 0) > self.filters["price_max"]:
                    return
        
        await self.send(text_data=json.dumps({
            "type": "price_update",
            "data": message,
        }))
    
    async def new_offer(self, event):
        """Handle new GPU offer notifications."""
        await self.send(text_data=json.dumps({
            "type": "new_offer",
            "data": event.get("message", {}),
        }))
    
    async def offer_removed(self, event):
        """Handle GPU offer removal notifications."""
        await self.send(text_data=json.dumps({
            "type": "offer_removed",
            "data": event.get("message", {}),
        }))
    
    async def _heartbeat_loop(self):
        """Send heartbeat messages periodically."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_SECONDS)
                await self.send(text_data=json.dumps({"type": "heartbeat"}))
        except asyncio.CancelledError:
            pass


# Helper function to broadcast availability updates
async def broadcast_availability_update(
    offer_id: str,
    provider: str,
    gpu_type: str,
    region: str,
    old_availability: str,
    new_availability: str,
    old_price: Optional[float] = None,
    new_price: Optional[float] = None,
):
    """
    Broadcast GPU availability update to all subscribed clients.
    
    Sends to:
    - Global gpu_availability group
    - Provider-specific group
    - GPU type-specific group
    - Region-specific group
    """
    from channels.layers import get_channel_layer
    from datetime import datetime, timezone
    
    channel_layer = get_channel_layer()
    
    message = {
        "offer_id": offer_id,
        "provider": provider,
        "gpu_type": gpu_type,
        "region": region,
        "old_availability": old_availability,
        "new_availability": new_availability,
        "old_price": old_price,
        "new_price": new_price,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    
    # Send to global group
    await channel_layer.group_send(
        GPU_AVAILABILITY_GROUP,
        {
            "type": "availability_update",
            "message": message,
        }
    )
    
    # Send to provider-specific group
    await channel_layer.group_send(
        f"gpu_provider_{provider.lower()}",
        {
            "type": "availability_update",
            "message": message,
        }
    )
    
    # Send to GPU type-specific group
    normalized_gpu = gpu_type.lower().replace(" ", "_")
    await channel_layer.group_send(
        f"gpu_type_{normalized_gpu}",
        {
            "type": "availability_update",
            "message": message,
        }
    )
    
    # Send to region-specific group
    await channel_layer.group_send(
        f"gpu_region_{region.lower()}",
        {
            "type": "availability_update",
            "message": message,
        }
    )

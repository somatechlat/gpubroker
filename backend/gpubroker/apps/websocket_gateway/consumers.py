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

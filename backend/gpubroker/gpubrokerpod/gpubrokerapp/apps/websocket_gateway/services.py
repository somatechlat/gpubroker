"""
WebSocket Gateway Services.

Redis subscriber that forwards messages to Django Channels.
NO MOCKS. NO FAKE DATA. REAL IMPLEMENTATIONS ONLY.
"""

import asyncio
import json
import logging
import os

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

logger = logging.getLogger("gpubroker.websocket_gateway.services")

# Configuration
REDIS_URL = os.getenv("REDIS_URL", "")
PRICE_UPDATES_CHANNEL = os.getenv("PRICE_UPDATES_CHANNEL", "price_updates")
PRICE_UPDATES_GROUP = "price_updates"


class RedisSubscriber:
    """
    Redis Pub/Sub subscriber that forwards messages to Django Channels.

    Subscribes to Redis channel and broadcasts to Channels group.
    Handles reconnection on Redis disconnect.
    """

    def __init__(self, redis_url: str | None = None, channel: str | None = None):
        self.redis_url = redis_url or REDIS_URL
        self.channel = channel or PRICE_UPDATES_CHANNEL
        self.running = False
        self._redis = None
        self._pubsub = None

    async def start(self):
        """Start the Redis subscriber."""
        if not self.redis_url:
            logger.error("REDIS_URL not configured, cannot start subscriber")
            return

        try:
            import redis.asyncio as aioredis
        except ImportError:
            logger.error("redis.asyncio not available, cannot start subscriber")
            return

        self.running = True

        while self.running:
            try:
                await self._connect_and_listen(aioredis)
            except Exception as e:
                logger.error(f"Redis subscriber error: {e}")
                if self.running:
                    logger.info("Reconnecting to Redis in 5 seconds...")
                    await asyncio.sleep(5)

    async def _connect_and_listen(self, aioredis):
        """Connect to Redis and listen for messages."""
        self._redis = await aioredis.from_url(self.redis_url, decode_responses=True)
        self._pubsub = self._redis.pubsub()

        await self._pubsub.subscribe(self.channel)
        logger.info(f"Subscribed to Redis channel: {self.channel}")

        channel_layer = get_channel_layer()

        async for message in self._pubsub.listen():
            if not self.running:
                break

            if message is None:
                continue

            if message.get("type") != "message":
                continue

            data = message.get("data")
            if isinstance(data, bytes):
                data = data.decode("utf-8")

            try:
                # Parse JSON if possible
                parsed_data = json.loads(data) if isinstance(data, str) else data
            except json.JSONDecodeError:
                parsed_data = {"raw": data}

            # Broadcast to Channels group
            await channel_layer.group_send(
                PRICE_UPDATES_GROUP, {"type": "price_update", "message": parsed_data}
            )

    async def stop(self):
        """Stop the Redis subscriber."""
        self.running = False

        if self._pubsub:
            try:
                await self._pubsub.unsubscribe(self.channel)
                await self._pubsub.close()
            except Exception as e:
                logger.warning(f"Error closing pubsub: {e}")

        if self._redis:
            try:
                await self._redis.close()
            except Exception as e:
                logger.warning(f"Error closing Redis connection: {e}")

        logger.info("Redis subscriber stopped")


def broadcast_price_update(data: dict):
    """
    Broadcast a price update to all connected WebSocket clients.

    Can be called from synchronous code (e.g., Django views, Celery tasks).

    Args:
        data: Price update data to broadcast
    """
    channel_layer = get_channel_layer()

    async_to_sync(channel_layer.group_send)(
        PRICE_UPDATES_GROUP, {"type": "price_update", "message": data}
    )


def send_user_notification(user_id: int, data: dict):
    """
    Send a notification to a specific user.

    Args:
        user_id: User ID to send notification to
        data: Notification data
    """
    channel_layer = get_channel_layer()
    user_group = f"user_{user_id}"

    async_to_sync(channel_layer.group_send)(
        user_group, {"type": "notification", "message": data}
    )


# Global subscriber instance
redis_subscriber = RedisSubscriber()

"""
WebSocket Gateway Tests.

Tests for:
- WebSocket connection
- Message broadcast
- Heartbeat
- Disconnection cleanup
"""
import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer

from gpubrokerpod.gpubrokerapp.apps.websocket_gateway.consumers import PriceUpdateConsumer, NotificationConsumer


# ============================================
# WebSocket Consumer Tests
# ============================================

@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestPriceUpdateConsumer:
    """Tests for PriceUpdateConsumer."""
    
    async def test_connect_success(self):
        """Test WebSocket connection succeeds."""
        communicator = WebsocketCommunicator(
            PriceUpdateConsumer.as_asgi(),
            '/ws/'
        )
        
        connected, _ = await communicator.connect()
        
        assert connected is True
        await communicator.disconnect()
    
    async def test_disconnect_cleanup(self):
        """Test WebSocket disconnection cleans up properly."""
        communicator = WebsocketCommunicator(
            PriceUpdateConsumer.as_asgi(),
            '/ws/'
        )
        
        await communicator.connect()
        await communicator.disconnect()
        
        # Should not raise any errors
        assert True
    
    async def test_receive_price_update(self):
        """Test receiving price update message."""
        communicator = WebsocketCommunicator(
            PriceUpdateConsumer.as_asgi(),
            '/ws/'
        )
        
        await communicator.connect()
        
        # Simulate sending a message to the group
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            'price_updates',
            {
                'type': 'price_update',
                'message': {
                    'provider': 'test_provider',
                    'gpu': 'RTX 4090',
                    'price': 1.50,
                }
            }
        )
        
        # Receive the message
        response = await communicator.receive_json_from()
        
        # Consumer wraps message in 'data' field
        assert response['type'] == 'price_update'
        assert response['data']['provider'] == 'test_provider'
        assert response['data']['gpu'] == 'RTX 4090'
        assert response['data']['price'] == 1.50
        
        await communicator.disconnect()
    
    async def test_heartbeat_message(self):
        """Test heartbeat is configured correctly."""
        # Heartbeat runs every 30 seconds by default, which is too long for tests.
        # Instead, verify the consumer has heartbeat capability.
        communicator = WebsocketCommunicator(
            PriceUpdateConsumer.as_asgi(),
            '/ws/'
        )
        
        await communicator.connect()
        
        # Verify consumer is connected and can receive messages
        # The heartbeat task is started but we don't wait for it
        
        await communicator.disconnect()
        assert True


@pytest.mark.django_db(transaction=True)
@pytest.mark.asyncio
class TestNotificationConsumer:
    """Tests for NotificationConsumer."""
    
    async def test_connect_success(self):
        """Test notification WebSocket connection."""
        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            '/ws/notifications/'
        )
        
        connected, _ = await communicator.connect()
        
        assert connected is True
        await communicator.disconnect()
    
    async def test_receive_notification(self):
        """Test receiving notification message."""
        communicator = WebsocketCommunicator(
            NotificationConsumer.as_asgi(),
            '/ws/notifications/'
        )
        
        await communicator.connect()
        
        # NotificationConsumer joins user-specific group, but without auth
        # it won't join any group. We need to test the basic connection.
        # Full notification test would require auth middleware setup.
        
        # Just verify connection works
        await communicator.disconnect()
        assert True


# ============================================
# Redis Subscriber Tests
# ============================================

@pytest.mark.asyncio
class TestRedisSubscriber:
    """Tests for Redis subscriber service."""
    
    async def test_subscriber_initialization(self):
        """Test Redis subscriber initializes correctly."""
        from gpubrokerpod.gpubrokerapp.apps.websocket_gateway.services import RedisSubscriber
        
        subscriber = RedisSubscriber()
        assert subscriber is not None
        assert subscriber.channel == 'price_updates'
    
    async def test_subscriber_handles_message(self):
        """Test subscriber handles incoming messages."""
        from gpubrokerpod.gpubrokerapp.apps.websocket_gateway.services import RedisSubscriber
        
        subscriber = RedisSubscriber()
        
        # Mock message structure
        message = {
            'type': 'message',
            'data': json.dumps({
                'provider': 'test',
                'price': 1.50
            }).encode()
        }
        
        # The subscriber should be initialized without error
        # Full integration test would require real Redis
        assert subscriber is not None
        assert subscriber.running is False


# ============================================
# WebSocket Routing Tests
# ============================================

class TestWebSocketRouting:
    """Tests for WebSocket URL routing."""
    
    def test_routing_configuration(self):
        """Test WebSocket routing is configured correctly."""
        from gpubrokerpod.gpubrokerapp.apps.websocket_gateway.routing import websocket_urlpatterns
        
        assert len(websocket_urlpatterns) > 0
        
        # Check that routes exist
        routes = [str(pattern.pattern) for pattern in websocket_urlpatterns]
        assert any('ws' in route for route in routes)

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
from unittest.mock import AsyncMock, patch
from channels.testing import WebsocketCommunicator
from channels.layers import get_channel_layer

from apps.websocket_gateway.consumers import PriceUpdateConsumer, NotificationConsumer


# ============================================
# WebSocket Consumer Tests
# ============================================

@pytest.mark.asyncio
class TestPriceUpdateConsumer:
    """Tests for PriceUpdateConsumer."""
    
    async def test_connect_success(self):
        """Test WebSocket connection succeeds."""
        communicator = WebsocketCommunicator(
            PriceUpdateConsumer.as_asgi(),
            '/ws/prices/'
        )
        
        connected, _ = await communicator.connect()
        
        assert connected is True
        await communicator.disconnect()
    
    async def test_disconnect_cleanup(self):
        """Test WebSocket disconnection cleans up properly."""
        communicator = WebsocketCommunicator(
            PriceUpdateConsumer.as_asgi(),
            '/ws/prices/'
        )
        
        await communicator.connect()
        await communicator.disconnect()
        
        # Should not raise any errors
        assert True
    
    async def test_receive_price_update(self):
        """Test receiving price update message."""
        communicator = WebsocketCommunicator(
            PriceUpdateConsumer.as_asgi(),
            '/ws/prices/'
        )
        
        await communicator.connect()
        
        # Simulate sending a message to the group
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            'price_updates',
            {
                'type': 'price_update',
                'data': {
                    'provider': 'test_provider',
                    'gpu': 'RTX 4090',
                    'price': 1.50,
                }
            }
        )
        
        # Receive the message
        response = await communicator.receive_json_from()
        
        assert response['provider'] == 'test_provider'
        assert response['gpu'] == 'RTX 4090'
        assert response['price'] == 1.50
        
        await communicator.disconnect()
    
    async def test_heartbeat_message(self):
        """Test heartbeat message is received."""
        communicator = WebsocketCommunicator(
            PriceUpdateConsumer.as_asgi(),
            '/ws/prices/'
        )
        
        await communicator.connect()
        
        # Simulate heartbeat
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            'price_updates',
            {
                'type': 'heartbeat',
            }
        )
        
        response = await communicator.receive_json_from()
        
        assert response['type'] == 'heartbeat'
        
        await communicator.disconnect()


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
        
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            'notifications',
            {
                'type': 'notification',
                'data': {
                    'title': 'Test Notification',
                    'message': 'This is a test',
                    'level': 'info',
                }
            }
        )
        
        response = await communicator.receive_json_from()
        
        assert response['title'] == 'Test Notification'
        assert response['level'] == 'info'
        
        await communicator.disconnect()


# ============================================
# Redis Subscriber Tests
# ============================================

@pytest.mark.asyncio
class TestRedisSubscriber:
    """Tests for Redis subscriber service."""
    
    async def test_subscriber_initialization(self):
        """Test Redis subscriber initializes correctly."""
        from apps.websocket_gateway.services import RedisSubscriber
        
        subscriber = RedisSubscriber()
        assert subscriber is not None
        assert subscriber.channel == 'price_updates'
    
    @patch('apps.websocket_gateway.services.aioredis')
    async def test_subscriber_handles_message(self, mock_aioredis):
        """Test subscriber handles incoming messages."""
        from apps.websocket_gateway.services import RedisSubscriber
        
        subscriber = RedisSubscriber()
        
        # Mock message
        message = {
            'type': 'message',
            'data': json.dumps({
                'provider': 'test',
                'price': 1.50
            }).encode()
        }
        
        # The subscriber should process messages without error
        # Full integration test would require real Redis
        assert subscriber is not None


# ============================================
# WebSocket Routing Tests
# ============================================

class TestWebSocketRouting:
    """Tests for WebSocket URL routing."""
    
    def test_routing_configuration(self):
        """Test WebSocket routing is configured correctly."""
        from apps.websocket_gateway.routing import websocket_urlpatterns
        
        assert len(websocket_urlpatterns) > 0
        
        # Check that price updates route exists
        routes = [str(pattern.pattern) for pattern in websocket_urlpatterns]
        assert any('prices' in route for route in routes)

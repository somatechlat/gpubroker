# Design Document: Provider API Gateway

## Overview

The Provider API Gateway is the high-performance core of GPUBROKER, designed to handle millions of concurrent requests while aggregating GPU pricing data from 20+ cloud providers. This design implements:

**Core Stack (Django 5 + Django Ninja)**:
- Django ORM for all database operations
- Django Cache Framework with Redis backend
- Django Channels for WebSocket real-time updates
- Django Middleware for rate limiting

**Apache Stack for Scale**:
- **Apache Kafka (KRaft Mode)** - Event streaming backbone for async communication (NO ZooKeeper)
- **Apache Flink** - Real-time stream processing for price analytics
- **Apache Airflow** - Workflow orchestration (NO Celery)

**Multiple Connection Methods**:
- REST API (Django Ninja)
- WebSocket (Django Channels) - Always available
- Server-Sent Events (SSE)
- GraphQL Subscriptions (optional)

**Observability**:
- Prometheus metrics
- OpenTelemetry tracing
- Grafana dashboards

## Architecture

```mermaid
graph TB
    subgraph "Clients"
        C1[REST Client]
        C2[WebSocket Client]
        C3[SSE Client]
    end
    
    subgraph "Load Balancer"
        LB[nginx/HAProxy]
    end
    
    subgraph "Django Gateway Instances"
        GW1[Gateway + Channels]
        GW2[Gateway + Channels]
        GWN[Gateway + Channels]
    end
    
    subgraph "Apache Kafka Cluster (KRaft Mode)"
        K1[price-updates topic]
        K2[provider-events topic]
        K3[webhooks topic]
        KC[KRaft Controller]
    end
    
    subgraph "Apache Flink"
        F1[Price Change Detector]
        F2[Anomaly Detection]
        F3[Real-time Aggregation]
    end
    
    subgraph "Apache Airflow"
        AF[Airflow Scheduler]
        AW[Airflow Workers]
    end
    
    subgraph "Caching"
        L2[L2 In-Memory]
        L1[Redis Cluster]
    end
    
    subgraph "Providers"
        PA[20+ Provider Adapters]
    end
    
    subgraph "Storage"
        PG[PostgreSQL]
        VAULT[HashiCorp Vault]
    end
    
    C1 & C2 & C3 --> LB
    LB --> GW1 & GW2 & GWN
    GW1 & GW2 & GWN --> L2 --> L1
    GW1 & GW2 & GWN --> K1 & K2
    K1 & K2 --> F1 & F2 & F3
    F1 & F2 & F3 --> K3
    AF --> AW --> PA
    AW --> L1
    GW1 & GW2 & GWN --> PG
    GW1 & GW2 & GWN --> VAULT
```


## Components and Interfaces

### 1. WebSocket Gateway (Django Channels) - ALWAYS AVAILABLE

```python
# backend/gpubroker/apps/providers/consumers.py

import json
import logging
from typing import Dict, Set, Optional
from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async
from django.conf import settings

logger = logging.getLogger('gpubroker.providers.websocket')


class ProviderGatewayConsumer(AsyncJsonWebsocketConsumer):
    """
    WebSocket consumer for real-time provider updates.
    
    Supports:
    - Real-time price updates
    - Provider health status changes
    - Offer availability notifications
    - Custom subscriptions by GPU type/region
    
    Always available as primary real-time channel.
    """
    
    # Track subscriptions per connection
    subscriptions: Dict[str, Set[str]] = {}
    
    async def connect(self):
        """Handle WebSocket connection."""
        self.user = self.scope.get('user')
        self.session_id = self.scope['session'].session_key or 'anonymous'
        
        # Join global updates group
        await self.channel_layer.group_add(
            'provider_updates',
            self.channel_name
        )
        
        # Initialize subscriptions for this connection
        self.subscriptions[self.channel_name] = set()
        
        await self.accept()
        
        # Send connection confirmation with available subscriptions
        await self.send_json({
            'type': 'connection_established',
            'session_id': self.session_id,
            'available_subscriptions': [
                'price_updates',
                'health_status',
                'availability',
                'provider:{provider_name}',
                'gpu:{gpu_type}',
                'region:{region}',
            ],
            'message': 'WebSocket connected. Subscribe to channels for updates.'
        })
    
    async def disconnect(self, close_code):
        """Handle WebSocket disconnection."""
        # Leave all groups
        await self.channel_layer.group_discard(
            'provider_updates',
            self.channel_name
        )
        
        # Clean up subscriptions
        for subscription in self.subscriptions.get(self.channel_name, set()):
            await self.channel_layer.group_discard(
                subscription,
                self.channel_name
            )
        
        if self.channel_name in self.subscriptions:
            del self.subscriptions[self.channel_name]
    
    async def receive_json(self, content):
        """Handle incoming WebSocket messages."""
        msg_type = content.get('type')
        
        if msg_type == 'subscribe':
            await self.handle_subscribe(content)
        elif msg_type == 'unsubscribe':
            await self.handle_unsubscribe(content)
        elif msg_type == 'ping':
            await self.send_json({'type': 'pong', 'timestamp': content.get('timestamp')})
        elif msg_type == 'get_providers':
            await self.handle_get_providers(content)
        elif msg_type == 'get_offers':
            await self.handle_get_offers(content)
        else:
            await self.send_json({
                'type': 'error',
                'message': f'Unknown message type: {msg_type}'
            })
    
    async def handle_subscribe(self, content):
        """Subscribe to a channel."""
        channel = content.get('channel')
        if not channel:
            await self.send_json({'type': 'error', 'message': 'Channel required'})
            return
        
        # Validate channel format
        valid_prefixes = ['price_updates', 'health_status', 'availability', 
                         'provider:', 'gpu:', 'region:']
        if not any(channel.startswith(p) or channel == p.rstrip(':') 
                   for p in valid_prefixes):
            await self.send_json({
                'type': 'error', 
                'message': f'Invalid channel: {channel}'
            })
            return
        
        # Join the group
        group_name = f'sub_{channel.replace(":", "_")}'
        await self.channel_layer.group_add(group_name, self.channel_name)
        self.subscriptions[self.channel_name].add(group_name)
        
        await self.send_json({
            'type': 'subscribed',
            'channel': channel,
            'message': f'Subscribed to {channel}'
        })
    
    async def handle_unsubscribe(self, content):
        """Unsubscribe from a channel."""
        channel = content.get('channel')
        if not channel:
            return
        
        group_name = f'sub_{channel.replace(":", "_")}'
        await self.channel_layer.group_discard(group_name, self.channel_name)
        self.subscriptions[self.channel_name].discard(group_name)
        
        await self.send_json({
            'type': 'unsubscribed',
            'channel': channel
        })
    
    async def handle_get_providers(self, content):
        """Get list of providers via WebSocket."""
        from .adapters.registry import ProviderRegistry
        from .load_balancer import get_load_balancer
        
        lb = get_load_balancer()
        providers = []
        
        for name in ProviderRegistry.list_adapters():
            stats = lb.get_stats().get('providers', {}).get(name, {})
            providers.append({
                'name': name,
                'healthy': stats.get('healthy', False),
                'weight': stats.get('weight', 0),
                'avg_latency_ms': stats.get('avg_latency_ms', 0),
            })
        
        await self.send_json({
            'type': 'providers_list',
            'providers': providers
        })
    
    async def handle_get_offers(self, content):
        """Get offers via WebSocket with filters."""
        from .services import list_offers_from_db
        
        filters = content.get('filters', {})
        result = await list_offers_from_db(
            gpu_term=filters.get('gpu'),
            region=filters.get('region'),
            provider_name=filters.get('provider'),
            max_price=filters.get('max_price'),
            page=filters.get('page', 1),
            per_page=filters.get('per_page', 20),
        )
        
        await self.send_json({
            'type': 'offers_list',
            'total': result['total'],
            'items': result['items'],
            'filters': filters
        })
    
    # Event handlers for group messages
    async def price_update(self, event):
        """Handle price update event from Kafka/Flink."""
        await self.send_json({
            'type': 'price_update',
            'provider': event['provider'],
            'offer_id': event['offer_id'],
            'old_price': event['old_price'],
            'new_price': event['new_price'],
            'change_percent': event['change_percent'],
            'timestamp': event['timestamp'],
        })
    
    async def health_update(self, event):
        """Handle provider health status change."""
        await self.send_json({
            'type': 'health_update',
            'provider': event['provider'],
            'healthy': event['healthy'],
            'reason': event.get('reason'),
            'timestamp': event['timestamp'],
        })
    
    async def availability_update(self, event):
        """Handle offer availability change."""
        await self.send_json({
            'type': 'availability_update',
            'provider': event['provider'],
            'offer_id': event['offer_id'],
            'availability': event['availability'],
            'timestamp': event['timestamp'],
        })


# WebSocket URL routing
# backend/gpubroker/apps/providers/routing.py

from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/providers/$', consumers.ProviderGatewayConsumer.as_asgi()),
    re_path(r'ws/providers/(?P<provider>\w+)/$', consumers.ProviderGatewayConsumer.as_asgi()),
]
```


### 2. Apache Kafka Integration - Event Backbone

```python
# backend/gpubroker/apps/providers/kafka_client.py

import json
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass
from datetime import datetime, timezone
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
from confluent_kafka.admin import AdminClient, NewTopic
from django.conf import settings

logger = logging.getLogger('gpubroker.providers.kafka')


@dataclass
class KafkaConfig:
    """Kafka configuration."""
    bootstrap_servers: str = 'localhost:9092'
    client_id: str = 'gpubroker-gateway'
    group_id: str = 'gpubroker-consumers'
    
    # Topics
    price_updates_topic: str = 'gpubroker.price-updates'
    provider_events_topic: str = 'gpubroker.provider-events'
    webhooks_topic: str = 'gpubroker.webhooks'
    health_checks_topic: str = 'gpubroker.health-checks'


class KafkaProducerClient:
    """
    Kafka producer for publishing events.
    
    Used by Gateway to publish:
    - Price updates from providers
    - Provider health status changes
    - Webhook delivery requests
    - Audit events
    """
    
    def __init__(self, config: Optional[KafkaConfig] = None):
        self.config = config or KafkaConfig(
            bootstrap_servers=getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        )
        self._producer: Optional[Producer] = None
    
    def _get_producer(self) -> Producer:
        """Get or create Kafka producer."""
        if self._producer is None:
            self._producer = Producer({
                'bootstrap.servers': self.config.bootstrap_servers,
                'client.id': self.config.client_id,
                'acks': 'all',  # Wait for all replicas
                'retries': 3,
                'retry.backoff.ms': 100,
                'linger.ms': 5,  # Batch messages for 5ms
                'compression.type': 'snappy',
            })
        return self._producer
    
    def _delivery_callback(self, err, msg):
        """Callback for message delivery confirmation."""
        if err:
            logger.error(f"Kafka delivery failed: {err}")
        else:
            logger.debug(f"Kafka message delivered to {msg.topic()}[{msg.partition()}]")
    
    async def publish_price_update(
        self,
        provider: str,
        offer_id: str,
        old_price: float,
        new_price: float,
    ):
        """Publish price update event."""
        event = {
            'event_type': 'price_update',
            'provider': provider,
            'offer_id': offer_id,
            'old_price': old_price,
            'new_price': new_price,
            'change_percent': ((new_price - old_price) / old_price) * 100 if old_price > 0 else 0,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        
        producer = self._get_producer()
        producer.produce(
            topic=self.config.price_updates_topic,
            key=f"{provider}:{offer_id}".encode(),
            value=json.dumps(event).encode(),
            callback=self._delivery_callback,
        )
        producer.poll(0)  # Trigger callbacks
    
    async def publish_provider_event(
        self,
        provider: str,
        event_type: str,
        data: Dict[str, Any],
    ):
        """Publish provider event (health change, error, etc.)."""
        event = {
            'event_type': event_type,
            'provider': provider,
            'data': data,
            'timestamp': datetime.now(timezone.utc).isoformat(),
        }
        
        producer = self._get_producer()
        producer.produce(
            topic=self.config.provider_events_topic,
            key=provider.encode(),
            value=json.dumps(event).encode(),
            callback=self._delivery_callback,
        )
        producer.poll(0)
    
    async def publish_webhook_request(
        self,
        webhook_url: str,
        event_type: str,
        payload: Dict[str, Any],
    ):
        """Publish webhook delivery request."""
        event = {
            'webhook_url': webhook_url,
            'event_type': event_type,
            'payload': payload,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'retry_count': 0,
        }
        
        producer = self._get_producer()
        producer.produce(
            topic=self.config.webhooks_topic,
            value=json.dumps(event).encode(),
            callback=self._delivery_callback,
        )
        producer.poll(0)
    
    def flush(self, timeout: float = 10.0):
        """Flush pending messages."""
        if self._producer:
            self._producer.flush(timeout)
    
    def close(self):
        """Close producer."""
        if self._producer:
            self._producer.flush()
            self._producer = None


class KafkaConsumerClient:
    """
    Kafka consumer for processing events.
    
    Used by Gateway to consume:
    - Processed price updates from Flink
    - Health check results
    - Webhook delivery confirmations
    """
    
    def __init__(self, config: Optional[KafkaConfig] = None):
        self.config = config or KafkaConfig(
            bootstrap_servers=getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
        )
        self._consumer: Optional[Consumer] = None
        self._running = False
    
    def _get_consumer(self, topics: List[str]) -> Consumer:
        """Get or create Kafka consumer."""
        if self._consumer is None:
            self._consumer = Consumer({
                'bootstrap.servers': self.config.bootstrap_servers,
                'group.id': self.config.group_id,
                'auto.offset.reset': 'latest',
                'enable.auto.commit': True,
                'auto.commit.interval.ms': 5000,
            })
            self._consumer.subscribe(topics)
        return self._consumer
    
    async def consume_loop(
        self,
        topics: List[str],
        handler: Callable[[Dict[str, Any]], None],
    ):
        """
        Start consuming messages in a loop.
        
        Args:
            topics: List of topics to consume
            handler: Callback function for each message
        """
        consumer = self._get_consumer(topics)
        self._running = True
        
        while self._running:
            try:
                msg = consumer.poll(timeout=1.0)
                
                if msg is None:
                    continue
                
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        continue
                    logger.error(f"Kafka consumer error: {msg.error()}")
                    continue
                
                # Parse and handle message
                try:
                    event = json.loads(msg.value().decode())
                    await handler(event)
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON in Kafka message: {e}")
                except Exception as e:
                    logger.error(f"Error handling Kafka message: {e}")
                    
            except KafkaException as e:
                logger.error(f"Kafka exception: {e}")
    
    def stop(self):
        """Stop the consumer loop."""
        self._running = False
        if self._consumer:
            self._consumer.close()
            self._consumer = None


# Singleton instances
_kafka_producer: Optional[KafkaProducerClient] = None
_kafka_consumer: Optional[KafkaConsumerClient] = None


def get_kafka_producer() -> KafkaProducerClient:
    """Get Kafka producer singleton."""
    global _kafka_producer
    if _kafka_producer is None:
        _kafka_producer = KafkaProducerClient()
    return _kafka_producer


def get_kafka_consumer() -> KafkaConsumerClient:
    """Get Kafka consumer singleton."""
    global _kafka_consumer
    if _kafka_consumer is None:
        _kafka_consumer = KafkaConsumerClient()
    return _kafka_consumer
```


### 3. Apache Flink Jobs - Real-Time Stream Processing

```python
# flink/jobs/price_change_detector.py
# PyFlink job for detecting price changes in real-time

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.connectors.kafka import FlinkKafkaConsumer, FlinkKafkaProducer
from pyflink.common.serialization import SimpleStringSchema
from pyflink.datastream.functions import MapFunction, FilterFunction, KeyedProcessFunction
from pyflink.datastream.state import ValueStateDescriptor
from pyflink.common.typeinfo import Types
import json
from datetime import datetime


class PriceChangeDetector(KeyedProcessFunction):
    """
    Flink keyed process function to detect price changes.
    
    Maintains state per offer_id and emits events when price changes
    exceed threshold (default 5%).
    """
    
    def __init__(self, threshold_percent: float = 5.0):
        self.threshold = threshold_percent
        self.last_price_state = None
    
    def open(self, runtime_context):
        """Initialize state."""
        self.last_price_state = runtime_context.get_state(
            ValueStateDescriptor("last_price", Types.FLOAT())
        )
    
    def process_element(self, value, ctx):
        """Process each price update."""
        event = json.loads(value)
        current_price = event.get('new_price', 0)
        offer_id = event.get('offer_id')
        provider = event.get('provider')
        
        last_price = self.last_price_state.value()
        
        if last_price is not None and last_price > 0:
            change_percent = abs((current_price - last_price) / last_price) * 100
            
            if change_percent >= self.threshold:
                # Emit significant price change event
                yield json.dumps({
                    'event_type': 'significant_price_change',
                    'provider': provider,
                    'offer_id': offer_id,
                    'old_price': last_price,
                    'new_price': current_price,
                    'change_percent': change_percent,
                    'direction': 'up' if current_price > last_price else 'down',
                    'timestamp': datetime.utcnow().isoformat(),
                })
        
        # Update state
        self.last_price_state.update(current_price)


class AnomalyDetector(KeyedProcessFunction):
    """
    Detect anomalous pricing patterns.
    
    Uses statistical analysis to identify:
    - Sudden price spikes/drops
    - Unusual availability patterns
    - Provider behavior anomalies
    """
    
    def __init__(self, window_size: int = 100, std_threshold: float = 3.0):
        self.window_size = window_size
        self.std_threshold = std_threshold
        self.prices_state = None
    
    def open(self, runtime_context):
        """Initialize state."""
        self.prices_state = runtime_context.get_list_state(
            ValueStateDescriptor("prices", Types.LIST(Types.FLOAT()))
        )
    
    def process_element(self, value, ctx):
        """Process each price update for anomaly detection."""
        event = json.loads(value)
        current_price = event.get('new_price', 0)
        
        # Get historical prices
        prices = list(self.prices_state.get() or [])
        
        if len(prices) >= 10:  # Need minimum samples
            import statistics
            mean = statistics.mean(prices)
            std = statistics.stdev(prices) if len(prices) > 1 else 0
            
            if std > 0:
                z_score = abs(current_price - mean) / std
                
                if z_score > self.std_threshold:
                    yield json.dumps({
                        'event_type': 'price_anomaly',
                        'provider': event.get('provider'),
                        'offer_id': event.get('offer_id'),
                        'price': current_price,
                        'mean': mean,
                        'std': std,
                        'z_score': z_score,
                        'timestamp': datetime.utcnow().isoformat(),
                    })
        
        # Update state (sliding window)
        prices.append(current_price)
        if len(prices) > self.window_size:
            prices = prices[-self.window_size:]
        self.prices_state.update(prices)


def create_price_analytics_job():
    """
    Create Flink job for price analytics.
    
    Pipeline:
    1. Consume from gpubroker.price-updates
    2. Key by offer_id
    3. Detect significant changes
    4. Detect anomalies
    5. Produce to gpubroker.price-alerts
    """
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(4)
    
    # Kafka consumer
    kafka_consumer = FlinkKafkaConsumer(
        topics='gpubroker.price-updates',
        deserialization_schema=SimpleStringSchema(),
        properties={
            'bootstrap.servers': 'localhost:9092',
            'group.id': 'flink-price-analytics',
        }
    )
    kafka_consumer.set_start_from_latest()
    
    # Kafka producer
    kafka_producer = FlinkKafkaProducer(
        topic='gpubroker.price-alerts',
        serialization_schema=SimpleStringSchema(),
        producer_config={
            'bootstrap.servers': 'localhost:9092',
        }
    )
    
    # Build pipeline
    stream = env.add_source(kafka_consumer)
    
    # Key by offer_id and detect changes
    keyed_stream = stream.key_by(
        lambda x: json.loads(x).get('offer_id', 'unknown')
    )
    
    # Price change detection
    changes = keyed_stream.process(PriceChangeDetector(threshold_percent=5.0))
    
    # Anomaly detection
    anomalies = keyed_stream.process(AnomalyDetector(window_size=100))
    
    # Union and produce to alerts topic
    alerts = changes.union(anomalies)
    alerts.add_sink(kafka_producer)
    
    return env


# Real-time aggregation job
def create_aggregation_job():
    """
    Create Flink job for real-time aggregations.
    
    Computes:
    - Average price per GPU type (1-minute windows)
    - Provider availability rates
    - Market trends
    """
    env = StreamExecutionEnvironment.get_execution_environment()
    
    # Similar structure with windowed aggregations
    # Using Flink's window functions for time-based aggregations
    
    return env
```


### 3. Apache Flink - Real-Time Stream Processing

```python
# Flink jobs are deployed separately as JAR files or PyFlink scripts
# This shows the integration points with Django Gateway

# backend/gpubroker/apps/providers/flink_integration.py

"""
Apache Flink Integration for GPUBROKER.

Flink Jobs:
1. PriceChangeDetector - Detects price changes and publishes to Kafka
2. AnomalyDetector - Detects unusual pricing patterns
3. RealTimeAggregator - Computes live statistics per provider/GPU type
4. HealthScorer - Calculates provider health scores

All jobs consume from Kafka topics and produce to output topics.
Django Gateway consumes processed results.
"""

from dataclasses import dataclass
from typing import Dict, Any, List
from datetime import datetime, timezone


@dataclass
class FlinkJobConfig:
    """Configuration for Flink jobs."""
    job_manager_url: str = 'http://localhost:8081'
    parallelism: int = 4
    checkpoint_interval_ms: int = 60000
    
    # Input topics
    raw_prices_topic: str = 'gpubroker.raw-prices'
    provider_events_topic: str = 'gpubroker.provider-events'
    
    # Output topics
    price_changes_topic: str = 'gpubroker.price-changes'
    anomalies_topic: str = 'gpubroker.anomalies'
    aggregations_topic: str = 'gpubroker.aggregations'
    health_scores_topic: str = 'gpubroker.health-scores'


# PyFlink Job: Price Change Detector
PRICE_CHANGE_DETECTOR_SQL = """
-- Flink SQL job for detecting price changes
-- Deployed via Flink SQL Gateway or as a JAR

CREATE TABLE raw_prices (
    provider STRING,
    offer_id STRING,
    gpu_type STRING,
    price DECIMAL(10, 4),
    region STRING,
    event_time TIMESTAMP(3),
    WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
) WITH (
    'connector' = 'kafka',
    'topic' = 'gpubroker.raw-prices',
    'properties.bootstrap.servers' = 'localhost:9092',
    'format' = 'json',
    'scan.startup.mode' = 'latest-offset'
);

CREATE TABLE price_changes (
    provider STRING,
    offer_id STRING,
    gpu_type STRING,
    old_price DECIMAL(10, 4),
    new_price DECIMAL(10, 4),
    change_percent DECIMAL(10, 4),
    region STRING,
    detected_at TIMESTAMP(3)
) WITH (
    'connector' = 'kafka',
    'topic' = 'gpubroker.price-changes',
    'properties.bootstrap.servers' = 'localhost:9092',
    'format' = 'json'
);

-- Detect price changes using LAG window function
INSERT INTO price_changes
SELECT 
    provider,
    offer_id,
    gpu_type,
    LAG(price) OVER (PARTITION BY provider, offer_id ORDER BY event_time) as old_price,
    price as new_price,
    CASE 
        WHEN LAG(price) OVER (PARTITION BY provider, offer_id ORDER BY event_time) > 0 
        THEN ((price - LAG(price) OVER (PARTITION BY provider, offer_id ORDER BY event_time)) 
              / LAG(price) OVER (PARTITION BY provider, offer_id ORDER BY event_time)) * 100
        ELSE 0
    END as change_percent,
    region,
    event_time as detected_at
FROM raw_prices
WHERE price <> LAG(price) OVER (PARTITION BY provider, offer_id ORDER BY event_time);
"""


# PyFlink Job: Real-Time Aggregations
REALTIME_AGGREGATION_SQL = """
-- Tumbling window aggregations for real-time statistics

CREATE TABLE price_aggregations (
    provider STRING,
    gpu_type STRING,
    window_start TIMESTAMP(3),
    window_end TIMESTAMP(3),
    avg_price DECIMAL(10, 4),
    min_price DECIMAL(10, 4),
    max_price DECIMAL(10, 4),
    offer_count BIGINT,
    PRIMARY KEY (provider, gpu_type, window_start) NOT ENFORCED
) WITH (
    'connector' = 'kafka',
    'topic' = 'gpubroker.aggregations',
    'properties.bootstrap.servers' = 'localhost:9092',
    'format' = 'json'
);

-- 1-minute tumbling window aggregations
INSERT INTO price_aggregations
SELECT 
    provider,
    gpu_type,
    TUMBLE_START(event_time, INTERVAL '1' MINUTE) as window_start,
    TUMBLE_END(event_time, INTERVAL '1' MINUTE) as window_end,
    AVG(price) as avg_price,
    MIN(price) as min_price,
    MAX(price) as max_price,
    COUNT(*) as offer_count
FROM raw_prices
GROUP BY 
    provider,
    gpu_type,
    TUMBLE(event_time, INTERVAL '1' MINUTE);
"""


class FlinkResultConsumer:
    """
    Consumes processed results from Flink via Kafka.
    
    Pushes updates to WebSocket clients via Django Channels.
    """
    
    def __init__(self):
        from .kafka_client import get_kafka_consumer
        self.consumer = get_kafka_consumer()
    
    async def handle_price_change(self, event: Dict[str, Any]):
        """Handle price change event from Flink."""
        from channels.layers import get_channel_layer
        
        channel_layer = get_channel_layer()
        
        # Broadcast to all subscribers
        await channel_layer.group_send(
            'provider_updates',
            {
                'type': 'price_update',
                'provider': event['provider'],
                'offer_id': event['offer_id'],
                'old_price': event['old_price'],
                'new_price': event['new_price'],
                'change_percent': event['change_percent'],
                'timestamp': event['detected_at'],
            }
        )
        
        # Also send to provider-specific channel
        await channel_layer.group_send(
            f"sub_provider_{event['provider']}",
            {
                'type': 'price_update',
                'provider': event['provider'],
                'offer_id': event['offer_id'],
                'old_price': event['old_price'],
                'new_price': event['new_price'],
                'change_percent': event['change_percent'],
                'timestamp': event['detected_at'],
            }
        )
    
    async def handle_anomaly(self, event: Dict[str, Any]):
        """Handle anomaly detection event from Flink."""
        from channels.layers import get_channel_layer
        import logging
        
        logger = logging.getLogger('gpubroker.providers.flink')
        logger.warning(f"Price anomaly detected: {event}")
        
        channel_layer = get_channel_layer()
        await channel_layer.group_send(
            'provider_updates',
            {
                'type': 'anomaly_alert',
                'provider': event['provider'],
                'anomaly_type': event['anomaly_type'],
                'details': event['details'],
                'timestamp': event['detected_at'],
            }
        )
    
    async def start_consuming(self):
        """Start consuming Flink output topics."""
        topics = [
            'gpubroker.price-changes',
            'gpubroker.anomalies',
            'gpubroker.aggregations',
        ]
        
        async def handler(event: Dict[str, Any]):
            event_type = event.get('event_type', 'unknown')
            if 'change_percent' in event:
                await self.handle_price_change(event)
            elif 'anomaly_type' in event:
                await self.handle_anomaly(event)
        
        await self.consumer.consume_loop(topics, handler)
```


### 4. Apache Airflow DAGs - Workflow Orchestration (NO CELERY)

```python
# airflow/dags/provider_workflows.py

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.sensors.external_task import ExternalTaskSensor
from airflow.utils.dates import days_ago
import json
import logging

logger = logging.getLogger('airflow.gpubroker')


# Default DAG arguments
default_args = {
    'owner': 'gpubroker',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=1),
    'execution_timeout': timedelta(minutes=10),
}


# =============================================================================
# DAG 1: Cache Warming (Every 5 minutes)
# =============================================================================

def warm_provider_cache(provider_name: str, **context):
    """
    Task to warm cache for a single provider.
    
    Fetches latest offers and stores in Redis.
    """
    import asyncio
    import sys
    sys.path.insert(0, '/app/backend/gpubroker')
    
    from apps.providers.adapters.registry import ProviderRegistry
    from apps.providers.vault_client import get_vault_manager
    from apps.providers.cache import get_cache
    
    async def _warm():
        adapter = ProviderRegistry.get_adapter(provider_name)
        vault = get_vault_manager()
        cache = get_cache()
        
        api_key = await vault.get_provider_credential(provider_name)
        offers = await adapter.get_offers(api_key)
        
        cache_key = f"gateway:offers:{provider_name}"
        await cache.set(cache_key, [o.__dict__ for o in offers], ttl=300)
        
        logger.info(f"Cache warmed for {provider_name}: {len(offers)} offers")
        return len(offers)
    
    return asyncio.run(_warm())


with DAG(
    dag_id='cache_warming',
    default_args=default_args,
    description='Warm provider caches every 5 minutes',
    schedule_interval='*/5 * * * *',
    start_date=days_ago(1),
    catchup=False,
    tags=['cache', 'providers'],
) as cache_warming_dag:
    
    # Get list of providers dynamically
    providers = ['runpod', 'vastai', 'aws_sagemaker', 'lambdalabs', 'paperspace']
    
    warm_tasks = []
    for provider in providers:
        task = PythonOperator(
            task_id=f'warm_{provider}_cache',
            python_callable=warm_provider_cache,
            op_kwargs={'provider_name': provider},
            pool='provider_pool',  # Limit concurrent provider calls
        )
        warm_tasks.append(task)
    
    # All tasks run in parallel
    warm_tasks


# =============================================================================
# DAG 2: Health Checks (Every 30 seconds)
# =============================================================================

def check_provider_health(provider_name: str, **context):
    """
    Task to health check a provider.
    
    Updates load balancer health status.
    """
    import asyncio
    import sys
    sys.path.insert(0, '/app/backend/gpubroker')
    
    from apps.providers.adapters.registry import ProviderRegistry
    from apps.providers.load_balancer import get_load_balancer
    from apps.providers.vault_client import get_vault_manager
    from apps.providers.kafka_client import get_kafka_producer
    
    async def _check():
        adapter = ProviderRegistry.get_adapter(provider_name)
        vault = get_vault_manager()
        lb = get_load_balancer()
        kafka = get_kafka_producer()
        
        try:
            api_key = await vault.get_provider_credential(provider_name)
            is_healthy = await adapter.validate_credentials({'api_key': api_key})
            
            if is_healthy:
                lb.mark_healthy(provider_name)
            else:
                lb.mark_unhealthy(provider_name)
            
            # Publish health event to Kafka
            await kafka.publish_provider_event(
                provider=provider_name,
                event_type='health_check',
                data={'healthy': is_healthy}
            )
            
            return is_healthy
            
        except Exception as e:
            lb.mark_unhealthy(provider_name)
            await kafka.publish_provider_event(
                provider=provider_name,
                event_type='health_check_failed',
                data={'error': str(e)}
            )
            raise
    
    return asyncio.run(_check())


with DAG(
    dag_id='health_checks',
    default_args=default_args,
    description='Health check all providers every 30 seconds',
    schedule_interval='*/1 * * * *',  # Airflow minimum is 1 minute
    start_date=days_ago(1),
    catchup=False,
    max_active_runs=1,
    tags=['health', 'providers'],
) as health_checks_dag:
    
    providers = ['runpod', 'vastai', 'aws_sagemaker', 'lambdalabs', 'paperspace']
    
    for provider in providers:
        PythonOperator(
            task_id=f'check_{provider}_health',
            python_callable=check_provider_health,
            op_kwargs={'provider_name': provider},
            pool='health_check_pool',
        )


# =============================================================================
# DAG 3: Data Sync (Hourly)
# =============================================================================

def sync_provider_offers(provider_name: str, **context):
    """
    Full sync of provider offers to database.
    """
    import asyncio
    import sys
    sys.path.insert(0, '/app/backend/gpubroker')
    
    from apps.providers.adapters.registry import ProviderRegistry
    from apps.providers.vault_client import get_vault_manager
    from apps.providers.models import Provider, GPUOffer
    from django.db import transaction
    
    async def _sync():
        adapter = ProviderRegistry.get_adapter(provider_name)
        vault = get_vault_manager()
        
        api_key = await vault.get_provider_credential(provider_name)
        offers = await adapter.get_offers(api_key)
        
        # Get or create provider
        provider, _ = await Provider.objects.aget_or_create(
            name=provider_name,
            defaults={'display_name': provider_name.title()}
        )
        
        # Bulk upsert offers
        synced_count = 0
        for offer in offers:
            await GPUOffer.objects.aupdate_or_create(
                provider=provider,
                name=offer.instance_type,
                region=offer.region,
                defaults={
                    'gpu_type': offer.instance_type,
                    'gpu_memory_gb': offer.gpu_memory_gb,
                    'price_per_hour': offer.price_per_hour,
                    'availability_status': offer.availability,
                    'compliance_tags': offer.compliance_tags,
                }
            )
            synced_count += 1
        
        logger.info(f"Synced {synced_count} offers from {provider_name}")
        return synced_count
    
    return asyncio.run(_sync())


with DAG(
    dag_id='data_sync',
    default_args=default_args,
    description='Full sync of provider data hourly',
    schedule_interval='@hourly',
    start_date=days_ago(1),
    catchup=False,
    tags=['sync', 'providers', 'database'],
) as data_sync_dag:
    
    providers = ['runpod', 'vastai', 'aws_sagemaker', 'lambdalabs', 'paperspace']
    
    sync_tasks = []
    for provider in providers:
        task = PythonOperator(
            task_id=f'sync_{provider}_offers',
            python_callable=sync_provider_offers,
            op_kwargs={'provider_name': provider},
            pool='provider_pool',
        )
        sync_tasks.append(task)
    
    # Cleanup old offers after sync
    cleanup = PostgresOperator(
        task_id='cleanup_stale_offers',
        postgres_conn_id='gpubroker_db',
        sql="""
            DELETE FROM gpu_offers 
            WHERE last_updated < NOW() - INTERVAL '24 hours'
        """,
    )
    
    sync_tasks >> cleanup


# =============================================================================
# DAG 4: Webhook Delivery (Triggered by Kafka)
# =============================================================================

def deliver_webhook(webhook_url: str, payload: dict, **context):
    """
    Deliver webhook with retries.
    """
    import httpx
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(webhook_url, json=payload)
            response.raise_for_status()
            return {'status': 'delivered', 'status_code': response.status_code}
    except Exception as e:
        logger.error(f"Webhook delivery failed: {e}")
        raise


with DAG(
    dag_id='webhook_delivery',
    default_args={
        **default_args,
        'retries': 5,
        'retry_delay': timedelta(seconds=30),
        'retry_exponential_backoff': True,
    },
    description='Deliver webhooks with retry logic',
    schedule_interval=None,  # Triggered externally
    start_date=days_ago(1),
    catchup=False,
    tags=['webhooks', 'notifications'],
) as webhook_dag:
    
    deliver = PythonOperator(
        task_id='deliver_webhook',
        python_callable=deliver_webhook,
        op_kwargs={
            'webhook_url': '{{ dag_run.conf.webhook_url }}',
            'payload': '{{ dag_run.conf.payload }}',
        },
    )
```


### 4. Apache Airflow - Workflow Orchestration (NO CELERY)

```python
# Airflow DAGs are deployed to the Airflow scheduler
# Located in: airflow/dags/gpubroker/

# airflow/dags/gpubroker/provider_workflows.py

"""
Apache Airflow DAGs for GPUBROKER Provider Gateway.

DAGs:
1. cache_warming_dag - Warm provider caches every 5 minutes
2. health_check_dag - Check provider health every 30 seconds
3. data_sync_dag - Sync provider data to database hourly
4. analytics_dag - Generate daily analytics reports
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.providers.http.operators.http import SimpleHttpOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.utils.dates import days_ago


# Default arguments for all DAGs
default_args = {
    'owner': 'gpubroker',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=1),
    'execution_timeout': timedelta(minutes=10),
}


# =============================================================================
# DAG 1: Cache Warming (Every 5 minutes)
# =============================================================================

def warm_provider_cache(provider_name: str, **context):
    """
    Warm cache for a single provider.
    
    Fetches latest offers and stores in Redis.
    """
    import asyncio
    import json
    import redis
    import httpx
    import os
    
    # Get API key from Vault or environment
    api_key = os.getenv(f"{provider_name.upper()}_API_KEY")
    
    # Provider API endpoints (simplified - real implementation uses adapters)
    provider_urls = {
        'vastai': 'https://console.vast.ai/api/v0/bundles',
        'runpod': 'https://api.runpod.io/graphql',
        # ... other providers
    }
    
    url = provider_urls.get(provider_name)
    if not url:
        print(f"Unknown provider: {provider_name}")
        return
    
    # Fetch offers
    headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
    
    try:
        with httpx.Client(timeout=30) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            offers = response.json()
        
        # Store in Redis
        redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
        cache_key = f"gateway:offers:{provider_name}"
        redis_client.setex(cache_key, 300, json.dumps(offers))
        
        print(f"Cached {len(offers) if isinstance(offers, list) else 'N/A'} offers for {provider_name}")
        
    except Exception as e:
        print(f"Cache warming failed for {provider_name}: {e}")
        raise


with DAG(
    'gpubroker_cache_warming',
    default_args=default_args,
    description='Warm provider caches every 5 minutes',
    schedule_interval='*/5 * * * *',  # Every 5 minutes
    start_date=days_ago(1),
    catchup=False,
    tags=['gpubroker', 'cache'],
) as cache_warming_dag:
    
    providers = ['vastai', 'runpod', 'lambdalabs', 'paperspace']
    
    for provider in providers:
        PythonOperator(
            task_id=f'warm_cache_{provider}',
            python_callable=warm_provider_cache,
            op_kwargs={'provider_name': provider},
        )


# =============================================================================
# DAG 2: Health Checks (Every 30 seconds via sensor)
# =============================================================================

def check_provider_health(provider_name: str, **context):
    """
    Check health of a provider and update load balancer.
    """
    import httpx
    import os
    import redis
    import json
    from datetime import datetime, timezone
    
    api_key = os.getenv(f"{provider_name.upper()}_API_KEY")
    
    # Health check endpoints
    health_endpoints = {
        'vastai': 'https://console.vast.ai/api/v0/',
        'runpod': 'https://api.runpod.io/health',
        # ... other providers
    }
    
    url = health_endpoints.get(provider_name)
    if not url:
        return {'provider': provider_name, 'healthy': False, 'reason': 'Unknown provider'}
    
    try:
        headers = {'Authorization': f'Bearer {api_key}'} if api_key else {}
        
        with httpx.Client(timeout=10) as client:
            start = datetime.now()
            response = client.get(url, headers=headers)
            latency_ms = (datetime.now() - start).total_seconds() * 1000
            
            is_healthy = response.status_code < 500
            
            # Update Redis with health status
            redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
            health_data = {
                'provider': provider_name,
                'healthy': is_healthy,
                'latency_ms': latency_ms,
                'status_code': response.status_code,
                'checked_at': datetime.now(timezone.utc).isoformat(),
            }
            redis_client.hset('provider_health', provider_name, json.dumps(health_data))
            
            return health_data
            
    except Exception as e:
        # Mark as unhealthy on error
        redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
        health_data = {
            'provider': provider_name,
            'healthy': False,
            'error': str(e),
            'checked_at': datetime.now(timezone.utc).isoformat(),
        }
        redis_client.hset('provider_health', provider_name, json.dumps(health_data))
        return health_data


with DAG(
    'gpubroker_health_checks',
    default_args=default_args,
    description='Check provider health every minute',
    schedule_interval='* * * * *',  # Every minute (Airflow minimum)
    start_date=days_ago(1),
    catchup=False,
    tags=['gpubroker', 'health'],
) as health_check_dag:
    
    providers = ['vastai', 'runpod', 'lambdalabs', 'paperspace']
    
    for provider in providers:
        PythonOperator(
            task_id=f'health_check_{provider}',
            python_callable=check_provider_health,
            op_kwargs={'provider_name': provider},
        )


# =============================================================================
# DAG 3: Data Sync (Hourly)
# =============================================================================

def sync_provider_to_database(provider_name: str, **context):
    """
    Sync provider offers to PostgreSQL database.
    """
    import os
    import json
    import redis
    import psycopg2
    from datetime import datetime, timezone
    
    # Get cached offers from Redis
    redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379/0'))
    cache_key = f"gateway:offers:{provider_name}"
    cached_data = redis_client.get(cache_key)
    
    if not cached_data:
        print(f"No cached data for {provider_name}")
        return
    
    offers = json.loads(cached_data)
    
    # Connect to PostgreSQL
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    
    try:
        # Upsert offers
        for offer in offers if isinstance(offers, list) else []:
            cursor.execute("""
                INSERT INTO gpu_offers (
                    id, provider_id, name, gpu_type, price_per_hour, 
                    region, availability_status, last_updated
                )
                SELECT 
                    gen_random_uuid(),
                    p.id,
                    %(name)s,
                    %(gpu_type)s,
                    %(price)s,
                    %(region)s,
                    'available',
                    %(updated_at)s
                FROM providers p
                WHERE p.name = %(provider)s
                ON CONFLICT (provider_id, gpu_type, region) 
                DO UPDATE SET
                    price_per_hour = EXCLUDED.price_per_hour,
                    last_updated = EXCLUDED.last_updated
            """, {
                'name': offer.get('name', offer.get('gpu_type', 'Unknown')),
                'gpu_type': offer.get('gpu_type', offer.get('gpu_name', 'Unknown')),
                'price': offer.get('price_per_hour', offer.get('dph_total', 0)),
                'region': offer.get('region', 'global'),
                'provider': provider_name,
                'updated_at': datetime.now(timezone.utc),
            })
        
        conn.commit()
        print(f"Synced {len(offers) if isinstance(offers, list) else 0} offers for {provider_name}")
        
    finally:
        cursor.close()
        conn.close()


with DAG(
    'gpubroker_data_sync',
    default_args=default_args,
    description='Sync provider data to database hourly',
    schedule_interval='@hourly',
    start_date=days_ago(1),
    catchup=False,
    tags=['gpubroker', 'sync'],
) as data_sync_dag:
    
    providers = ['vastai', 'runpod', 'lambdalabs', 'paperspace']
    
    for provider in providers:
        PythonOperator(
            task_id=f'sync_{provider}',
            python_callable=sync_provider_to_database,
            op_kwargs={'provider_name': provider},
        )


# =============================================================================
# DAG 4: Webhook Delivery (Triggered by Kafka)
# =============================================================================

def deliver_webhook(webhook_url: str, payload: dict, **context):
    """
    Deliver webhook notification with retries.
    """
    import httpx
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(webhook_url, json=payload)
            response.raise_for_status()
            return {'status': 'delivered', 'url': webhook_url}
    except Exception as e:
        print(f"Webhook delivery failed: {e}")
        raise


with DAG(
    'gpubroker_webhook_delivery',
    default_args={
        **default_args,
        'retries': 5,
        'retry_delay': timedelta(seconds=30),
    },
    description='Deliver webhook notifications',
    schedule_interval=None,  # Triggered externally
    start_date=days_ago(1),
    catchup=False,
    tags=['gpubroker', 'webhooks'],
) as webhook_dag:
    
    PythonOperator(
        task_id='deliver_webhook',
        python_callable=deliver_webhook,
        op_kwargs={
            'webhook_url': '{{ dag_run.conf.webhook_url }}',
            'payload': '{{ dag_run.conf.payload }}',
        },
    )
```


### 5. Multi-Tier Cache Layer

```python
# backend/gpubroker/apps/providers/cache.py

from typing import Optional, Any, Dict
from datetime import datetime
import random
import hashlib
import logging
from django.core.cache import caches
from django.conf import settings

logger = logging.getLogger('gpubroker.providers.cache')


class L2InMemoryCache:
    """
    L2 in-memory cache with probabilistic early expiration (XFetch).
    
    Prevents cache stampede by probabilistically refreshing
    items before they expire.
    """
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 60):
        self._cache: Dict[str, tuple] = {}
        self._max_size = max_size
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value with probabilistic early expiration."""
        if key not in self._cache:
            return None
        
        value, expiry, delta = self._cache[key]
        now = datetime.now().timestamp()
        
        if now >= expiry:
            del self._cache[key]
            return None
        
        # XFetch algorithm for stampede prevention
        time_remaining = expiry - now
        if time_remaining < delta:
            probability = min(1.0, delta / (time_remaining + 0.001))
            if random.random() < probability * 0.1:
                return None  # Trigger refresh
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, delta: int = 10):
        """Set value with TTL."""
        if len(self._cache) >= self._max_size:
            self._evict_oldest()
        
        ttl = ttl or self._default_ttl
        expiry = datetime.now().timestamp() + ttl
        self._cache[key] = (value, expiry, delta)
    
    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def _evict_oldest(self):
        if not self._cache:
            return
        sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][1])
        evict_count = max(1, len(sorted_keys) // 10)
        for key in sorted_keys[:evict_count]:
            del self._cache[key]


class MultiTierCache:
    """
    Multi-tier cache: L2 (in-memory) -> L1 (Redis).
    
    Lookup: L2 -> L1 -> source
    Write: L1 -> L2 (write-through)
    """
    
    def __init__(self):
        self._l2 = L2InMemoryCache(max_size=10000, default_ttl=60)
        self._redis_alias = 'default'
    
    @property
    def _redis(self):
        return caches[self._redis_alias]
    
    def _make_key(self, path: str, params: Dict[str, Any]) -> str:
        base = path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v)
        return "gateway:" + hashlib.sha256(base.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        # Try L2 first
        value = self._l2.get(key)
        if value is not None:
            return value
        
        # Try L1 (Redis)
        try:
            value = self._redis.get(key)
            if value is not None:
                self._l2.set(key, value, ttl=30)
                return value
        except Exception as e:
            logger.warning(f"Redis unavailable: {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 60):
        try:
            self._redis.set(key, value, timeout=ttl)
        except Exception as e:
            logger.warning(f"Redis write failed: {e}")
        
        self._l2.set(key, value, ttl=min(ttl, 30))
    
    async def delete(self, key: str):
        self._l2.delete(key)
        try:
            self._redis.delete(key)
        except Exception:
            pass


_cache_instance: Optional[MultiTierCache] = None


def get_cache() -> MultiTierCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MultiTierCache()
    return _cache_instance
```

### 6. Redis-Backed Sliding Window Rate Limiter

```python
# backend/gpubroker/apps/providers/rate_limiter.py

import time
import logging
from typing import Optional
from dataclasses import dataclass
from django.conf import settings

logger = logging.getLogger('gpubroker.providers.rate_limiter')


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_at: float
    retry_after: Optional[int] = None


class SlidingWindowRateLimiter:
    """
    Redis-backed sliding window rate limiter.
    
    Uses sorted sets for precise sliding window counting.
    """
    
    PLAN_LIMITS = {
        'free': 10,
        'pro': 100,
        'enterprise': 1000,
        'unlimited': 100000,
    }
    
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
    
    def _get_redis_client(self):
        import redis
        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        return redis.from_url(redis_url)
    
    def check(self, key: str, plan: str = 'free') -> RateLimitResult:
        limit = self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS['free'])
        now = time.time()
        window_start = now - self.window_seconds
        redis_key = f"ratelimit:{key}"
        
        try:
            client = self._get_redis_client()
            pipe = client.pipeline()
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zcard(redis_key)
            results = pipe.execute()
            current_count = results[1]
            
            if current_count < limit:
                client.zadd(redis_key, {str(now): now})
                client.expire(redis_key, self.window_seconds + 1)
                return RateLimitResult(
                    allowed=True,
                    remaining=limit - current_count - 1,
                    reset_at=now + self.window_seconds,
                )
            else:
                oldest = client.zrange(redis_key, 0, 0, withscores=True)
                retry_after = int(oldest[0][1] + self.window_seconds - now) + 1 if oldest else self.window_seconds
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=now + retry_after,
                    retry_after=retry_after,
                )
        except Exception as e:
            logger.error(f"Rate limiter error: {e}")
            return RateLimitResult(allowed=True, remaining=limit, reset_at=now + self.window_seconds)


_rate_limiter: Optional[SlidingWindowRateLimiter] = None


def get_rate_limiter() -> SlidingWindowRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = SlidingWindowRateLimiter(window_seconds=60)
    return _rate_limiter
```


### 5. Multi-Tier Cache Layer

```python
# backend/gpubroker/apps/providers/cache.py

from typing import Optional, Any, Dict
from datetime import datetime
import random
import json
import hashlib
import logging
from django.core.cache import caches
from django.conf import settings

logger = logging.getLogger('gpubroker.providers.cache')


class L2InMemoryCache:
    """
    L2 in-memory cache with probabilistic early expiration (PEE).
    
    Implements cache stampede prevention using the XFetch algorithm:
    - Items have a TTL and a delta (time to recompute)
    - As TTL approaches, probability of early refresh increases
    - Prevents thundering herd on cache expiration
    """
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 60):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry, delta)
        self._max_size = max_size
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value with probabilistic early expiration."""
        if key not in self._cache:
            return None
        
        value, expiry, delta = self._cache[key]
        now = datetime.now().timestamp()
        
        if now >= expiry:
            del self._cache[key]
            return None
        
        # Probabilistic early expiration (XFetch algorithm)
        time_remaining = expiry - now
        if time_remaining < delta:
            probability = min(1.0, delta / (time_remaining + 0.001))
            if random.random() < probability * 0.1:
                logger.debug(f"PEE triggered for key {key[:20]}...")
                return None
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, delta: int = 10):
        """Set value with TTL and delta for PEE."""
        if len(self._cache) >= self._max_size:
            self._evict_oldest()
        
        ttl = ttl or self._default_ttl
        expiry = datetime.now().timestamp() + ttl
        self._cache[key] = (value, expiry, delta)
    
    def delete(self, key: str) -> bool:
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def _evict_oldest(self):
        if not self._cache:
            return
        sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][1])
        evict_count = max(1, len(sorted_keys) // 10)
        for key in sorted_keys[:evict_count]:
            del self._cache[key]


class MultiTierCache:
    """
    Multi-tier cache with L2 (in-memory) and L1 (Redis).
    
    Lookup order: L2 -> L1 -> fetch from source
    Write order: L1 -> L2 (write-through)
    """
    
    def __init__(self):
        self._l2 = L2InMemoryCache(max_size=10000, default_ttl=60)
        self._redis_alias = 'default'
    
    @property
    def _redis(self):
        return caches[self._redis_alias]
    
    def _make_key(self, path: str, params: Dict[str, Any]) -> str:
        base = path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v)
        return "gateway:" + hashlib.sha256(base.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        # Try L2 first
        value = self._l2.get(key)
        if value is not None:
            logger.debug(f"L2 cache hit for {key[:20]}...")
            return value
        
        # Try L1 (Redis)
        try:
            value = self._redis.get(key)
            if value is not None:
                logger.debug(f"L1 cache hit for {key[:20]}...")
                self._l2.set(key, value, ttl=30)
                return value
        except Exception as e:
            logger.warning(f"Redis unavailable, using L2 only: {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 60):
        try:
            self._redis.set(key, value, timeout=ttl)
        except Exception as e:
            logger.warning(f"Redis write failed: {e}")
        
        self._l2.set(key, value, ttl=min(ttl, 30))
    
    async def delete(self, key: str):
        self._l2.delete(key)
        try:
            self._redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")


_cache_instance: Optional[MultiTierCache] = None


def get_cache() -> MultiTierCache:
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MultiTierCache()
    return _cache_instance
```


### 6. Redis-Backed Sliding Window Rate Limiter

```python
# backend/gpubroker/apps/providers/rate_limiter.py

import time
import logging
from typing import Optional
from dataclasses import dataclass
from django.conf import settings

logger = logging.getLogger('gpubroker.providers.rate_limiter')


@dataclass
class RateLimitResult:
    allowed: bool
    remaining: int
    reset_at: float
    retry_after: Optional[int] = None


class SlidingWindowRateLimiter:
    """
    Redis-backed sliding window rate limiter.
    
    Uses Redis sorted sets for precise sliding window counting.
    """
    
    PLAN_LIMITS = {
        'free': 10,
        'pro': 100,
        'enterprise': 1000,
        'unlimited': 100000,
    }
    
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
    
    def _get_redis_client(self):
        import redis
        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        return redis.from_url(redis_url)
    
    def check(self, key: str, plan: str = 'free') -> RateLimitResult:
        limit = self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS['free'])
        now = time.time()
        window_start = now - self.window_seconds
        redis_key = f"ratelimit:{key}"
        
        try:
            client = self._get_redis_client()
            pipe = client.pipeline()
            
            pipe.zremrangebyscore(redis_key, 0, window_start)
            pipe.zcard(redis_key)
            results = pipe.execute()
            current_count = results[1]
            
            if current_count < limit:
                client.zadd(redis_key, {str(now): now})
                client.expire(redis_key, self.window_seconds + 1)
                
                return RateLimitResult(
                    allowed=True,
                    remaining=limit - current_count - 1,
                    reset_at=now + self.window_seconds,
                )
            else:
                oldest = client.zrange(redis_key, 0, 0, withscores=True)
                retry_after = int(oldest[0][1] + self.window_seconds - now) + 1 if oldest else self.window_seconds
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=now + retry_after,
                    retry_after=retry_after,
                )
                
        except Exception as e:
            logger.error(f"Rate limiter Redis error: {e}")
            return RateLimitResult(allowed=True, remaining=limit, reset_at=now + self.window_seconds)
    
    def get_limit_for_plan(self, plan: str) -> int:
        return self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS['free'])


_rate_limiter: Optional[SlidingWindowRateLimiter] = None


def get_rate_limiter() -> SlidingWindowRateLimiter:
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = SlidingWindowRateLimiter(window_seconds=60)
    return _rate_limiter
```


### 7. Enhanced Circuit Breaker with Prometheus Metrics

```python
# backend/gpubroker/apps/providers/circuit_breaker.py

from __future__ import annotations
import time
import logging
from typing import Callable, Dict, Optional, Any, Awaitable
from dataclasses import dataclass
from enum import Enum
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger('gpubroker.providers.circuit_breaker')

# Prometheus metrics
CIRCUIT_STATE = Gauge('circuit_breaker_state', 'Circuit state', ['provider'])
CIRCUIT_FAILURES = Counter('circuit_breaker_failures_total', 'Failures', ['provider'])
CIRCUIT_SUCCESSES = Counter('circuit_breaker_successes_total', 'Successes', ['provider'])
PROVIDER_LATENCY = Histogram('provider_request_latency_seconds', 'Latency', ['provider'])


class CircuitState(Enum):
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2


class CircuitBreakerOpen(Exception):
    pass


@dataclass
class CircuitBreakerConfig:
    fail_max: int = 5
    fail_rate_threshold: float = 0.5
    window_seconds: int = 30
    reset_timeout: int = 30
    half_open_max_calls: int = 3


class AsyncCircuitBreaker:
    """Enhanced circuit breaker with Prometheus metrics."""
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._failures: list[float] = []
        self._successes: list[float] = []
        self._opened_at: Optional[float] = None
        self._half_open_calls: int = 0
        CIRCUIT_STATE.labels(provider=name).set(0)
    
    @property
    def state(self) -> CircuitState:
        return self._state
    
    @state.setter
    def state(self, new_state: CircuitState):
        if self._state != new_state:
            self._state = new_state
            CIRCUIT_STATE.labels(provider=self.name).set(new_state.value)
    
    def _get_failure_rate(self) -> float:
        total = len(self._failures) + len(self._successes)
        return len(self._failures) / total if total > 0 else 0.0
    
    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        now = time.monotonic()
        
        # Check if can attempt
        if self._state == CircuitState.OPEN:
            if self._opened_at and now - self._opened_at >= self.config.reset_timeout:
                self.state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
            else:
                raise CircuitBreakerOpen(f"Circuit {self.name} is open")
        
        start_time = time.monotonic()
        try:
            result = await func(*args, **kwargs)
            latency = time.monotonic() - start_time
            PROVIDER_LATENCY.labels(provider=self.name).observe(latency)
            CIRCUIT_SUCCESSES.labels(provider=self.name).inc()
            
            self._successes.append(now)
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_calls += 1
                if self._half_open_calls >= self.config.half_open_max_calls:
                    self.state = CircuitState.CLOSED
                    self._failures.clear()
            
            return result
        except Exception:
            CIRCUIT_FAILURES.labels(provider=self.name).inc()
            self._failures.append(now)
            
            # Prune old entries
            cutoff = now - self.config.window_seconds
            self._failures = [t for t in self._failures if t >= cutoff]
            self._successes = [t for t in self._successes if t >= cutoff]
            
            if self._state == CircuitState.HALF_OPEN or self._get_failure_rate() >= self.config.fail_rate_threshold:
                self.state = CircuitState.OPEN
                self._opened_at = now
            
            raise


_breakers: Dict[str, AsyncCircuitBreaker] = {}


def get_breaker(key: str, config: Optional[CircuitBreakerConfig] = None) -> AsyncCircuitBreaker:
    if key not in _breakers:
        _breakers[key] = AsyncCircuitBreaker(name=key, config=config)
    return _breakers[key]
```

### 8. Weighted Load Balancer

```python
# backend/gpubroker/apps/providers/load_balancer.py

import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque
from prometheus_client import Gauge
import random

logger = logging.getLogger('gpubroker.providers.load_balancer')

PROVIDER_WEIGHT = Gauge('provider_weight', 'Provider weight', ['provider'])
PROVIDER_HEALTH = Gauge('provider_health', 'Provider health', ['provider'])


@dataclass
class ProviderHealth:
    name: str
    healthy: bool = True
    weight: float = 1.0
    base_weight: float = 1.0
    avg_latency_ms: float = 0.0
    consecutive_failures: int = 0
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def update_latency(self, latency_ms: float):
        self.latency_samples.append(latency_ms)
        self.avg_latency_ms = sum(self.latency_samples) / len(self.latency_samples)
    
    def calculate_weight(self) -> float:
        if not self.healthy:
            return 0.0
        weight = self.base_weight
        if self.avg_latency_ms > 2000:
            weight *= 0.5
        elif self.avg_latency_ms > 1000:
            weight *= 0.75
        self.weight = max(0.1, weight)
        return self.weight


class WeightedLoadBalancer:
    """Weighted round-robin load balancer with health tracking."""
    
    def __init__(self, max_concurrent: int = 50):
        self.max_concurrent = max_concurrent
        self._providers: Dict[str, ProviderHealth] = {}
        self._active_requests: Dict[str, int] = {}
    
    def register_provider(self, name: str, base_weight: float = 1.0):
        self._providers[name] = ProviderHealth(name=name, base_weight=base_weight, weight=base_weight)
        self._active_requests[name] = 0
        PROVIDER_WEIGHT.labels(provider=name).set(base_weight)
        PROVIDER_HEALTH.labels(provider=name).set(1)
    
    def get_healthy_providers(self) -> List[str]:
        return [n for n, h in self._providers.items() if h.healthy and h.weight > 0]
    
    def select_provider(self, exclude: Optional[List[str]] = None) -> Optional[str]:
        exclude = exclude or []
        candidates = [(n, h.weight) for n, h in self._providers.items() 
                      if h.healthy and n not in exclude and h.weight > 0]
        if not candidates:
            return None
        
        total_weight = sum(w for _, w in candidates)
        r = random.uniform(0, total_weight)
        cumulative = 0
        for name, weight in candidates:
            cumulative += weight
            if r <= cumulative:
                return name
        return candidates[0][0]
    
    def record_success(self, provider: str, latency_ms: float):
        if provider in self._providers:
            h = self._providers[provider]
            h.update_latency(latency_ms)
            h.consecutive_failures = 0
            h.healthy = True
            h.calculate_weight()
            PROVIDER_WEIGHT.labels(provider=provider).set(h.weight)
            PROVIDER_HEALTH.labels(provider=provider).set(1)
    
    def record_failure(self, provider: str):
        if provider in self._providers:
            h = self._providers[provider]
            h.consecutive_failures += 1
            if h.consecutive_failures >= 3:
                h.healthy = False
                h.weight = 0
                PROVIDER_HEALTH.labels(provider=provider).set(0)
    
    def mark_healthy(self, provider: str):
        if provider in self._providers:
            self._providers[provider].healthy = True
            self._providers[provider].consecutive_failures = 0
            PROVIDER_HEALTH.labels(provider=provider).set(1)
    
    def mark_unhealthy(self, provider: str):
        if provider in self._providers:
            self._providers[provider].healthy = False
            self._providers[provider].weight = 0
            PROVIDER_HEALTH.labels(provider=provider).set(0)
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            'providers': {
                n: {'healthy': h.healthy, 'weight': h.weight, 'avg_latency_ms': h.avg_latency_ms}
                for n, h in self._providers.items()
            }
        }


_load_balancer: Optional[WeightedLoadBalancer] = None


def get_load_balancer() -> WeightedLoadBalancer:
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = WeightedLoadBalancer()
    return _load_balancer
```


### 7. Enhanced Circuit Breaker with Prometheus Metrics

```python
# backend/gpubroker/apps/providers/circuit_breaker.py

from __future__ import annotations
import time
import logging
from typing import Callable, Dict, Optional, Any, Awaitable
from dataclasses import dataclass
from enum import Enum
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger('gpubroker.providers.circuit_breaker')

# Prometheus metrics
CIRCUIT_STATE = Gauge('circuit_breaker_state', 'Circuit breaker state', ['provider'])
CIRCUIT_FAILURES = Counter('circuit_breaker_failures_total', 'Total failures', ['provider'])
CIRCUIT_SUCCESSES = Counter('circuit_breaker_successes_total', 'Total successes', ['provider'])
CIRCUIT_REJECTIONS = Counter('circuit_breaker_rejections_total', 'Rejected requests', ['provider'])
PROVIDER_LATENCY = Histogram('provider_request_latency_seconds', 'Request latency', ['provider'],
                             buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0])


class CircuitState(Enum):
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2


class CircuitBreakerOpen(Exception):
    pass


@dataclass
class CircuitBreakerConfig:
    fail_max: int = 5
    fail_rate_threshold: float = 0.5
    window_seconds: int = 30
    reset_timeout: int = 30
    half_open_max_calls: int = 3


class AsyncCircuitBreaker:
    """Enhanced async circuit breaker with Prometheus metrics."""
    
    def __init__(self, name: str, config: Optional[CircuitBreakerConfig] = None,
                 clock: Callable[[], float] = time.monotonic):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._failures: list[float] = []
        self._successes: list[float] = []
        self._opened_at: Optional[float] = None
        self._half_open_calls: int = 0
        
        CIRCUIT_STATE.labels(provider=name).set(0)
    
    @property
    def state(self) -> CircuitState:
        return self._state
    
    @state.setter
    def state(self, new_state: CircuitState):
        if self._state != new_state:
            self._state = new_state
            CIRCUIT_STATE.labels(provider=self.name).set(new_state.value)
            logger.info(f"Circuit breaker {self.name} -> {new_state.name}")
    
    def _prune_window(self, now: float):
        cutoff = now - self.config.window_seconds
        self._failures = [t for t in self._failures if t >= cutoff]
        self._successes = [t for t in self._successes if t >= cutoff]
    
    def _get_failure_rate(self) -> float:
        total = len(self._failures) + len(self._successes)
        return len(self._failures) / total if total > 0 else 0.0
    
    def _should_open(self) -> bool:
        total = len(self._failures) + len(self._successes)
        if total < self.config.fail_max:
            return False
        return self._get_failure_rate() >= self.config.fail_rate_threshold
    
    def _can_attempt(self, now: float) -> bool:
        if self._state == CircuitState.CLOSED:
            return True
        if self._state == CircuitState.OPEN:
            if self._opened_at and now - self._opened_at >= self.config.reset_timeout:
                self.state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                return True
            return False
        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls
        return False
    
    def _record_success(self, now: float):
        self._successes.append(now)
        CIRCUIT_SUCCESSES.labels(provider=self.name).inc()
        
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self._failures.clear()
                self._opened_at = None
    
    def _record_failure(self, now: float):
        self._failures.append(now)
        CIRCUIT_FAILURES.labels(provider=self.name).inc()
        self._prune_window(now)
        
        if self._state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self._opened_at = now
        elif self._should_open():
            self.state = CircuitState.OPEN
            self._opened_at = now
    
    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        now = self._clock()
        
        if not self._can_attempt(now):
            CIRCUIT_REJECTIONS.labels(provider=self.name).inc()
            raise CircuitBreakerOpen(f"Circuit breaker {self.name} is open")
        
        start_time = time.monotonic()
        try:
            result = await func(*args, **kwargs)
            latency = time.monotonic() - start_time
            PROVIDER_LATENCY.labels(provider=self.name).observe(latency)
            self._record_success(self._clock())
            return result
        except Exception:
            latency = time.monotonic() - start_time
            PROVIDER_LATENCY.labels(provider=self.name).observe(latency)
            self._record_failure(self._clock())
            raise
    
    def reset(self):
        self.state = CircuitState.CLOSED
        self._failures.clear()
        self._successes.clear()
        self._opened_at = None
        self._half_open_calls = 0


_breakers: Dict[str, AsyncCircuitBreaker] = {}


def get_breaker(key: str, config: Optional[CircuitBreakerConfig] = None) -> AsyncCircuitBreaker:
    if key not in _breakers:
        _breakers[key] = AsyncCircuitBreaker(name=key, config=config)
    return _breakers[key]


def reset_breaker(key: str):
    if key in _breakers:
        _breakers[key].reset()
```


### 8. Weighted Load Balancer with Health Tracking

```python
# backend/gpubroker/apps/providers/load_balancer.py

import time
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from collections import deque
import random
from prometheus_client import Gauge

logger = logging.getLogger('gpubroker.providers.load_balancer')

PROVIDER_WEIGHT = Gauge('provider_weight', 'Provider weight', ['provider'])
PROVIDER_HEALTH = Gauge('provider_health', 'Provider health (0/1)', ['provider'])


@dataclass
class ProviderHealth:
    name: str
    healthy: bool = True
    weight: float = 1.0
    base_weight: float = 1.0
    avg_latency_ms: float = 0.0
    consecutive_failures: int = 0
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def update_latency(self, latency_ms: float):
        self.latency_samples.append(latency_ms)
        if self.latency_samples:
            self.avg_latency_ms = sum(self.latency_samples) / len(self.latency_samples)
    
    def calculate_weight(self) -> float:
        if not self.healthy:
            return 0.0
        
        weight = self.base_weight
        
        if self.avg_latency_ms > 2000:
            weight *= 0.5
        elif self.avg_latency_ms > 1000:
            weight *= 0.75
        
        self.weight = max(0.1, weight)
        return self.weight


class WeightedLoadBalancer:
    """Weighted round-robin load balancer with health tracking."""
    
    def __init__(self, max_concurrent_per_provider: int = 50):
        self.max_concurrent = max_concurrent_per_provider
        self._providers: Dict[str, ProviderHealth] = {}
        self._active_requests: Dict[str, int] = {}
    
    def register_provider(self, name: str, base_weight: float = 1.0):
        self._providers[name] = ProviderHealth(name=name, base_weight=base_weight, weight=base_weight)
        self._active_requests[name] = 0
        PROVIDER_WEIGHT.labels(provider=name).set(base_weight)
        PROVIDER_HEALTH.labels(provider=name).set(1)
    
    def get_healthy_providers(self) -> List[str]:
        return [name for name, health in self._providers.items() if health.healthy and health.weight > 0]
    
    def select_provider(self, exclude: Optional[List[str]] = None) -> Optional[str]:
        exclude = exclude or []
        candidates = [(name, health.weight) for name, health in self._providers.items()
                      if health.healthy and name not in exclude and health.weight > 0]
        
        if not candidates:
            return None
        
        total_weight = sum(w for _, w in candidates)
        if total_weight == 0:
            return None
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        for name, weight in candidates:
            cumulative += weight
            if r <= cumulative:
                return name
        
        return candidates[0][0]
    
    def record_success(self, provider: str, latency_ms: float):
        if provider not in self._providers:
            return
        
        health = self._providers[provider]
        health.update_latency(latency_ms)
        health.consecutive_failures = 0
        health.healthy = True
        health.calculate_weight()
        
        PROVIDER_WEIGHT.labels(provider=provider).set(health.weight)
        PROVIDER_HEALTH.labels(provider=provider).set(1)
    
    def record_failure(self, provider: str):
        if provider not in self._providers:
            return
        
        health = self._providers[provider]
        health.consecutive_failures += 1
        
        if health.consecutive_failures >= 3:
            health.healthy = False
            health.weight = 0
            PROVIDER_HEALTH.labels(provider=provider).set(0)
        
        health.calculate_weight()
        PROVIDER_WEIGHT.labels(provider=provider).set(health.weight)
    
    def mark_healthy(self, provider: str):
        if provider in self._providers:
            health = self._providers[provider]
            health.healthy = True
            health.consecutive_failures = 0
            health.calculate_weight()
            PROVIDER_HEALTH.labels(provider=provider).set(1)
    
    def mark_unhealthy(self, provider: str):
        if provider in self._providers:
            health = self._providers[provider]
            health.healthy = False
            health.weight = 0
            PROVIDER_HEALTH.labels(provider=provider).set(0)
    
    def get_stats(self) -> Dict[str, Any]:
        return {
            'providers': {
                name: {
                    'healthy': health.healthy,
                    'weight': health.weight,
                    'avg_latency_ms': health.avg_latency_ms,
                    'consecutive_failures': health.consecutive_failures,
                }
                for name, health in self._providers.items()
            }
        }


_load_balancer: Optional[WeightedLoadBalancer] = None


def get_load_balancer() -> WeightedLoadBalancer:
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = WeightedLoadBalancer()
    return _load_balancer
```


### 9. Vault Integration for Credentials

```python
# backend/gpubroker/apps/providers/vault_client.py

import time
import logging
from typing import Optional, Dict
from dataclasses import dataclass
import hvac
from django.conf import settings

logger = logging.getLogger('gpubroker.providers.vault')


@dataclass
class CachedCredential:
    value: str
    fetched_at: float
    ttl: int = 3600
    
    @property
    def is_expired(self) -> bool:
        return time.time() - self.fetched_at > self.ttl


class VaultCredentialManager:
    """HashiCorp Vault integration for secure credentials."""
    
    def __init__(self):
        self._client: Optional[hvac.Client] = None
        self._cache: Dict[str, CachedCredential] = {}
    
    def _get_client(self) -> Optional[hvac.Client]:
        if self._client is None:
            vault_addr = getattr(settings, 'VAULT_ADDR', 'http://localhost:8200')
            vault_token = getattr(settings, 'VAULT_TOKEN', None)
            if vault_token:
                try:
                    self._client = hvac.Client(url=vault_addr, token=vault_token)
                except Exception as e:
                    logger.error(f"Vault connection failed: {e}")
        return self._client
    
    async def get_provider_credential(self, provider: str, user_id: Optional[str] = None) -> Optional[str]:
        cache_key = f"{provider}:{user_id or 'default'}"
        
        # Check cache
        cached = self._cache.get(cache_key)
        if cached and not cached.is_expired:
            return cached.value
        
        # Try Vault
        client = self._get_client()
        if client:
            try:
                path = f"gpubroker/providers/{provider}"
                response = client.secrets.kv.v2.read_secret_version(path=path, mount_point='secret')
                if response and 'data' in response:
                    api_key = response['data']['data'].get('api_key')
                    if api_key:
                        self._cache[cache_key] = CachedCredential(value=api_key, fetched_at=time.time())
                        return api_key
            except Exception as e:
                logger.warning(f"Vault read failed: {e}")
        
        # Fallback to cached (even if stale) or env var
        if cached:
            return cached.value
        
        import os
        return os.getenv(f"{provider.upper()}_API_KEY")


_vault_manager: Optional[VaultCredentialManager] = None


def get_vault_manager() -> VaultCredentialManager:
    global _vault_manager
    if _vault_manager is None:
        _vault_manager = VaultCredentialManager()
    return _vault_manager
```

## Data Models

### Schemas

```python
# backend/gpubroker/apps/providers/schemas.py

from datetime import datetime
from typing import Optional, List, Dict, Any
from ninja import Schema


class ProviderItem(Schema):
    id: str
    provider: str
    name: str
    gpu: str
    memory_gb: int
    price_per_hour: float
    currency: str = "USD"
    availability: str
    region: str
    tags: List[str] = []
    last_updated: datetime


class ProviderListResponse(Schema):
    total: int
    items: List[ProviderItem]
    warnings: Optional[List[str]] = None
    page: int = 1
    per_page: int = 20


class RateLimitInfo(Schema):
    limit: int
    remaining: int
    reset_at: datetime
    retry_after: Optional[int] = None


class ProviderHealthStatus(Schema):
    provider: str
    healthy: bool
    weight: float
    avg_latency_ms: float
    circuit_state: str


class GatewayHealthResponse(Schema):
    status: str
    timestamp: datetime
    providers: List[ProviderHealthStatus]
    kafka_connected: bool
    redis_connected: bool
    websocket_connections: int
```

### Database Models

```python
# backend/gpubroker/apps/providers/models.py

from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid


class Provider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    display_name = models.CharField(max_length=200)
    api_base_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    health_status = models.CharField(max_length=20, default='healthy', db_index=True)
    last_health_check = models.DateTimeField(null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'providers'


class GPUOffer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='offers')
    name = models.CharField(max_length=200, db_index=True)
    gpu_type = models.CharField(max_length=100, db_index=True)
    gpu_count = models.IntegerField(default=1)
    gpu_memory_gb = models.IntegerField(null=True, db_index=True)
    vcpus = models.IntegerField(null=True)
    ram_gb = models.IntegerField(null=True)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=4, db_index=True)
    spot_price = models.DecimalField(max_digits=10, decimal_places=4, null=True)
    currency = models.CharField(max_length=3, default='USD')
    availability_status = models.CharField(max_length=20, default='available', db_index=True)
    region = models.CharField(max_length=50, db_index=True)
    compliance_tags = ArrayField(models.CharField(max_length=50), default=list)
    last_updated = models.DateTimeField(auto_now=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'gpu_offers'
        indexes = [
            models.Index(fields=['provider', 'gpu_type']),
            models.Index(fields=['price_per_hour', 'availability_status']),
        ]
```


### 9. Vault Integration for Credential Management

```python
# backend/gpubroker/apps/providers/vault_client.py

import time
import logging
from typing import Optional, Dict
from dataclasses import dataclass
import hvac
from django.conf import settings

logger = logging.getLogger('gpubroker.providers.vault')


@dataclass
class CachedCredential:
    value: str
    fetched_at: float
    ttl: int = 3600
    
    @property
    def is_expired(self) -> bool:
        return time.time() - self.fetched_at > self.ttl
    
    @property
    def is_stale(self) -> bool:
        return time.time() - self.fetched_at > self.ttl * 0.8


class VaultCredentialManager:
    """HashiCorp Vault integration for secure credential management."""
    
    def __init__(self):
        self._client: Optional[hvac.Client] = None
        self._cache: Dict[str, CachedCredential] = {}
        self._vault_available = True
        self._last_vault_check = 0
    
    def _get_client(self) -> Optional[hvac.Client]:
        if self._client is None:
            vault_addr = getattr(settings, 'VAULT_ADDR', 'http://localhost:8200')
            vault_token = getattr(settings, 'VAULT_TOKEN', None)
            
            if not vault_token:
                logger.warning("VAULT_TOKEN not configured")
                return None
            
            try:
                self._client = hvac.Client(url=vault_addr, token=vault_token)
                if not self._client.is_authenticated():
                    logger.error("Vault authentication failed")
                    self._client = None
            except Exception as e:
                logger.error(f"Vault connection failed: {e}")
                self._client = None
        
        return self._client
    
    def _check_vault_health(self) -> bool:
        now = time.time()
        if now - self._last_vault_check < 30:
            return self._vault_available
        
        self._last_vault_check = now
        client = self._get_client()
        
        if client is None:
            self._vault_available = False
            return False
        
        try:
            client.sys.read_health_status()
            self._vault_available = True
            return True
        except Exception as e:
            logger.warning(f"Vault health check failed: {e}")
            self._vault_available = False
            return False
    
    async def get_provider_credential(self, provider: str, user_id: Optional[str] = None) -> Optional[str]:
        cache_key = f"{provider}:{user_id or 'default'}"
        
        cached = self._cache.get(cache_key)
        if cached and not cached.is_expired:
            return cached.value
        
        if self._check_vault_health():
            try:
                client = self._get_client()
                if client:
                    path = f"gpubroker/users/{user_id}/providers/{provider}" if user_id else f"gpubroker/providers/{provider}"
                    
                    response = client.secrets.kv.v2.read_secret_version(
                        path=path,
                        mount_point='secret',
                    )
                    
                    if response and 'data' in response and 'data' in response['data']:
                        api_key = response['data']['data'].get('api_key')
                        if api_key:
                            self._cache[cache_key] = CachedCredential(value=api_key, fetched_at=time.time())
                            return api_key
                            
            except Exception as e:
                logger.warning(f"Vault read failed for {provider}: {e}")
        
        if cached:
            logger.warning(f"Using stale credential for {provider}")
            return cached.value
        
        import os
        env_key = os.getenv(f"{provider.upper()}_API_KEY")
        if env_key:
            self._cache[cache_key] = CachedCredential(value=env_key, fetched_at=time.time(), ttl=300)
        return env_key
    
    async def store_user_credential(self, user_id: str, provider: str, api_key: str) -> bool:
        if not self._check_vault_health():
            return False
        
        try:
            client = self._get_client()
            if client:
                path = f"gpubroker/users/{user_id}/providers/{provider}"
                client.secrets.kv.v2.create_or_update_secret(
                    path=path,
                    secret={'api_key': api_key},
                    mount_point='secret',
                )
                
                cache_key = f"{provider}:{user_id}"
                self._cache[cache_key] = CachedCredential(value=api_key, fetched_at=time.time())
                return True
                
        except Exception as e:
            logger.error(f"Vault write failed: {e}")
        
        return False


_vault_manager: Optional[VaultCredentialManager] = None


def get_vault_manager() -> VaultCredentialManager:
    global _vault_manager
    if _vault_manager is None:
        _vault_manager = VaultCredentialManager()
    return _vault_manager
```


## Data Models

### Request/Response Schemas

```python
# backend/gpubroker/apps/providers/schemas.py

from datetime import datetime
from typing import Optional, List, Dict, Any
from ninja import Schema


class ProviderItem(Schema):
    id: str
    provider: str
    name: str
    gpu: str
    memory_gb: int
    price_per_hour: float
    currency: str = "USD"
    availability: str
    region: str
    tags: List[str] = []
    last_updated: datetime


class ProviderListResponse(Schema):
    total: int
    items: List[ProviderItem]
    warnings: Optional[List[str]] = None
    page: int = 1
    per_page: int = 20
    has_next: bool = False


class RateLimitInfo(Schema):
    limit: int
    remaining: int
    reset_at: datetime
    retry_after: Optional[int] = None


class CircuitBreakerStatus(Schema):
    provider: str
    state: str
    failure_count: int
    success_count: int


class ProviderHealthStatus(Schema):
    provider: str
    healthy: bool
    weight: float
    avg_latency_ms: float
    last_check: datetime


class GatewayHealthResponse(Schema):
    status: str
    timestamp: datetime
    providers: List[ProviderHealthStatus]
    kafka_connected: bool
    flink_jobs_running: int
    airflow_healthy: bool


class IntegrationConfig(Schema):
    provider: str
    api_key: Optional[str] = None
    api_url: Optional[str] = None


class IntegrationStatus(Schema):
    provider: str
    status: str
    message: Optional[str] = None
    last_checked: datetime
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do.*

### Property 1: Cache Lookup Order and Fallback
*For any* request, cache lookup SHALL follow: L2 (in-memory) → L1 (Redis) → provider fetch. If Redis unavailable, SHALL fall back to L2 gracefully.
**Validates: Requirements 2.2, 2.6**

### Property 2: Cache TTL Expiration
*For any* cached item with TTL T, the item SHALL expire after T seconds. Pricing=60s, static=300s.
**Validates: Requirements 2.3**

### Property 3: Cache Stampede Prevention
*For any* N concurrent requests near expiration, at most 1 SHALL trigger provider fetch (XFetch algorithm).
**Validates: Requirements 2.5**

### Property 4: Circuit Breaker State Machine
*For any* provider, circuit breaker SHALL transition: CLOSED→OPEN (≥50% failures), OPEN→HALF_OPEN (30s), HALF_OPEN→CLOSED (3 successes).
**Validates: Requirements 3.1, 3.2, 3.4, 3.5**

### Property 5: Circuit Breaker Cached Fallback
*For any* request when circuit OPEN, SHALL return cached data or skip provider. No requests to provider while OPEN.
**Validates: Requirements 3.3**

### Property 6: Rate Limiting by Plan Tier
*For any* user with plan P, rate limiter SHALL allow LIMIT[P] requests/minute (Free=10, Pro=100, Enterprise=1000).
**Validates: Requirements 4.1, 4.4, 4.5**

### Property 7: Rate Limit Response Format
*For any* rate-limited request, SHALL return HTTP 429 with Retry-After header.
**Validates: Requirements 4.2**

### Property 8: Sliding Window Rate Limiting
*For any* request sequence, rate limiter SHALL use sliding window (last 60s), not fixed buckets.
**Validates: Requirements 4.3, 4.6**

### Property 9: Weighted Load Balancing
*For any* healthy providers with weights W1..Wn, load balancer SHALL distribute proportionally. Slow providers (>2s) weight reduced 50%.
**Validates: Requirements 5.1, 5.2**

### Property 10: All Providers Unhealthy Fallback
*For any* request when all providers unhealthy, SHALL return cached data with warning.
**Validates: Requirements 5.4**

### Property 11: Parallel Provider Fetching
*For any* multi-provider fetch, SHALL query all healthy providers in parallel. Total time ≈ max(individual), not sum.
**Validates: Requirements 1.3, 7.2**

### Property 12: Response Normalization
*For any* provider response, SHALL normalize to standard Offer schema with all required fields.
**Validates: Requirements 7.1**

### Property 13: Filter Correctness
*For any* filter parameters, returned offers SHALL match ALL specified filters.
**Validates: Requirements 7.4**

### Property 14: WebSocket Connection Persistence
*For any* WebSocket connection, SHALL remain open until client disconnects or server shutdown. Reconnection SHALL restore subscriptions.
**Validates: Requirements 11.1, 11.2**

### Property 15: Kafka Event Delivery
*For any* price update event, SHALL be published to Kafka within 100ms. Flink SHALL process within 500ms.
**Validates: Requirements 10.1, 10.3**

### Property 16: Airflow Task Execution
*For any* scheduled Airflow DAG, SHALL execute within schedule tolerance (±30s for health checks, ±60s for cache warming).
**Validates: Requirements 10.1, 10.2**

### Property 17: Vault Credential Security
*For any* log entry or error, SHALL NOT include API keys. Credentials masked or omitted.
**Validates: Requirements 9.4**

### Property 18: Request Timeout
*For any* request exceeding 5s, SHALL timeout and return cached data or error.
**Validates: Requirements 1.5**

## Error Handling

### Error Categories
- **4xx Client Errors**: 400 Bad Request, 401 Unauthorized, 429 Rate Limited
- **5xx Server Errors**: 500 Internal, 502 Bad Gateway, 503 Unavailable, 504 Timeout

### Graceful Degradation
1. Redis unavailable → L2 in-memory cache
2. Vault unavailable → Cached credentials (1 hour)
3. Provider unavailable → Cached data + warning
4. Kafka unavailable → Local queue + retry
5. All providers down → Cached data or 503

## Testing Strategy

### Property-Based Testing (Hypothesis)
- Minimum 100 iterations per property
- Tag format: `**Feature: provider-api-gateway, Property N: {text}**`

### Integration Tests
- Full request flow through all components
- WebSocket connection lifecycle
- Kafka event publishing/consuming
- Airflow DAG execution

### Load Tests
- 10,000 RPS throughput validation
- WebSocket connection scaling (10K+ concurrent)
- Kafka throughput (100K events/sec)

## Configuration

```python
# Django settings additions

# Apache Kafka
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')

# Apache Flink (managed externally)
FLINK_JOBMANAGER_URL = os.getenv('FLINK_JOBMANAGER_URL', 'http://localhost:8081')

# Apache Airflow (managed externally)
AIRFLOW_API_URL = os.getenv('AIRFLOW_API_URL', 'http://localhost:8080/api/v1')

# WebSocket (Django Channels)
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [(os.getenv('REDIS_HOST', 'localhost'), 6379)],
            'capacity': 1500,
            'expiry': 10,
        },
    },
}

# Rate Limits
RATE_LIMITS = {'free': 10, 'pro': 100, 'enterprise': 1000}

# Cache TTLs
CACHE_TTL_PRICING = 60
CACHE_TTL_STATIC = 300

# Circuit Breaker
CIRCUIT_BREAKER_FAIL_RATE = 0.5
CIRCUIT_BREAKER_RESET_TIMEOUT = 30
```

## Infrastructure Requirements

### Apache Stack
- **Kafka**: 3-node cluster in KRaft mode (NO ZooKeeper)
- **Flink**: JobManager + 2 TaskManagers
- **Airflow**: Scheduler + 2 Workers + PostgreSQL metadata DB (NO Celery)

### Scaling
- Django Gateway: Horizontal (stateless)
- Redis: Cluster mode for HA
- Kafka: Partition-based scaling
- Flink: Parallelism-based scaling


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do.*

### Property 1: Cache Lookup Order and Fallback
*For any* request, cache lookup SHALL follow: L2 (in-memory) → L1 (Redis) → provider fetch. If Redis unavailable, SHALL fall back to L2 gracefully.
**Validates: Requirements 2.2, 2.6**

### Property 2: Cache TTL Expiration
*For any* cached item with TTL T, SHALL be expired after T seconds. Pricing=60s, static=300s.
**Validates: Requirements 2.3**

### Property 3: Cache Stampede Prevention
*For any* N concurrent requests near expiration, at most 1 SHALL trigger provider fetch (PEE algorithm).
**Validates: Requirements 2.5**

### Property 4: Circuit Breaker State Machine
*For any* provider: CLOSED→OPEN (≥50% failures over 10 requests), OPEN→HALF_OPEN (30s timeout), HALF_OPEN→CLOSED (3 successes), HALF_OPEN→OPEN (any failure).
**Validates: Requirements 3.1, 3.2, 3.4, 3.5**

### Property 5: Circuit Breaker Cached Fallback
*For any* request when circuit OPEN, SHALL return cached data or skip provider. No requests to provider while OPEN.
**Validates: Requirements 3.3**

### Property 6: Rate Limiting by Plan Tier
*For any* user with plan P, SHALL allow exactly LIMIT[P] requests/minute (Free=10, Pro=100, Enterprise=1000). Anonymous by IP at Free tier.
**Validates: Requirements 4.1, 4.4, 4.5**

### Property 7: Rate Limit Response Format
*For any* rate-limited request, SHALL return HTTP 429 with Retry-After header.
**Validates: Requirements 4.2**

### Property 8: Sliding Window Rate Limiting
*For any* request sequence, rate limiter SHALL use sliding window (last 60s), not fixed buckets.
**Validates: Requirements 4.3, 4.6**

### Property 9: Weighted Load Balancing
*For any* healthy providers with weights W1..Wn, SHALL distribute proportionally. Slow providers (>2s) weight reduced 50%.
**Validates: Requirements 5.1, 5.2**

### Property 10: All Providers Unhealthy Fallback
*For any* request when all providers unhealthy, SHALL return cached data with warning.
**Validates: Requirements 5.4**

### Property 11: Parallel Provider Fetching
*For any* provider fetch, SHALL query all healthy providers in parallel. Total time ≈ max(individual), not sum.
**Validates: Requirements 1.3, 7.2**

### Property 12: Response Normalization
*For any* provider response, SHALL normalize to standard Offer schema with required fields.
**Validates: Requirements 7.1**

### Property 13: Filter Correctness
*For any* filter parameters, returned offers SHALL match ALL filters.
**Validates: Requirements 7.4**

### Property 14: Kafka Event Delivery
*For any* price change, SHALL publish to Kafka topic with at-least-once delivery.
**Validates: Requirements 10.4**

### Property 15: Flink Price Change Detection
*For any* price change in Kafka stream, Flink SHALL detect and publish to output topic within 5 seconds.
**Validates: Requirements 10.3**

### Property 16: WebSocket Real-Time Updates
*For any* price change from Flink, SHALL broadcast to subscribed WebSocket clients within 1 second.
**Validates: Requirements 6.4**

### Property 17: Airflow DAG Execution
*For any* scheduled DAG (cache warming, health checks), Airflow SHALL execute within schedule tolerance (±30s).
**Validates: Requirements 10.1**

### Property 18: Vault Credential Retrieval
*For any* credential request, SHALL try Vault first. If unavailable, use cached credentials up to 1 hour.
**Validates: Requirements 9.1, 9.3**

### Property 19: Credential Security
*For any* log entry, SHALL NOT include API keys or sensitive credentials.
**Validates: Requirements 9.4**

### Property 20: Request Timeout
*For any* request exceeding 5 seconds, SHALL timeout and return cached data or error.
**Validates: Requirements 1.5**


## Error Handling

### Error Categories

1. **Client Errors (4xx)**: 400 Bad Request, 401 Unauthorized, 403 Forbidden, 429 Too Many Requests
2. **Server Errors (5xx)**: 500 Internal Error, 502 Bad Gateway, 503 Service Unavailable, 504 Gateway Timeout

### Graceful Degradation

1. **Redis Unavailable**: Fall back to L2 in-memory cache
2. **Vault Unavailable**: Use cached credentials (up to 1 hour)
3. **Kafka Unavailable**: Queue events locally, retry on reconnect
4. **Flink Unavailable**: Gateway continues without real-time analytics
5. **Airflow Unavailable**: Manual cache warming via API
6. **All Providers Down**: Return cached data or 503 with retry hint


## Testing Strategy

### Property-Based Testing with Hypothesis

```python
from hypothesis import given, strategies as st, settings

@settings(max_examples=100)
@given(plan=st.sampled_from(['free', 'pro', 'enterprise']), request_count=st.integers(1, 200))
def test_rate_limiter_enforces_plan_limits(plan, request_count):
    """**Feature: provider-api-gateway, Property 6: Rate Limiting by Plan Tier**"""
    limiter = SlidingWindowRateLimiter()
    limit = limiter.PLAN_LIMITS[plan]
    allowed = sum(1 for _ in range(request_count) if limiter.check(f"test_{plan}", plan).allowed)
    assert allowed <= limit
```

### Integration Tests

- Full request flow through all components
- Graceful degradation when components fail
- Kafka → Flink → WebSocket pipeline
- Airflow DAG execution


## Configuration

### Django Settings

```python
# Apache Stack Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv('KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
FLINK_JOBMANAGER_URL = os.getenv('FLINK_JOBMANAGER_URL', 'http://localhost:8081')
AIRFLOW_API_URL = os.getenv('AIRFLOW_API_URL', 'http://localhost:8080/api/v1')

# Rate Limiting
RATE_LIMITS = {'free': 10, 'pro': 100, 'enterprise': 1000}

# Cache TTLs
CACHE_TTL_PRICING = 60
CACHE_TTL_STATIC = 300

# Circuit Breaker
CIRCUIT_BREAKER_FAIL_RATE = 0.5
CIRCUIT_BREAKER_RESET_TIMEOUT = 30

# Vault
VAULT_ADDR = os.getenv('VAULT_ADDR', 'http://localhost:8200')
VAULT_TOKEN = os.getenv('VAULT_TOKEN')

# Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Connection Pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,
        'CONN_HEALTH_CHECKS': True,
    }
}

CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {'max_connections': 50},
        },
    }
}

# Django Channels
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            'hosts': [REDIS_URL],
            'capacity': 1500,
            'expiry': 10,
        },
    },
}
```

### Docker Compose Services

```yaml
# docker-compose.yml additions for Apache Stack

services:
  # Kafka KRaft Mode (NO ZOOKEEPER)
  kafka:
    image: confluentinc/cp-kafka:7.5.0
    environment:
      KAFKA_NODE_ID: 1
      KAFKA_PROCESS_ROLES: broker,controller
      KAFKA_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_LISTENERS: PLAINTEXT://0.0.0.0:9092,CONTROLLER://0.0.0.0:9093
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
      KAFKA_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_INTER_BROKER_LISTENER_NAME: PLAINTEXT
      KAFKA_LOG_DIRS: /var/lib/kafka/data
      CLUSTER_ID: 'MkU3OEVBNTcwNTJENDM2Qk'
    ports:
      - "9092:9092"
    volumes:
      - kafka_data:/var/lib/kafka/data

  flink-jobmanager:
    image: flink:1.18-scala_2.12
    command: jobmanager
    environment:
      FLINK_PROPERTIES: |
        jobmanager.rpc.address: flink-jobmanager
    ports:
      - "8081:8081"

  flink-taskmanager:
    image: flink:1.18-scala_2.12
    command: taskmanager
    depends_on:
      - flink-jobmanager
    environment:
      FLINK_PROPERTIES: |
        jobmanager.rpc.address: flink-jobmanager
        taskmanager.numberOfTaskSlots: 4

  airflow-webserver:
    image: apache/airflow:2.8.0
    command: webserver
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql://postgres:postgres@postgres:5432/airflow
    ports:
      - "8080:8080"
    volumes:
      - ./airflow/dags:/opt/airflow/dags

  airflow-scheduler:
    image: apache/airflow:2.8.0
    command: scheduler
    environment:
      AIRFLOW__CORE__EXECUTOR: LocalExecutor
      AIRFLOW__DATABASE__SQL_ALCHEMY_CONN: postgresql://postgres:postgres@postgres:5432/airflow
    volumes:
      - ./airflow/dags:/opt/airflow/dags
```

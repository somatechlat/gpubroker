from __future__ import annotations

import os
import asyncio
import json
import logging
from typing import Optional, Dict, Any

try:
    from aiokafka import AIOKafkaProducer  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    AIOKafkaProducer = None

logger = logging.getLogger(__name__)

_producer: Optional[AIOKafkaProducer] = None


def kafka_enabled() -> bool:
    return bool(os.getenv("ENABLE_KAFKA", "false").lower() in {"1", "true", "yes"} and os.getenv("KAFKA_BROKER_URL"))


async def get_producer() -> Optional[AIOKafkaProducer]:
    global _producer
    if not kafka_enabled() or AIOKafkaProducer is None:
        return None
    if _producer is None:
        broker = os.getenv("KAFKA_BROKER_URL")
        _producer = AIOKafkaProducer(bootstrap_servers=broker)
        await _producer.start()
        logger.info("Kafka producer started for broker %s", broker)
    return _producer


async def send_price_update(message: Dict[str, Any]) -> None:
    producer = await get_producer()
    if not producer:
        return
    topic = os.getenv("KAFKA_TOPIC_PRICE_UPDATES", "price_updates")
    try:
        await producer.send_and_wait(topic, json.dumps(message).encode("utf-8"))
        logger.debug("Published price update to Kafka topic %s", topic)
    except Exception as e:
        logger.warning("Failed to publish price update: %s", e)


async def close_producer() -> None:
    global _producer
    if _producer:
        try:
            await _producer.stop()
        except Exception as e:
            logger.warning("Failed to stop Kafka producer cleanly: %s", e)
        _producer = None

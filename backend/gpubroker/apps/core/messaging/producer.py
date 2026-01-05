import json
import logging
import os
from kafka import KafkaProducer as PythonKafkaProducer
from django.conf import settings

logger = logging.getLogger(__name__)

class KafkaProducer:
    _instance = None
    _producer = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(KafkaProducer, cls).__new__(cls)
            cls._instance._initialize_producer()
        return cls._instance

    def _initialize_producer(self):
        """Initialize the Kafka producer with settings."""
        brokers = getattr(settings, 'KAFKA_BROKERS', 'kafka:9092')
        if not brokers:
            logger.warning("KAFKA_BROKERS not configured. Kafka producer disabled.")
            return

        try:
            self._producer = PythonKafkaProducer(
                bootstrap_servers=brokers.split(','),
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                retries=3
            )
            logger.info(f"Kafka Producer connected to: {brokers}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka Producer: {e}")
            self._producer = None

    def send(self, topic, key, value):
        """
        Send a message to a Kafka topic.
        
        Args:
            topic (str): The target topic.
            key (str): The partition key (usually ID).
            value (dict): The payload dictionary.
        """
        if not self._producer:
            # Try to reconnect lazily if failed initially
            self._initialize_producer()
            if not self._producer:
                logger.error("Kafka Producer not available. Message dropped.")
                return 

        try:
            future = self._producer.send(
                topic, 
                key=key.encode('utf-8') if key else None, 
                value=value
            )
            # We don't wait for future here to be non-blocking, 
            # but in robust systems we might handle callbacks.
            return future
        except Exception as e:
            logger.error(f"Failed to send Kafka message to {topic}: {e}")

# Global instance
producer = KafkaProducer()

"""
Provider Signals

Kafka event production for Provider model changes.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

# Lazy import to avoid circular dependencies
def get_producer():
    """Get Kafka producer from messaging module."""
    try:
        from gpubrokerpod.gpubrokerapp.apps.providers.messaging import producer
        return producer
    except ImportError:
        logger.warning("Kafka producer not available - messaging module not found")
        return None


@receiver(post_save, sender='providers.Provider')
def provider_event_producer(sender, instance, created, **kwargs):
    """
    Produce a Kafka message when a Provider is created or updated.
    Topic: gpubroker.provider.events
    
    This signal is automatically connected when the providers app is loaded.
    """
    # Skip if this is a fixture load or migration
    if kwargs.get('raw', False):
        return
    
    topic = 'gpubroker.provider.events'
    event_type = 'PROVIDER_CREATED' if created else 'PROVIDER_UPDATED'
    
    # Build payload - handle potential missing attributes gracefully
    payload = {
        'event': event_type,
        'provider_id': str(instance.id),
        'name': getattr(instance, 'name', 'Unknown'),
        'country': getattr(instance, 'country', ''),
        'gpu_type': getattr(instance, 'gpu_type', ''),
        'total_gpus': getattr(instance, 'total_gpus', 0),
        'price_per_hour': float(getattr(instance, 'price_per_hour', 0) or 0.0),
        'status': getattr(instance, 'status', 'unknown')
    }
    
    # Try to send to Kafka
    producer = get_producer()
    if producer is None:
        logger.debug(f"Would send Kafka event {event_type} for Provider {instance.id} (producer unavailable)")
        return
    
    try:
        producer.send(topic, key=str(instance.id), value=payload)
        logger.info(f"Published Kafka event {event_type} for Provider {instance.id}")
    except Exception as e:
        logger.error(f"Failed to publish Kafka event for Provider {instance.id}: {e}")

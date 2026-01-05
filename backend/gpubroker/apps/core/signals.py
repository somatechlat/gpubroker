from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Provider
from .messaging.producer import producer
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Provider)
def provider_event_producer(sender, instance, created, **kwargs):
    """
    Produce a Kafka message when a Provider is created or updated.
    Topic: gpubroker.provider.events
    """
    topic = 'gpubroker.provider.events'
    event_type = 'PROVIDER_CREATED' if created else 'PROVIDER_UPDATED'
    
    payload = {
        'event': event_type,
        'provider_id': str(instance.id),
        'name': instance.name,
        'country': instance.country,
        'gpu_type': instance.gpu_type,
        'total_gpus': instance.total_gpus,
        'price_per_hour': float(instance.price_per_hour) if instance.price_per_hour else 0.0,
        'status': instance.status
    }
    
    try:
        producer.send(topic, key=str(instance.id), value=payload)
        logger.info(f"Published Kafka event {event_type} for Provider {instance.id}")
    except Exception as e:
        logger.error(f"Failed to publish Kafka event: {e}")

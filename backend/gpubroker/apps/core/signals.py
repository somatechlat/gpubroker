"""
Core Infrastructure Signals

NOTE: This file is deprecated. Signals should be defined in the app where the model lives.
This file exists for backward compatibility but is not loaded by default.

The provider_event_producer signal has been moved to:
backend/gpubroker/gpubrokerpod/gpubrokerapp/apps/providers/signals.py

To use signals from this file, you would need to:
1. Create apps/core/models.py with Provider model reference
2. Uncomment the ready() method in apps/core/apps.py
3. Import this module in ready()

However, the recommended approach is to keep signals with their models.
"""
import logging

logger = logging.getLogger(__name__)

# Placeholder - actual signal moved to providers app
def provider_event_producer(sender, instance, created, **kwargs):
    """
    DEPRECATED: This signal has been moved to the providers app.
    This function is kept for reference only.
    """
    logger.warning(
        "provider_event_producer called from deprecated location. "
        "Signal should be in gpubrokerpod.gpubrokerapp.apps.providers.signals"
    )

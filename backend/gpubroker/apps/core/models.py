"""
Core Infrastructure Models

This file exists to satisfy Django's app structure requirements.
The core app provides infrastructure services (messaging, utilities) but does not
define its own database models.

All actual data models are defined in their respective apps:
- Provider models: gpubrokerpod.gpubrokerapp.apps.providers.models
- Auth models: gpubrokerpod.gpubrokerapp.apps.auth_app.models
- etc.

This file can be used in the future if core needs to define abstract base models
or model mixins that other apps can inherit from.
"""
from django.db import models


class BaseModel(models.Model):
    """
    Abstract base model for all GPUBROKER models.
    
    Provides common fields and methods that all models should inherit.
    """
    created_at = models.DateTimeField(auto_now_add=True, editable=False)
    updated_at = models.DateTimeField(auto_now=True, editable=False)

    class Meta:
        abstract = True
        # Ensure this model is not migrated
        managed = False

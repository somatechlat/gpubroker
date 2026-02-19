#!/usr/bin/env python
"""
Script to create migrations for test database.

This script patches all models to managed=True before running makemigrations,
which is necessary because production models use managed=False.

The key insight is that we need to patch the model classes BEFORE Django
inspects them for migration generation.
"""

import os

# Set Django settings
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gpubroker.settings.test")

# We need to patch the model Meta classes BEFORE Django setup
# This requires importing the models directly and modifying them

# First, let's patch the model files by modifying the Meta.managed attribute
# at the class level before Django's app registry processes them

# Import Django's app loading mechanism
import django
from django.conf import settings

# Configure Django settings first
if not settings.configured:
    settings.configure()

# Now we need to patch the models before they're loaded
# The trick is to use a custom AppConfig or modify the models module

# Actually, the cleanest approach is to temporarily modify the model files
# or use a migration that explicitly sets managed=True

# Let's use a different approach: create migrations manually with managed=True
print("Creating migrations with managed=True...")

# Setup Django
django.setup()

# Patch all models to be managed
from django.apps import apps

for model in apps.get_models():
    model._meta.managed = True
    # Also need to update the original_attrs which makemigrations uses
    if hasattr(model._meta, "original_attrs"):
        model._meta.original_attrs["managed"] = True
    print(f"Patched {model._meta.app_label}.{model.__name__} to managed=True")

# Clear the migration writer cache to pick up the changes
from django.db.migrations import writer

if hasattr(writer, "_migration_template"):
    delattr(writer, "_migration_template")

# Now run makemigrations
from django.core.management import call_command

print("\n--- Creating migrations ---")
call_command(
    "makemigrations",
    "auth_app",
    "providers",
    "math_core",
    "kpi",
    "ai_assistant",
    "websocket_gateway",
    verbosity=2,
)

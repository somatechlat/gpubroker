#!/usr/bin/env python
"""
Health check script for GPUBROKER Django application.
Returns 0 if healthy, 1 if unhealthy.
"""

import os
import sys

# Set Django settings module
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "gpubroker.settings.database_backed")


def check_health():
    """Check application health."""
    try:
        import django

        django.setup()

        from django.core.cache import cache
        from django.db import connection

        # Check database connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        # Check cache connection
        cache.set("health_check", "ok", 10)
        if cache.get("health_check") != "ok":
            print("Cache check failed", file=sys.stderr)
            return 1

        print("OK")
        return 0

    except Exception as e:
        print(f"Health check failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(check_health())

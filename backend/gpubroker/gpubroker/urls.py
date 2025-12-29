"""
URL configuration for GPUBROKER project.

Routes:
- /admin/ - Django Admin interface
- /api/v2/ - Django Ninja API v2 endpoints
- /health - Health check endpoint
- /metrics - Prometheus metrics (via django-prometheus)
"""
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.db import connection
from django.core.cache import cache
from datetime import datetime, timezone

from gpubroker.api.v2 import api


def health_check(request):
    """
    Health check endpoint.
    
    Returns JSON with status of database and cache connections.
    Response time target: ≤100ms
    """
    status = {
        'status': 'healthy',
        'database': 'unknown',
        'cache': 'unknown',
        'timestamp': datetime.now(timezone.utc).isoformat(),
    }
    
    # Check database
    try:
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        status['database'] = 'connected'
    except Exception as e:
        status['database'] = f'error: {str(e)}'
        status['status'] = 'unhealthy'
    
    # Check cache (Redis)
    try:
        cache.set('health_check', 'ok', timeout=10)
        if cache.get('health_check') == 'ok':
            status['cache'] = 'connected'
        else:
            status['cache'] = 'error: cache read failed'
            status['status'] = 'unhealthy'
    except Exception as e:
        status['cache'] = f'error: {str(e)}'
        status['status'] = 'unhealthy'
    
    http_status = 200 if status['status'] == 'healthy' else 503
    return JsonResponse(status, status=http_status)


urlpatterns = [
    # Admin interface
    path('admin/', admin.site.urls),
    
    # Health check
    path('health', health_check, name='health_check'),
    
    # Prometheus metrics
    path('', include('django_prometheus.urls')),
    
    # API v2 (Django Ninja)
    path('api/v2/', api.urls),
]

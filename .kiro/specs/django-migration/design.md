# Design Document: Django 5 Migration

## Overview

This document specifies the technical design for GPUBROKER's Django 5 + Django Ninja architecture. The migration from the previous microservices architecture has been **completed with full feature parity**.

## Architecture

### Target Project Structure

```
backend/
├── gpubroker/                    # Django project root
│   ├── __init__.py
│   ├── asgi.py                   # ASGI config for Channels + Uvicorn
│   ├── wsgi.py                   # WSGI fallback
│   ├── settings/
│   │   ├── __init__.py
│   │   ├── base.py               # Common settings
│   │   ├── development.py        # Dev overrides
│   │   └── production.py         # Prod overrides
│   ├── urls.py                   # Root URL config
│   └── api/
│       └── v2/
│           ├── __init__.py       # NinjaAPI instance
│           └── router.py         # Aggregated routers
├── apps/
│   ├── auth_app/                 # Auth Service migration
│   │   ├── __init__.py
│   │   ├── models.py             # User, Tenant, AuditLog
│   │   ├── api.py                # Django Ninja endpoints
│   │   ├── schemas.py            # Pydantic schemas
│   │   ├── services.py           # Business logic
│   │   ├── auth.py               # JWT authentication
│   │   └── admin.py              # Django Admin config
│   ├── providers/                # Provider Service migration
│   │   ├── __init__.py
│   │   ├── models.py             # Provider, GPUOffer, PriceHistory
│   │   ├── api.py                # Django Ninja endpoints
│   │   ├── schemas.py            # Pydantic schemas
│   │   ├── services.py           # Business logic
│   │   ├── adapters/             # Provider adapters (preserved)
│   │   │   ├── __init__.py
│   │   │   ├── base.py           # BaseProviderAdapter
│   │   │   ├── runpod.py
│   │   │   ├── vastai.py
│   │   │   └── registry.py       # ProviderRegistry
│   │   └── admin.py
│   ├── kpi/                      # KPI Service migration
│   │   ├── __init__.py
│   │   ├── models.py             # KPI-related models if any
│   │   ├── api.py                # Django Ninja endpoints
│   │   ├── schemas.py
│   │   ├── services.py           # KPIEngine
│   │   └── admin.py
│   ├── math_core/                # Math Core migration
│   │   ├── __init__.py
│   │   ├── models.py             # GPUBenchmark
│   │   ├── api.py                # Django Ninja endpoints
│   │   ├── schemas.py
│   │   ├── algorithms/           # Preserved algorithm modules
│   │   │   ├── topsis.py
│   │   │   ├── collaborative.py
│   │   │   ├── content_based.py
│   │   │   ├── ensemble.py
│   │   │   └── workload_mapper.py
│   │   └── admin.py
│   ├── ai_assistant/             # AI Assistant migration
│   │   ├── __init__.py
│   │   ├── api.py                # Django Ninja endpoints
│   │   ├── schemas.py
│   │   ├── services.py           # SomaAgent client
│   │   └── admin.py
│   └── websocket_gateway/        # WebSocket Gateway migration
│       ├── __init__.py
│       ├── consumers.py          # Django Channels consumers
│       ├── routing.py            # WebSocket URL routing
│       └── services.py           # Connection manager
├── shared/                       # Shared utilities (preserved)
│   ├── vault_client.py
│   └── ...
├── manage.py
├── requirements.txt
└── Dockerfile
```


## Design Decisions

### D1: Unified Django Project (Req 1)

**Decision**: Single Django project with multiple apps instead of separate microservices.

**Rationale**:
- Reduces operational complexity (one deployment unit)
- Shared ORM models eliminate data duplication
- Django's app system provides logical separation
- Easier transaction management across domains

**Trade-offs**:
- Larger deployment artifact
- All services scale together (mitigated by async views)

**Implementation**:
- Each service domain is a Django app
- Apps communicate via direct Python imports, not HTTP
- External services (SomaAgent, Vault) still use HTTP clients

---

### D2: Django Ninja for REST APIs (Req 10)

**Decision**: Use Django Ninja instead of Django REST Framework.

**Rationale**:
- Syntax similar to FastAPI (familiar patterns)
- Native Pydantic support (reuse existing schemas)
- Async view support out of the box
- Auto-generated OpenAPI docs
- Better performance than DRF

**Implementation**:
```python
# gpubroker/api/v2/__init__.py
from ninja import NinjaAPI
from ninja.security import HttpBearer

class JWTAuth(HttpBearer):
    async def authenticate(self, request, token):
        # Validate JWT, return user or None
        ...

api = NinjaAPI(
    title="GPUBROKER API v2",
    version="2.0.0",
    urls_namespace="api-v2",
    auth=JWTAuth(),
)

# Register app routers
from apps.auth_app.api import router as auth_router
from apps.providers.api import router as providers_router
# ...

api.add_router("/auth/", auth_router, tags=["auth"])
api.add_router("/providers/", providers_router, tags=["providers"])
# ...
```

---

### D3: Django ORM with Existing Tables (Req 2, 11)

**Decision**: Map Django models to existing PostgreSQL tables using `Meta.db_table`.

**Rationale**:
- Zero data migration required
- Existing data preserved
- Gradual schema evolution via Django migrations

**Implementation**:
```python
# apps/auth_app/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    full_name = models.CharField(max_length=255)
    organization = models.CharField(max_length=255, blank=True, null=True)
    tenant = models.ForeignKey('Tenant', on_delete=models.CASCADE, null=True)
    role = models.CharField(max_length=50, default='user')
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=255, blank=True, null=True)
    
    # Override username to use email
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    class Meta:
        db_table = 'users'  # Match existing table
        managed = False     # Initially, don't alter schema
```

**Migration Strategy**:
1. Create models with `managed = False`
2. Run `makemigrations --fake-initial`
3. Verify Django can read existing data
4. Gradually set `managed = True` for new fields

---

### D4: JWT Authentication with RS256 (Req 3)

**Decision**: Custom JWT authentication using `python-jose` (same as current).

**Rationale**:
- Maintains token compatibility during dual-stack operation
- Existing tokens continue to work
- RS256 with key pair from environment

**Implementation**:
```python
# apps/auth_app/auth.py
from jose import jwt, JWTError
from ninja.security import HttpBearer
from django.conf import settings
from datetime import datetime, timezone

class JWTAuth(HttpBearer):
    async def authenticate(self, request, token):
        try:
            payload = jwt.decode(
                token,
                settings.JWT_PUBLIC_KEY,
                algorithms=["RS256"]
            )
            email = payload.get("sub")
            if not email:
                return None
            
            # Async ORM lookup
            from apps.auth_app.models import User
            user = await User.objects.filter(email=email).afirst()
            return user
        except JWTError:
            return None
```

---

### D5: Django Channels for WebSocket (Req 9)

**Decision**: Use Django Channels for WebSocket support.

**Rationale**:
- Native Django integration
- Redis channel layer for pub/sub
- Scales horizontally with multiple workers

**Implementation**:
```python
# apps/websocket_gateway/consumers.py
import json
from channels.generic.websocket import AsyncWebsocketConsumer

class PriceUpdateConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("price_updates", self.channel_name)
        await self.accept()
    
    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("price_updates", self.channel_name)
    
    async def price_update(self, event):
        await self.send(text_data=json.dumps(event["data"]))
    
    async def heartbeat(self, event):
        await self.send(text_data=json.dumps({"type": "heartbeat"}))
```

```python
# apps/websocket_gateway/routing.py
from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/$', consumers.PriceUpdateConsumer.as_asgi()),
]
```

---

### D6: Caching with Django Cache Framework (Req 12)

**Decision**: Use Django's cache framework with Redis backend.

**Rationale**:
- Consistent API across cache backends
- Built-in cache decorators
- Same Redis instance as current implementation

**Implementation**:
```python
# settings/base.py
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("REDIS_URL"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}

# apps/providers/services.py
from django.core.cache import cache
import hashlib

def get_cache_key(params: dict) -> str:
    base = "&".join(f"{k}={v}" for k, v in sorted(params.items()))
    return f"providers:list:{hashlib.sha256(base.encode()).hexdigest()}"

async def list_providers(filters: dict):
    key = get_cache_key(filters)
    cached = cache.get(key)
    if cached:
        return cached
    
    # Query database
    result = await _query_providers(filters)
    cache.set(key, result, timeout=60)
    return result
```


---

### D7: Provider Adapter Pattern Preservation (Req 5)

**Decision**: Move existing adapter code to Django app with minimal changes.

**Rationale**:
- Adapters are provider-agnostic Python classes
- No framework dependencies in adapter code
- Registry pattern works identically

**Implementation**:
```python
# apps/providers/adapters/base.py
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from dataclasses import dataclass

@dataclass
class ProviderOffer:
    provider: str
    region: str
    gpu_type: str
    price_per_hour: float
    availability: str
    compliance_tags: List[str]
    gpu_memory_gb: int
    external_id: str

class BaseProviderAdapter(ABC):
    PROVIDER_NAME: str = ""
    BASE_URL: str = ""
    
    @abstractmethod
    async def get_offers(self, auth_token: str) -> List[ProviderOffer]:
        """Fetch offers from provider API."""
        pass
    
    @abstractmethod
    async def validate_credentials(self, credentials: Dict[str, str]) -> bool:
        """Validate API credentials."""
        pass
    
    @abstractmethod
    async def book_instance(self, offer_id: str, duration: int) -> Dict[str, Any]:
        """Book a GPU instance."""
        pass
```

```python
# apps/providers/adapters/registry.py
from typing import Dict, Type
from .base import BaseProviderAdapter

class ProviderRegistry:
    _adapters: Dict[str, Type[BaseProviderAdapter]] = {}
    
    @classmethod
    def register(cls, name: str, adapter_class: Type[BaseProviderAdapter]):
        cls._adapters[name] = adapter_class
    
    @classmethod
    def get_adapter(cls, name: str) -> BaseProviderAdapter:
        if name not in cls._adapters:
            raise ValueError(f"Unknown provider: {name}")
        return cls._adapters[name]()
    
    @classmethod
    def list_adapters(cls) -> List[str]:
        return list(cls._adapters.keys())
```

---

### D8: Async Database Operations (Req 18)

**Decision**: Use Django 5's native async ORM methods.

**Rationale**:
- Django 5 has full async ORM support
- No need for `sync_to_async` wrappers
- Compatible with async views and Channels

**Implementation**:
```python
# apps/providers/services.py
from apps.providers.models import GPUOffer, Provider

async def get_offers_by_filter(
    gpu_type: str = None,
    region: str = None,
    provider_name: str = None,
    price_max: float = None,
    page: int = 1,
    per_page: int = 20,
):
    queryset = GPUOffer.objects.select_related('provider')
    
    if gpu_type:
        queryset = queryset.filter(gpu_type__icontains=gpu_type)
    if region:
        queryset = queryset.filter(region=region)
    if provider_name:
        queryset = queryset.filter(provider__name=provider_name)
    if price_max:
        queryset = queryset.filter(price_per_hour__lte=price_max)
    
    total = await queryset.acount()
    offset = (page - 1) * per_page
    items = [item async for item in queryset[offset:offset + per_page]]
    
    return {"total": total, "items": items}
```

---

### D9: Error Handling and Response Format (Req 10)

**Decision**: Consistent JSON error format matching existing API.

**Rationale**:
- Frontend expects specific error structure
- Trace ID for debugging
- HTTP status codes unchanged

**Implementation**:
```python
# gpubroker/api/v2/__init__.py
from ninja import NinjaAPI
from ninja.errors import ValidationError
from django.http import JsonResponse
import uuid

api = NinjaAPI(...)

@api.exception_handler(ValidationError)
def validation_error_handler(request, exc):
    return JsonResponse({
        "error": {
            "code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors,
            "trace_id": str(uuid.uuid4())
        }
    }, status=422)

@api.exception_handler(Exception)
def generic_error_handler(request, exc):
    return JsonResponse({
        "error": {
            "code": "INTERNAL_ERROR",
            "message": str(exc),
            "details": None,
            "trace_id": str(uuid.uuid4())
        }
    }, status=500)
```

---

### D10: Nginx Routing (Req 15)

**Decision**: Nginx routes all traffic to Django.

**Rationale**:
- Migration complete - all endpoints served by Django
- Single backend simplifies routing

**Implementation**:
```nginx
# nginx.conf
upstream django {
    server django:8000;
}

server {
    listen 80;
    
    location /api/v2/ {
        proxy_pass http://django;
    }
    
    location /ws/ {
        proxy_pass http://django;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
    
    location /admin/ {
        proxy_pass http://django;
    }
    
    location /health {
        proxy_pass http://django;
    }
}
```

---

### D11: Observability Integration (Req 13)

**Decision**: Use `django-prometheus` and `opentelemetry-instrumentation-django`.

**Rationale**:
- Standard metrics format
- W3C Trace Context propagation
- Structured JSON logging

**Implementation**:
```python
# settings/base.py
INSTALLED_APPS = [
    ...
    'django_prometheus',
]

MIDDLEWARE = [
    'django_prometheus.middleware.PrometheusBeforeMiddleware',
    ...
    'django_prometheus.middleware.PrometheusAfterMiddleware',
]

# Structured logging
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'json',
        },
    },
    'formatters': {
        'json': {
            'format': '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "service": "gpubroker-django", "message": "%(message)s"}',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}
```

---

### D12: Security Configuration (Req 19)

**Decision**: Django security middleware with production hardening.

**Rationale**:
- Django has battle-tested security middleware
- CSRF protection for form submissions
- XSS, clickjacking protection built-in

**Implementation**:
```python
# settings/production.py
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# Rate limiting
RATELIMIT_ENABLE = True
RATELIMIT_USE_CACHE = 'default'
RATELIMIT_KEY_PREFIX = 'rl:'
```


## Data Models

### Auth App Models

```python
# apps/auth_app/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid

class Tenant(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    plan = models.CharField(max_length=20, choices=[
        ('free', 'Free'),
        ('pro', 'Pro'),
        ('enterprise', 'Enterprise'),
    ], default='free')
    rate_limit_rps = models.IntegerField(default=10)
    ws_limit = models.IntegerField(default=5)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'tenants'

class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255, db_column='password_hash')
    full_name = models.CharField(max_length=255)
    organization = models.CharField(max_length=255, blank=True, null=True)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, null=True, blank=True)
    role = models.CharField(max_length=50, default='user')
    mfa_enabled = models.BooleanField(default=False)
    mfa_secret = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    username = None  # Remove username field
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['full_name']
    
    class Meta:
        db_table = 'users'

class AuditLog(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=100)
    resource_type = models.CharField(max_length=100)
    resource_id = models.CharField(max_length=255, blank=True, null=True)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField(null=True)
    previous_hash = models.CharField(max_length=64, blank=True, null=True)
    current_hash = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'audit_logs'
        indexes = [
            models.Index(fields=['tenant', 'created_at']),
            models.Index(fields=['user', 'created_at']),
        ]
```

### Provider App Models

```python
# apps/providers/models.py
from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid

class Provider(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True)
    display_name = models.CharField(max_length=255)
    api_base_url = models.URLField()
    status = models.CharField(max_length=20, choices=[
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('maintenance', 'Maintenance'),
    ], default='active')
    reliability_score = models.FloatField(default=1.0)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    error_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'providers'

class GPUOffer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, related_name='offers')
    external_id = models.CharField(max_length=255)
    gpu_type = models.CharField(max_length=100)
    gpu_memory_gb = models.IntegerField()
    cpu_cores = models.IntegerField(default=0)
    ram_gb = models.IntegerField(default=0)
    storage_gb = models.IntegerField(default=0)
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=4)
    currency = models.CharField(max_length=3, default='USD')
    region = models.CharField(max_length=100)
    availability_status = models.CharField(max_length=20, choices=[
        ('available', 'Available'),
        ('limited', 'Limited'),
        ('unavailable', 'Unavailable'),
    ], default='available')
    compliance_tags = ArrayField(models.CharField(max_length=50), default=list)
    last_seen_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'gpu_offers'
        unique_together = [['provider', 'external_id']]
        indexes = [
            models.Index(fields=['gpu_type']),
            models.Index(fields=['region']),
            models.Index(fields=['price_per_hour']),
            models.Index(fields=['availability_status']),
        ]

class PriceHistory(models.Model):
    id = models.BigAutoField(primary_key=True)
    offer = models.ForeignKey(GPUOffer, on_delete=models.CASCADE, related_name='price_history')
    price_per_hour = models.DecimalField(max_digits=10, decimal_places=4)
    availability_status = models.CharField(max_length=20)
    recorded_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'price_history'
        indexes = [
            models.Index(fields=['offer', 'recorded_at']),
        ]
```

### Math Core Models

```python
# apps/math_core/models.py
from django.db import models
import uuid

class GPUBenchmark(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    gpu_model = models.CharField(max_length=100, unique=True)
    tflops_fp32 = models.FloatField()
    tflops_fp16 = models.FloatField()
    tflops_int8 = models.FloatField(null=True, blank=True)
    memory_bandwidth_gbps = models.FloatField()
    vram_gb = models.IntegerField()
    tokens_per_second_7b = models.IntegerField()
    tokens_per_second_13b = models.IntegerField(null=True, blank=True)
    tokens_per_second_70b = models.IntegerField(null=True, blank=True)
    image_gen_per_minute = models.IntegerField(null=True, blank=True)
    source = models.CharField(max_length=255)
    verified_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'gpu_benchmarks'
```

## API Endpoint Mapping

| Endpoint | Django Ninja v2 | Notes |
|----------|-----------------|-------|
| `POST /auth/register` | `POST /api/v2/auth/register` | User registration |
| `POST /auth/login` | `POST /api/v2/auth/login` | JWT authentication |
| `POST /auth/refresh` | `POST /api/v2/auth/refresh` | Token refresh |
| `GET /auth/me` | `GET /api/v2/auth/me` | Current user profile |
| `GET /providers` | `GET /api/v2/providers` | GPU offer listing |
| `POST /config/integrations` | `POST /api/v2/config/integrations` | Provider config |
| `GET /config/integrations` | `GET /api/v2/config/integrations` | Integration status |
| `GET /kpi/overview` | `GET /api/v2/kpi/overview` | KPI overview |
| `GET /kpi/gpu/{gpu_type}` | `GET /api/v2/kpi/gpu/{gpu_type}` | GPU metrics |
| `GET /kpi/provider/{name}` | `GET /api/v2/kpi/provider/{name}` | Provider KPIs |
| `GET /kpi/insights/market` | `GET /api/v2/kpi/insights/market` | Market insights |
| `POST /math/cost-per-token` | `POST /api/v2/math/cost-per-token` | Token cost calc |
| `POST /math/cost-per-gflop` | `POST /api/v2/math/cost-per-gflop` | GFLOP cost calc |
| `POST /math/topsis` | `POST /api/v2/math/topsis` | TOPSIS ranking |
| `POST /math/ensemble-recommend` | `POST /api/v2/math/ensemble-recommend` | Recommendations |
| `POST /math/estimate-workload` | `POST /api/v2/math/estimate-workload` | Workload estimation |
| `GET /math/benchmarks` | `GET /api/v2/math/benchmarks` | GPU benchmarks |
| `GET /math/benchmarks/{gpu}` | `GET /api/v2/math/benchmarks/{gpu}` | Single benchmark |
| `POST /ai/chat` | `POST /api/v2/ai/chat` | AI chat |
| `POST /ai/parse-workload` | `POST /api/v2/ai/parse-workload` | Workload parsing |
| `GET /ai/sessions/{id}/history` | `GET /api/v2/ai/sessions/{id}/history` | Chat history |
| `GET /ai/tools` | `GET /api/v2/ai/tools` | AI tools |
| `GET /ai/health` | `GET /api/v2/ai/health` | AI health |
| `WS /ws/` | `WS /ws/` | Django Channels |

## Dependencies

### Python Requirements

```
# Django core
Django>=5.0,<6.0
django-ninja>=1.0,<2.0
channels>=4.0,<5.0
channels-redis>=4.0,<5.0
daphne>=4.0,<5.0

# Database
psycopg[binary]>=3.0,<4.0
dj-database-url>=2.0,<3.0

# Authentication
python-jose[cryptography]>=3.3,<4.0
passlib[argon2]>=1.7,<2.0

# Caching
django-redis>=5.0,<6.0

# Observability
django-prometheus>=2.0,<3.0
opentelemetry-instrumentation-django>=0.40b0
python-json-logger>=2.0,<3.0

# Security
django-cors-headers>=4.0,<5.0
django-ratelimit>=4.0,<5.0

# Utilities
django-environ>=0.11,<1.0
whitenoise>=6.0,<7.0
httpx>=0.25,<1.0
numpy>=1.24,<2.0
pandas>=2.0,<3.0

# Testing
pytest>=7.0,<8.0
pytest-django>=4.5,<5.0
pytest-asyncio>=0.21,<1.0
```

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Token incompatibility | Users logged out | Use same JWT library and keys |
| Schema mismatch | Data corruption | Use `managed=False` initially |
| Performance regression | Slower API | Benchmark before/after, async views |
| WebSocket disconnects | Lost updates | Graceful reconnection in frontend |
| Cache key collision | Stale data | Prefix keys with `v2:` |

## Testing Strategy

1. **Unit Tests**: pytest-django for models and services
2. **Integration Tests**: Django test client for API endpoints
3. **Load Tests**: Locust to verify p95 latency ≤200ms
4. **WebSocket Tests**: pytest-asyncio for Channels consumers

# Requirements Document: Django 5 Migration

## Introduction

This document specifies the complete migration of GPUBROKER from the previous microservices architecture to Django 5 with Django Ninja API framework. The migration has been **completed with full feature parity**.

### Migration Status: ✅ COMPLETE

**Current State (Django 5 Stack):**
- Django 5.x with Django Ninja for REST APIs
- Django ORM for all database operations (replacing asyncpg raw queries)
- Django Channels for WebSocket/SSE realtime
- Django's authentication system with JWT extension
- Unified Django project with apps per service domain

### Core Principles (Applied During Migration)

1. **Feature Parity**: Every existing endpoint works identically after migration ✅
2. **In-Place Migration**: Migrated service by service ✅
3. **API Versioning**: All endpoints now at `/api/v2/` ✅
4. **Zero Downtime**: Migration completed without service interruption ✅
5. **Real Data Only**: No mocks, no fake implementations, no placeholders ✅

### Technology Stack (Current - Django 5)

| Component | Implementation |
|-----------|----------------|
| API Framework | Django 5 + Django Ninja |
| ORM | Django ORM |
| WebSocket | Django Channels |
| Authentication | Django + python-jose JWT (RS256) |
| Async Support | Django async views + Channels |
| Migrations | Django migrations |
| Admin | Django Admin |
| Testing | pytest-django + Django test client |

## Glossary

- **Django Ninja**: High-performance API framework for Django
- **Django Channels**: Async support for Django including WebSocket, SSE
- **Django ORM**: Object-Relational Mapper built into Django
- **ASGI**: Asynchronous Server Gateway Interface (required for Channels)
- **Feature Parity**: New implementation behaves identically to old
- **API v2**: Django Ninja endpoints versioned as v2

## Requirements

### Requirement 1: Django Project Structure Setup

**User Story:** As a developer, I want a properly structured Django 5 project that can host all migrated services, so that we have a unified codebase with clear separation of concerns.

#### Acceptance Criteria

1. WHEN the Django project is created THEN THE Project SHALL use Django 5.x with Python 3.12 compatibility
2. WHEN structuring the project THEN THE Project SHALL have separate Django apps for: `auth_app`, `providers`, `kpi`, `math_core`, `ai_assistant`, `websocket_gateway`
3. WHEN configuring settings THEN THE Project SHALL use environment variables for all secrets via `django-environ` or `python-decouple`
4. WHEN configuring the database THEN THE Project SHALL connect to the existing PostgreSQL database without schema conflicts
5. WHEN configuring async support THEN THE Project SHALL use ASGI with Daphne or Uvicorn for async views and Channels
6. WHEN the project starts THEN THE Health endpoint `/health` SHALL return status within 100ms
7. WHEN running in development THEN THE Project SHALL support hot-reload via `runserver` or `uvicorn --reload`

---

### Requirement 2: Django ORM Model Migration

**User Story:** As a developer, I want all database models defined in Django ORM, so that we can use Django's migration system and querysets instead of raw SQL.

#### Acceptance Criteria

1. WHEN defining User model THEN THE `auth_app` SHALL create a custom User model extending `AbstractUser` with fields: id (UUID), email, password_hash, full_name, organization, tenant_id, role, mfa_enabled, mfa_secret, is_active, created_at, updated_at
2. WHEN defining Tenant model THEN THE `auth_app` SHALL create Tenant with fields: id (UUID), name, plan (enum: free/pro/enterprise), rate_limit_rps, ws_limit, created_at
3. WHEN defining Provider model THEN THE `providers` app SHALL create Provider with fields: id (UUID), name, display_name, api_base_url, status, reliability_score, last_sync_at, error_count, created_at
4. WHEN defining GPUOffer model THEN THE `providers` app SHALL create GPUOffer with fields: id (UUID), provider (FK), external_id, gpu_type, gpu_memory_gb, cpu_cores, ram_gb, storage_gb, price_per_hour (Decimal), currency, region, availability_status, compliance_tags (ArrayField), last_seen_at, created_at, updated_at with unique constraint on (provider, external_id)
5. WHEN defining PriceHistory model THEN THE `providers` app SHALL create PriceHistory with fields: id, offer (FK), price_per_hour, availability_status, recorded_at
6. WHEN defining GPUBenchmark model THEN THE `math_core` app SHALL create GPUBenchmark with fields: id (UUID), gpu_model (unique), tflops_fp32, tflops_fp16, tflops_int8, memory_bandwidth_gbps, vram_gb, tokens_per_second_7b, tokens_per_second_13b, tokens_per_second_70b, image_gen_per_minute, source, verified_at, created_at
7. WHEN defining AuditLog model THEN THE `auth_app` SHALL create AuditLog with fields: id (UUID), tenant (FK), user (FK), action, resource_type, resource_id, details (JSONField), ip_address, previous_hash, current_hash, created_at
8. WHEN running migrations THEN Django SHALL detect existing tables and create migrations that are compatible with current schema
9. WHEN models reference existing tables THEN THE `Meta.db_table` SHALL match existing table names to avoid data loss

---

### Requirement 3: Auth Service Migration to Django

**User Story:** As a user, I want authentication to work identically after migration, so that my login, registration, and JWT tokens continue to function.

#### Acceptance Criteria

1. WHEN migrating `/auth/register` THEN THE Django Ninja endpoint SHALL accept {email, password, full_name, organization} and return {id, email, full_name, organization, is_active, created_at}
2. WHEN migrating `/auth/login` THEN THE Django Ninja endpoint SHALL accept {email, password}, verify with Argon2, and return {access_token, refresh_token, token_type: "bearer"}
3. WHEN issuing JWT tokens THEN THE Auth Service SHALL use RS256 algorithm with JWT_PRIVATE_KEY and JWT_PUBLIC_KEY from environment
4. WHEN issuing access tokens THEN THE Token SHALL have 15-minute expiry with claims: sub (email), exp, iat, roles, tenant_id
5. WHEN issuing refresh tokens THEN THE Token SHALL have 7-day expiry with claim type: "refresh"
6. WHEN migrating `/auth/refresh` THEN THE Django Ninja endpoint SHALL accept {refresh_token} and return new {access_token, refresh_token, expires_in}
7. WHEN migrating `/auth/me` THEN THE Django Ninja endpoint SHALL require Bearer token and return current user profile
8. WHEN validating tokens THEN THE Auth middleware SHALL decode JWT, verify signature, check expiry, and attach user to request
9. WHEN password hashing THEN THE Service SHALL use Argon2id via `django-argon2` or `passlib[argon2]`
10. WHEN a user attempts unauthorized action THEN THE Service SHALL return HTTP 403 with error JSON matching existing format

---

### Requirement 4: Provider Service Migration to Django

**User Story:** As a user, I want the provider marketplace API to work identically after migration, so that I can continue browsing and filtering GPU offers.

#### Acceptance Criteria

1. WHEN migrating `/providers` GET THEN THE Django Ninja endpoint SHALL accept query params: gpu, gpu_type, region, provider, availability, compliance_tag, gpu_memory_min, gpu_memory_max, price_min, max_price, page, per_page
2. WHEN returning provider list THEN THE Response SHALL match schema: {total: int, items: ProviderItem[], warnings?: string[]}
3. WHEN filtering by gpu_type THEN THE QuerySet SHALL use `__icontains` for partial matching
4. WHEN filtering by price range THEN THE QuerySet SHALL use `price_per_hour__gte` and `price_per_hour__lte`
5. WHEN filtering by compliance_tag THEN THE QuerySet SHALL use `compliance_tags__contains` for ArrayField
6. WHEN paginating results THEN THE Service SHALL use Django Paginator with page sizes 10, 20, 50, 100
7. WHEN caching responses THEN THE Service SHALL use Django cache framework with Redis backend, TTL 60 seconds
8. WHEN migrating `/config/integrations` POST THEN THE Django Ninja endpoint SHALL save provider API keys encrypted via Vault
9. WHEN migrating `/config/integrations` GET THEN THE Django Ninja endpoint SHALL return list of IntegrationStatus with provider, status, message, last_checked
10. WHEN rate limiting THEN THE Service SHALL enforce per-plan limits (free: 10/s, pro: 100/s, enterprise: 1000/s) using `django-ratelimit` or custom middleware
11. WHEN Math Core enrichment is enabled THEN THE Service SHALL call Math Core client and append cost_per_token, cost_per_gflop to offers

---

### Requirement 5: Provider Adapter Pattern Migration

**User Story:** As a developer, I want the provider adapter pattern preserved in Django, so that adding new GPU providers remains straightforward.

#### Acceptance Criteria

1. WHEN defining adapters THEN THE `providers` app SHALL have `adapters/` directory with `base.py` containing abstract `BaseProviderAdapter` class
2. WHEN implementing BaseProviderAdapter THEN THE Class SHALL define abstract methods: `get_offers(auth_token) -> List[ProviderOffer]`, `validate_credentials(credentials) -> bool`, `book_instance(offer_id, duration) -> BookingResult`
3. WHEN registering adapters THEN THE `ProviderRegistry` class SHALL support `register(name, adapter_class)` and `get_adapter(name)` methods
4. WHEN fetching offers THEN THE Service SHALL iterate registered adapters, call `get_offers()`, and normalize responses
5. WHEN normalizing offers THEN THE Service SHALL validate via Pydantic or Django serializers with required fields: provider, region, gpu_type, price_per_hour, availability
6. WHEN an adapter fails THEN THE Service SHALL log error, increment error counter, and continue with other adapters
7. WHEN circuit breaker triggers THEN THE Service SHALL use `pybreaker` or custom implementation with: 5 failures in 30s → open, 60s recovery

---

### Requirement 6: KPI Service Migration to Django

**User Story:** As a user, I want KPI calculations to work identically after migration, so that I can continue viewing cost-per-token and market insights.

#### Acceptance Criteria

1. WHEN migrating `/kpi/overview` THEN THE Django Ninja endpoint SHALL return {cost_per_token, uptime_pct, avg_latency_ms, active_providers}
2. WHEN migrating `/kpi/kpis/gpu/{gpu_type}` THEN THE Django Ninja endpoint SHALL return GPUMetrics with avg_price_per_hour, cost_per_token, cost_per_gflop
3. WHEN migrating `/kpi/kpis/provider/{provider_name}` THEN THE Django Ninja endpoint SHALL return ProviderKPI with total_offers, avg_price_per_hour, price_volatility, uptime_percentage
4. WHEN migrating `/kpi/insights/market` THEN THE Django Ninja endpoint SHALL return MarketInsights with total_providers, total_offers, cheapest_gpu_offer, most_expensive_gpu_offer, avg_market_price
5. WHEN calculating KPIs THEN THE Service SHALL use Django ORM aggregations: `Avg`, `Count`, `StdDev` instead of raw SQL
6. WHEN calculating cost_per_token THEN THE Service SHALL call Math Core `/math/cost-per-token` or use local KPIEngine class
7. WHEN database is unavailable THEN THE Service SHALL return HTTP 503 with {detail: "Database not available"}

---

### Requirement 7: Math Core Service Migration to Django

**User Story:** As a platform architect, I want Math Core calculations preserved in Django, so that all mathematical operations remain consistent and auditable.

#### Acceptance Criteria

1. WHEN migrating `/math/cost-per-token` THEN THE Django Ninja endpoint SHALL accept {price_per_hour, gpu_type, model_size} and return {cost_per_token, cost_per_million_tokens, tokens_per_second, confidence, calculation_details}
2. WHEN migrating `/math/cost-per-gflop` THEN THE Django Ninja endpoint SHALL accept {price_per_hour, gpu_type} and return {cost_per_gflop, cost_per_tflop_hour, gpu_tflops, confidence}
3. WHEN migrating `/math/topsis` THEN THE Django Ninja endpoint SHALL accept {decision_matrix, weights, criteria_types} and return {rankings, scores, ideal_solution, anti_ideal_solution}
4. WHEN migrating `/math/ensemble-recommend` THEN THE Django Ninja endpoint SHALL accept {user_id, workload_profile, candidate_offers, top_k} and return {recommendations, algorithm_contributions, confidence}
5. WHEN migrating `/math/estimate-workload` THEN THE Django Ninja endpoint SHALL accept {workload_type, quantity, duration_hours, quality, model_name} and return {min_vram_gb, recommended_vram_gb, recommended_gpu_tiers, estimated_cost_range, confidence, reasoning}
6. WHEN migrating `/math/benchmarks` THEN THE Django Ninja endpoint SHALL return list of GPUBenchmark from Django ORM
7. WHEN migrating `/math/benchmarks/{gpu_type}` THEN THE Django Ninja endpoint SHALL return single GPUBenchmark or 404
8. WHEN performing calculations THEN THE Service SHALL use existing algorithm modules: `algorithms/topsis.py`, `algorithms/collaborative.py`, `algorithms/content_based.py`, `algorithms/ensemble.py`, `algorithms/workload_mapper.py`
9. WHEN weights do not sum to 1.0 THEN THE Service SHALL return HTTP 400 with validation error

---

### Requirement 8: AI Assistant Service Migration to Django

**User Story:** As a user, I want the AI chat assistant to work identically after migration, so that I can continue getting GPU recommendations via natural language.

#### Acceptance Criteria

1. WHEN migrating `/ai/chat` THEN THE Django Ninja endpoint SHALL accept {user_id, message, context, history} and return {reply, sources, elapsed_ms, recommendations, session_history}
2. WHEN forwarding to SomaAgent THEN THE Service SHALL use `httpx.AsyncClient` to call `SOMA_AGENT_BASE/v1/llm/invoke`
3. WHEN trimming history THEN THE Service SHALL include at most last 10 turns plus current message
4. WHEN enriching with recommendations THEN THE Service SHALL fetch candidate offers from Provider Service and call Math Core `/math/ensemble-recommend`
5. WHEN SomaAgent fails THEN THE Service SHALL return HTTP 502 with {detail: "AI agent call failed"}
6. WHEN migrating `/ai/parse-workload` THEN THE Django Ninja endpoint SHALL accept {text} and return {workload_type, quantity, duration, region, quality}
7. WHEN migrating `/ai/sessions/{session_id}/history` THEN THE Django Ninja endpoint SHALL proxy to SomaAgent `/v1/sessions/{session_id}/history`
8. WHEN migrating `/ai/tools` THEN THE Django Ninja endpoint SHALL proxy to SomaAgent `/v1/tools`
9. WHEN migrating `/ai/health` THEN THE Django Ninja endpoint SHALL proxy to SomaAgent `/v1/health`

---

### Requirement 9: WebSocket Gateway Migration to Django Channels

**User Story:** As a user, I want real-time price updates to work identically after migration, so that I see live price changes without page refresh.

#### Acceptance Criteria

1. WHEN migrating WebSocket endpoint THEN THE Django Channels consumer SHALL handle connections at `/ws/`
2. WHEN a client connects THEN THE Consumer SHALL accept connection and add to connection manager
3. WHEN subscribing to Redis THEN THE Consumer SHALL use `channels_redis` to subscribe to `price_updates` channel
4. WHEN a price update arrives THEN THE Consumer SHALL broadcast to all connected clients within 500ms
5. WHEN heartbeat interval elapses (30s) THEN THE Consumer SHALL send {type: "heartbeat"} to client
6. WHEN client disconnects THEN THE Consumer SHALL remove from connection manager and clean up
7. WHEN configuring Channels THEN THE Project SHALL use `channels_redis` as channel layer backend
8. WHEN running ASGI THEN THE Project SHALL use Daphne or Uvicorn with `--ws` support

---

### Requirement 10: Django Ninja API Configuration

**User Story:** As a developer, I want Django Ninja configured consistently across all apps, so that API behavior is uniform and documented.

#### Acceptance Criteria

1. WHEN configuring Django Ninja THEN THE Project SHALL create a single `NinjaAPI` instance in `api/v2/__init__.py`
2. WHEN versioning APIs THEN THE Django Ninja router SHALL mount at `/api/v2/` prefix
3. WHEN documenting APIs THEN THE Django Ninja SHALL auto-generate OpenAPI schema at `/api/v2/docs`
4. WHEN handling errors THEN THE Django Ninja SHALL return consistent JSON: {error: {code, message, details, trace_id}}
5. WHEN authenticating requests THEN THE Django Ninja SHALL use custom `JWTAuth` class that validates Bearer tokens
6. WHEN validating requests THEN THE Django Ninja SHALL use Pydantic schemas (Schema classes) for request/response
7. WHEN handling async views THEN THE Django Ninja SHALL support `async def` endpoint functions
8. WHEN rate limiting THEN THE Django Ninja SHALL integrate with rate limit middleware via decorators or global config

---

### Requirement 11: Database Connection and Migration Strategy

**User Story:** As a developer, I want database migrations to be safe and reversible, so that we don't lose data during the transition.

#### Acceptance Criteria

1. WHEN connecting to database THEN THE Django settings SHALL use `DATABASE_URL` environment variable parsed by `dj-database-url`
2. WHEN defining models for existing tables THEN THE Model Meta SHALL set `managed = False` initially to prevent Django from altering existing schema
3. WHEN creating initial migrations THEN THE Developer SHALL run `makemigrations` with `--fake-initial` to mark existing tables as migrated
4. WHEN adding new fields THEN THE Migration SHALL use `AddField` with `null=True` default to avoid breaking existing data
5. WHEN removing fields THEN THE Migration SHALL be reversible with `RemoveField` that can be rolled back
6. WHEN running migrations in production THEN THE Pipeline SHALL run `migrate --plan` first to preview changes
7. WHEN connection pooling is needed THEN THE Project SHALL use `django-db-connection-pool` or PgBouncer

---

### Requirement 12: Caching Strategy Migration

**User Story:** As a developer, I want caching to work identically after migration, so that API performance remains fast.

#### Acceptance Criteria

1. WHEN configuring cache THEN THE Django settings SHALL use `django-redis` with `REDIS_URL` from environment
2. WHEN caching provider lists THEN THE Service SHALL use `cache.get()` and `cache.set()` with key pattern `providers:list:{hash}`
3. WHEN cache TTL is set THEN THE Default SHALL be 60 seconds
4. WHEN invalidating cache THEN THE Service SHALL call `cache.delete()` on offer updates
5. WHEN cache is unavailable THEN THE Service SHALL log warning and continue without cache (graceful degradation)
6. WHEN using cache decorators THEN THE Service MAY use `@cache_page` for view-level caching where appropriate

---

### Requirement 13: Logging and Observability Migration

**User Story:** As an operator, I want logging and metrics to work identically after migration, so that I can monitor system health.

#### Acceptance Criteria

1. WHEN configuring logging THEN THE Django settings SHALL output structured JSON with: timestamp, level, service, trace_id, message
2. WHEN logging requests THEN THE Middleware SHALL log: method, path, status_code, duration_ms, user_id, trace_id
3. WHEN exposing metrics THEN THE Service SHALL use `django-prometheus` to expose `/metrics` endpoint
4. WHEN recording metrics THEN THE Service SHALL track: request_count, request_latency_seconds, error_count with labels
5. WHEN propagating traces THEN THE Service SHALL use `opentelemetry-instrumentation-django` for W3C Trace Context
6. WHEN health check is called THEN THE `/health` endpoint SHALL return {status, database, cache, timestamp}

---

### Requirement 14: Testing Strategy Migration

**User Story:** As a developer, I want tests to run against Django, so that we can verify migration correctness.

#### Acceptance Criteria

1. WHEN configuring tests THEN THE Project SHALL use `pytest-django` with `DJANGO_SETTINGS_MODULE` set
2. WHEN testing endpoints THEN THE Tests SHALL use Django test client or `httpx.AsyncClient` with `ASGITransport`
3. WHEN testing models THEN THE Tests SHALL use Django's `TestCase` with database transactions
4. WHEN testing async views THEN THE Tests SHALL use `pytest-asyncio` with `async_to_sync` where needed
5. WHEN running tests THEN THE Coverage SHALL be ≥80% for migrated code
6. WHEN testing auth THEN THE Tests SHALL verify JWT issuance, validation, and expiry
7. WHEN testing providers THEN THE Tests SHALL verify filtering, pagination, and caching

---

### Requirement 15: Migration Verification (COMPLETED)

**User Story:** As an operator, I verified that Django provides full feature parity with the previous implementation.

#### Acceptance Criteria (All Verified)

1. ✅ Docker Compose runs Django service only (legacy services removed)
2. ✅ All API routes served by Django at `/api/v2/`
3. ✅ Frontend uses v2 endpoints exclusively
4. ✅ All v2 endpoints verified with full feature parity
5. ✅ Legacy services removed from docker-compose and codebase

---

### Requirement 16: Environment and Configuration Migration

**User Story:** As a developer, I want environment configuration to be consistent, so that deployment remains straightforward.

#### Acceptance Criteria

1. WHEN configuring Django THEN THE Settings SHALL read from environment: DATABASE_URL, REDIS_URL, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY, VAULT_ADDR, SOMA_AGENT_BASE
2. WHEN secrets are needed THEN THE Service SHALL fetch from Vault using existing `shared.vault_client`
3. WHEN DEBUG mode is set THEN THE Django SHALL enable debug toolbar and detailed errors only in development
4. WHEN ALLOWED_HOSTS is set THEN THE Django SHALL read from `ALLOWED_HOSTS` environment variable (comma-separated)
5. WHEN CORS is configured THEN THE Django SHALL use `django-cors-headers` with origins from environment
6. WHEN static files are served THEN THE Django SHALL use `whitenoise` for production static file serving

---

### Requirement 17: Admin Interface Setup

**User Story:** As an admin, I want Django Admin configured for data management, so that I can manage users, providers, and offers without direct database access.

#### Acceptance Criteria

1. WHEN configuring admin THEN THE Django Admin SHALL be available at `/admin/`
2. WHEN registering User model THEN THE Admin SHALL show: email, full_name, role, tenant, is_active, created_at
3. WHEN registering Provider model THEN THE Admin SHALL show: name, display_name, status, reliability_score, last_sync_at, error_count
4. WHEN registering GPUOffer model THEN THE Admin SHALL show: provider, gpu_type, price_per_hour, region, availability_status with filters
5. WHEN registering GPUBenchmark model THEN THE Admin SHALL show: gpu_model, tflops_fp32, vram_gb, tokens_per_second_7b
6. WHEN admin user is created THEN THE Superuser SHALL be created via `createsuperuser` command or migration
7. WHEN admin is accessed THEN THE Admin SHALL require authentication and log access to audit_log

---

### Requirement 18: Async Support and Performance

**User Story:** As a developer, I want async support in Django, so that I/O-bound operations don't block the event loop.

#### Acceptance Criteria

1. WHEN defining async views THEN THE Django Ninja endpoint SHALL use `async def` for database and HTTP operations
2. WHEN querying database async THEN THE Service SHALL use Django's async ORM methods: `aget()`, `afilter()`, `acount()`
3. WHEN making HTTP calls THEN THE Service SHALL use `httpx.AsyncClient` with connection pooling
4. WHEN running ASGI THEN THE Server SHALL use Uvicorn with `--workers` for production
5. WHEN connection pooling is needed THEN THE Database SHALL use async-compatible pool (Django 5 native or `databases` package)
6. WHEN performance testing THEN THE API SHALL maintain ≤200ms p95 latency for cached requests

---

### Requirement 19: Security Configuration

**User Story:** As a security engineer, I want Django security settings configured properly, so that the application is protected against common attacks.

#### Acceptance Criteria

1. WHEN configuring security THEN THE Django SHALL set: SECURE_SSL_REDIRECT=True, SESSION_COOKIE_SECURE=True, CSRF_COOKIE_SECURE=True in production
2. WHEN configuring CSRF THEN THE Django SHALL use `django.middleware.csrf.CsrfViewMiddleware` for form submissions
3. WHEN configuring XSS protection THEN THE Django SHALL set SECURE_BROWSER_XSS_FILTER=True
4. WHEN configuring clickjacking THEN THE Django SHALL set X_FRAME_OPTIONS='DENY'
5. WHEN validating input THEN THE Django Ninja schemas SHALL validate and sanitize all user input
6. WHEN rate limiting THEN THE Service SHALL block IPs exceeding 1000 req/min with HTTP 429
7. WHEN secrets are logged THEN THE Logger SHALL redact JWT tokens, API keys, and passwords

---

### Requirement 20: Deployment Configuration

**User Story:** As a DevOps engineer, I want Django deployment configured for containers, so that it runs in our existing Kubernetes infrastructure.

#### Acceptance Criteria

1. WHEN building Docker image THEN THE Dockerfile SHALL use `python:3.12-slim` base with multi-stage build
2. WHEN installing dependencies THEN THE Dockerfile SHALL use `pip install --no-cache-dir -r requirements.txt`
3. WHEN running in container THEN THE Entrypoint SHALL run migrations then start Uvicorn/Daphne
4. WHEN health check is configured THEN THE Dockerfile SHALL include `HEALTHCHECK` calling `/health`
5. WHEN configuring Kubernetes THEN THE Deployment SHALL set readiness probe on `/health` and liveness probe on `/health`
6. WHEN scaling THEN THE HPA SHALL scale based on CPU (70%) and custom metrics (p95 latency)
7. WHEN deploying THEN The CI/CD SHALL run: lint → test → build → push → deploy with rollback on failure


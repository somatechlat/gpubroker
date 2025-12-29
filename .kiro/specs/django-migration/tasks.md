# Implementation Tasks: Django 5 Migration

## Overview

This document contains the implementation tasks for migrating GPUBROKER to Django 5 + Django Ninja. Tasks are ordered by dependency and grouped by phase. **All tasks have been completed.**

## Tasks

### Phase 1: Project Foundation

- [x] 1.1 Create Django Project Structure
  - Create `backend/gpubroker/` Django project with `django-admin startproject`
  - Create `backend/apps/` directory for Django apps
  - Configure `settings/base.py`, `settings/development.py`, `settings/production.py`
  - Set up `asgi.py` for Channels support
  - Configure environment variables via `django-environ`
  - Create `manage.py` entry point
  - _Requirements: 1.1, 1.2, 1.3, 1.5, 1.6, 1.7_

- [x] 1.2 Configure Django Settings
  - Configure `DATABASE_URL` parsing with `dj-database-url`
  - Configure `REDIS_URL` for cache and Channels
  - Configure `JWT_PRIVATE_KEY` and `JWT_PUBLIC_KEY` from environment
  - Configure `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`
  - Configure `INSTALLED_APPS` with all Django apps
  - Configure `MIDDLEWARE` stack including security middleware
  - _Requirements: 16.1, 16.3, 16.4, 16.5, 19.1, 19.2, 19.3, 19.4_

- [x] 1.3 Set Up Django Ninja API
  - Create `gpubroker/api/v2/__init__.py` with `NinjaAPI` instance
  - Configure OpenAPI documentation at `/api/v2/docs`
  - Implement global exception handlers for consistent error format
  - Configure API versioning with `/api/v2/` prefix
  - _Requirements: 10.1, 10.2, 10.3, 10.4_

- [x] 1.4 Checkpoint - Verify project starts
  - Ensure Django project starts without errors
  - Verify `/api/v2/docs` is accessible
  - Ask the user if questions arise

---

### Phase 2: Database Models

- [x] 2.1 Create Auth App Models
  - Create `apps/auth_app/` Django app
  - Define `Tenant` model with `db_table='tenants'`, `managed=False`
  - Define custom `User` model extending `AbstractUser` with `db_table='users'`, `managed=False`
  - Define `AuditLog` model with `db_table='audit_logs'`, `managed=False`
  - Configure `AUTH_USER_MODEL = 'auth_app.User'` in settings
  - Run `makemigrations --fake-initial` to create initial migration
  - _Requirements: 2.1, 2.2, 2.7, 2.8, 2.9_

- [x] 2.2 Create Provider App Models
  - Create `apps/providers/` Django app
  - Define `Provider` model with `db_table='providers'`, `managed=False`
  - Define `GPUOffer` model with `db_table='gpu_offers'`, `managed=False`
  - Define `PriceHistory` model with `db_table='price_history'`, `managed=False`
  - Add `ArrayField` for `compliance_tags`
  - Add indexes for common query patterns
  - Run `makemigrations --fake-initial`
  - _Requirements: 2.3, 2.4, 2.5, 2.8, 2.9_

- [x] 2.3 Create Math Core Models
  - Create `apps/math_core/` Django app
  - Define `GPUBenchmark` model with `db_table='gpu_benchmarks'`, `managed=False`
  - Run `makemigrations --fake-initial`
  - _Requirements: 2.6, 2.8, 2.9_

- [x] 2.4 Create KPI App
  - Create `apps/kpi/` Django app
  - No new models required (uses Provider and GPUOffer models)
  - Run `makemigrations`
  - _Requirements: 2.8_

- [x] 2.5 Create AI Assistant App
  - Create `apps/ai_assistant/` Django app
  - No new models required (stateless proxy to SomaAgent)
  - Run `makemigrations`
  - _Requirements: 2.8_

- [x] 2.6 Create WebSocket Gateway App
  - Create `apps/websocket_gateway/` Django app
  - No new models required (stateless WebSocket handler)
  - Run `makemigrations`
  - _Requirements: 2.8_

- [x] 2.7 Checkpoint - Verify models
  - Ensure all migrations run without errors
  - Verify Django can read existing data from tables
  - Ask the user if questions arise

---

### Phase 3: Authentication

- [x] 3.1 Implement JWT Authentication
  - Create `apps/auth_app/auth.py` with `JWTAuth` class extending `HttpBearer`
  - Implement `authenticate()` method to decode JWT with `python-jose`
  - Verify RS256 signature using `JWT_PUBLIC_KEY`
  - Return `User` instance or `None` on failure
  - Add `JWTAuth` as default auth to `NinjaAPI` instance
  - _Requirements: 3.3, 3.4, 3.8_

- [x] 3.2 Implement Auth Endpoints
  - Create `apps/auth_app/schemas.py` with Pydantic schemas: `UserCreate`, `UserLogin`, `Token`, `UserResponse`
  - Create `apps/auth_app/services.py` with business logic: `create_user()`, `authenticate_user()`, `create_tokens()`
  - Create `apps/auth_app/api.py` with Django Ninja router
  - Implement `POST /register` endpoint
  - Implement `POST /login` endpoint
  - Implement `POST /refresh` endpoint
  - Implement `GET /me` endpoint
  - Use Argon2 password hashing via `passlib`
  - _Requirements: 3.1, 3.2, 3.5, 3.6, 3.7, 3.9, 3.10_

- [x] 3.3 Implement Auth Middleware
  - Create middleware to attach `request.user` from JWT
  - Log authentication attempts to `AuditLog`
  - Handle token expiry gracefully
  - _Requirements: 3.8, 3.10_

- [x] 3.4 Checkpoint - Verify auth
  - Test user registration
  - Test user login and JWT issuance
  - Test protected endpoint access
  - Ask the user if questions arise

---

### Phase 4: Provider Service

- [x] 4.1 Migrate Provider Adapters
  - Create `apps/providers/adapters/` directory
  - Copy `base_adapter.py` to `apps/providers/adapters/base.py`
  - Copy existing adapter implementations (runpod, vastai, etc.)
  - Copy `registry.py` to `apps/providers/adapters/registry.py`
  - Update imports to use Django app paths
  - Verify adapters work with async/await
  - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 4.2 Implement Provider Endpoints
  - Create `apps/providers/schemas.py` with Pydantic schemas
  - Create `apps/providers/services.py` with business logic
  - Create `apps/providers/api.py` with Django Ninja router
  - Implement `GET /providers` with all query filters
  - Implement `POST /config/integrations`
  - Implement `GET /config/integrations`
  - Implement Redis caching with 60s TTL
  - Implement rate limiting per plan
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11_

- [x] 4.3 Implement Circuit Breaker
  - Copy `core/async_circuit_breaker.py` to `apps/providers/circuit_breaker.py`
  - Configure: 5 failures in 30s → open, 60s recovery
  - Wrap adapter calls with circuit breaker
  - _Requirements: 5.5, 5.6, 5.7_

- [x] 4.4 Checkpoint - Verify providers
  - Test provider listing with filters
  - Test pagination
  - Test caching behavior
  - Ask the user if questions arise

---

### Phase 5: KPI Service

- [x] 5.1 Implement KPI Engine
  - Create `apps/kpi/services.py` with `KPIEngine` class
  - Implement `calculate_cost_per_token()` using GPU benchmarks
  - Implement `calculate_cost_per_gflop()` using GPU benchmarks
  - Use Django ORM aggregations: `Avg`, `Count`, `StdDev`
  - _Requirements: 6.5, 6.6_

- [x] 5.2 Implement KPI Endpoints
  - Create `apps/kpi/schemas.py` with Pydantic schemas
  - Create `apps/kpi/api.py` with Django Ninja router
  - Implement `GET /kpi/overview`
  - Implement `GET /kpi/gpu/{gpu_type}`
  - Implement `GET /kpi/provider/{provider_name}`
  - Implement `GET /kpi/insights/market`
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.7_

- [x] 5.3 Checkpoint - Verify KPI
  - Test all KPI endpoints
  - Verify calculations are correct
  - Ask the user if questions arise

---

### Phase 6: Math Core Service

- [x] 6.1 Migrate Algorithm Modules
  - Create `apps/math_core/algorithms/` directory
  - Copy `algorithms/topsis.py`
  - Copy `algorithms/collaborative.py`
  - Copy `algorithms/content_based.py`
  - Copy `algorithms/ensemble.py`
  - Copy `algorithms/workload_mapper.py`
  - Copy `algorithms/price_analytics.py`
  - Copy `algorithms/ranking_engine.py`
  - Copy `core/kpi_calculator.py`
  - Copy `core/benchmarks.py`
  - Update imports to use Django app paths
  - _Requirements: 7.8_

- [x] 6.2 Implement Math Core Endpoints
  - Create `apps/math_core/schemas.py` with all Pydantic schemas
  - Create `apps/math_core/api.py` with Django Ninja router
  - Implement `POST /math/cost-per-token`
  - Implement `POST /math/cost-per-gflop`
  - Implement `POST /math/topsis`
  - Implement `POST /math/ensemble-recommend`
  - Implement `POST /math/estimate-workload`
  - Implement `GET /math/benchmarks`
  - Implement `GET /math/benchmarks/{gpu_type}`
  - Validate weights sum to 1.0 for TOPSIS
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.9_

- [x] 6.3 Checkpoint - Verify Math Core
  - Test all math endpoints
  - Verify calculations are correct
  - Ask the user if questions arise

---

### Phase 7: AI Assistant Service

- [x] 7.1 Migrate SomaAgent Client
  - Copy `client.py` to `apps/ai_assistant/client.py`
  - Update imports
  - Verify async HTTP calls work with Django
  - _Requirements: 8.2_

- [x] 7.2 Implement AI Assistant Endpoints
  - Create `apps/ai_assistant/schemas.py` with Pydantic schemas
  - Create `apps/ai_assistant/services.py` with business logic
  - Create `apps/ai_assistant/api.py` with Django Ninja router
  - Implement `POST /ai/chat` with history trimming (max 10 turns)
  - Implement `POST /ai/parse-workload`
  - Implement `GET /ai/sessions/{session_id}/history`
  - Implement `GET /ai/tools`
  - Implement `GET /ai/health`
  - Enrich responses with Math Core recommendations
  - _Requirements: 8.1, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 8.9_

- [x] 7.3 Checkpoint - Verify AI Assistant
  - Test chat endpoint
  - Test workload parsing
  - Verify SomaAgent integration works
  - Ask the user if questions arise

---

### Phase 8: WebSocket Gateway

- [x] 8.1 Configure Django Channels
  - Add `channels` and `channels_redis` to `INSTALLED_APPS`
  - Configure `CHANNEL_LAYERS` with Redis backend
  - Update `asgi.py` to include Channels routing
  - Configure Daphne or Uvicorn for ASGI
  - _Requirements: 9.7, 9.8_

- [x] 8.2 Implement WebSocket Consumer
  - Create `apps/websocket_gateway/consumers.py` with `PriceUpdateConsumer`
  - Implement `connect()` to join `price_updates` group
  - Implement `disconnect()` to leave group
  - Implement `price_update()` to broadcast messages
  - Implement heartbeat every 30 seconds
  - Create `apps/websocket_gateway/routing.py` with WebSocket URL patterns
  - _Requirements: 9.1, 9.2, 9.4, 9.5, 9.6_

- [x] 8.3 Implement Redis Subscriber
  - Create background task to subscribe to Redis `price_updates` channel
  - Forward messages to Channels group
  - Handle reconnection on Redis disconnect
  - _Requirements: 9.3_

- [x] 8.4 Checkpoint - Verify WebSocket
  - Test WebSocket connection
  - Test message broadcast
  - Test heartbeat
  - Ask the user if questions arise

---

### Phase 9: Admin Interface

- [x] 9.1 Configure Django Admin
  - Create `apps/auth_app/admin.py` with `UserAdmin`, `TenantAdmin`, `AuditLogAdmin`
  - Create `apps/providers/admin.py` with `ProviderAdmin`, `GPUOfferAdmin`
  - Create `apps/math_core/admin.py` with `GPUBenchmarkAdmin`
  - Configure list displays, filters, search fields
  - Create superuser via migration or management command
  - _Requirements: 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7_

---

### Phase 10: Observability

- [x] 10.1 Configure Logging
  - Configure structured JSON logging in `settings/base.py`
  - Add request logging middleware
  - Include trace_id in all log entries
  - Redact sensitive data (JWT tokens, API keys)
  - _Requirements: 13.1, 13.2, 19.7_

- [x] 10.2 Configure Metrics
  - Add `django-prometheus` to `INSTALLED_APPS`
  - Add Prometheus middleware
  - Expose `/metrics` endpoint
  - Track: request_count, request_latency_seconds, error_count
  - _Requirements: 13.3, 13.4_

- [x] 10.3 Configure Tracing
  - Install `opentelemetry-instrumentation-django`
  - Configure W3C Trace Context propagation
  - Export traces to configured collector
  - _Requirements: 13.5_

---

### Phase 11: Health Checks

- [x] 11.1 Implement Health Endpoint
  - Create `/health` endpoint in root URL config
  - Check database connectivity
  - Check Redis connectivity
  - Return JSON: `{status, database, cache, timestamp}`
  - Response time ≤100ms
  - _Requirements: 1.6, 13.6_

---

### Phase 12: Testing

- [x] 12.1 Set Up Test Infrastructure
  - Configure `pytest-django` with `DJANGO_SETTINGS_MODULE`
  - Create `conftest.py` with fixtures
  - Configure test database
  - _Requirements: 14.1, 14.3_

- [x] 12.2 Write Auth Tests
  - Test user registration
  - Test user login
  - Test JWT token issuance and validation
  - Test token refresh
  - Test protected endpoint access
  - _Requirements: 14.6_

- [x] 12.3 Write Provider Tests
  - Test provider listing with filters
  - Test pagination
  - Test caching behavior
  - Test rate limiting
  - _Requirements: 14.7_

- [x] 12.4 Write KPI Tests
  - Test KPI overview endpoint
  - Test GPU metrics endpoint
  - Test provider KPI endpoint
  - Test market insights endpoint
  - _Requirements: 14.5_

- [x] 12.5 Write Math Core Tests
  - Test cost-per-token calculation
  - Test TOPSIS algorithm
  - Test ensemble recommendations
  - Test workload estimation
  - _Requirements: 14.5_

- [x] 12.6 Write WebSocket Tests
  - Test WebSocket connection
  - Test message broadcast
  - Test heartbeat
  - Test disconnection cleanup
  - _Requirements: 14.4_

- [x] 12.7 Write Parity Tests
  - Compare v1 and v2 responses for same inputs
  - Verify response schemas match
  - Verify error formats match
  - _Requirements: 14.5_

- [x] 12.8 Checkpoint - Verify tests pass
  - Ensure all tests pass
  - Verify coverage ≥80%
  - Ask the user if questions arise

---

### Phase 13: Deployment

- [x] 13.1 Create Dockerfile
  - Create multi-stage Dockerfile with `python:3.12-slim`
  - Install dependencies with `pip install --no-cache-dir`
  - Configure entrypoint to run migrations then start server
  - Add `HEALTHCHECK` instruction
  - _Requirements: 20.1, 20.2, 20.3, 20.4_

- [x] 13.2 Update Docker Compose
  - Django service configured in `docker-compose.yml`
  - Configure environment variables
  - Configure volume mounts for development
  - _Requirements: 15.1_

- [x] 13.3 Configure Nginx Routing
  - Route `/api/v2/*` to Django service
  - Route `/ws/` to Django Channels
  - Configure WebSocket upgrade headers
  - _Requirements: 15.2, 15.3_

---

### Phase 14: Migration Verification

- [x] 14.1 Run Parity Tests
  - Execute parity test suite
  - Verify all endpoints return identical responses
  - Document any intentional differences
  - _Requirements: 15.4_

- [x] 14.2 Performance Benchmarking
  - Run load tests with Locust
  - Verify p95 latency ≤200ms for cached requests
  - Document results
  - _Requirements: 18.6_

- [x] 14.3 Security Audit
  - Verify HTTPS redirect in production
  - Verify secure cookie settings
  - Verify CSRF protection
  - Verify rate limiting
  - Run security scanner
  - _Requirements: 19.1, 19.2, 19.3, 19.4, 19.5, 19.6_

- [x] 14.4 Final Checkpoint
  - Ensure all tests pass
  - Verify dual-stack operation works
  - Document migration completion
  - Ask the user if questions arise

---

## Notes

- All tasks are required for comprehensive migration
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Estimated total duration: ~33 days

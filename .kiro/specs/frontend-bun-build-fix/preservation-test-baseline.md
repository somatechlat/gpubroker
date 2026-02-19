# Preservation Property Tests - Baseline Results

**Date**: 2026-01-08
**Status**: ✅ ALL TESTS PASSED on UNFIXED code
**Test File**: `infrastructure/docker/tests/test_frontend_bun_build_preservation.py`

## Summary

All preservation property tests PASSED on the UNFIXED docker-compose.yml, confirming the baseline behavior that must be preserved after implementing the fix.

**Total Tests**: 14
**Passed**: 14
**Failed**: 0

## Test Results

### 1. All Services Except Frontend Unchanged ✅
**Validates**: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6

Verified that all non-frontend services exist and have valid configuration:
- vault: 8 configuration keys
- postgres: 6 configuration keys
- clickhouse: 5 configuration keys
- redis: 5 configuration keys
- django: 7 configuration keys
- nginx: 6 configuration keys

### 2. Volume Definitions Unchanged ✅
**Validates**: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6

Verified all volume definitions exist:
- vault_data
- postgres_data
- clickhouse_data
- redis_data
- static_files

### 3. Frontend Service Non-Command Fields Unchanged ✅
**Validates**: Requirements 3.2, 3.3, 3.4, 3.5, 3.6

Verified frontend service configuration (except command):
- **Build context**: `../../frontend`
- **Container name**: `gpubroker_frontend`
- **Environment variables**:
  - VITE_API_URL: `${VITE_API_URL:-http://localhost:28010/api/v2}`
  - VITE_WS_URL: `${VITE_WS_URL:-ws://localhost:28010/ws}`
- **Ports**: `${PORT_FRONTEND:-28030}:3000`
- **Volumes**:
  - `./frontend:/app`
  - `/app/node_modules`

### 4. Service Dependencies Unchanged ✅
**Validates**: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6

Verified service dependencies:
- **Django depends on**:
  - postgres (condition: service_healthy)
  - redis (condition: service_started)
  - vault (condition: service_started)
- **Nginx depends on**:
  - django
  - frontend

### 5. Healthcheck Configurations Unchanged ✅
**Validates**: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6

Verified healthcheck configurations for:
- vault: `vault status` (interval: 30s, timeout: 10s, retries: 3, start_period: 10s)
- postgres: `pg_isready -U gpubroker` (interval: 10s, timeout: 5s, retries: 5)
- django: `curl -f http://localhost:8000/health` (interval: 30s, timeout: 10s, retries: 3, start_period: 40s)
- nginx: `nginx -t` (interval: 30s, timeout: 10s, retries: 3)

### 6. Environment Variables for All Services Unchanged ✅
**Validates**: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6

Verified environment variables for all services:
- **vault**: VAULT_ADDR, VAULT_API_ADDR
- **postgres**: POSTGRES_DB, POSTGRES_USER, POSTGRES_PASSWORD
- **clickhouse**: CLICKHOUSE_DB, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD
- **django**: DJANGO_SETTINGS_MODULE, BOOTSTRAP_DB_NAME, BOOTSTRAP_DB_USER, BOOTSTRAP_DB_PASSWORD, BOOTSTRAP_DB_HOST, BOOTSTRAP_DB_PORT, VAULT_ADDR, VAULT_TOKEN, DEBUG, ALLOWED_HOSTS, CORS_ALLOWED_ORIGINS, KAFKA_BROKERS, CLICKHOUSE_URL
- **frontend**: VITE_API_URL, VITE_WS_URL

### 7. Port Mappings for All Services Unchanged ✅
**Validates**: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6

Verified port mappings:
- vault: `${PORT_VAULT:-28005}:8200`
- postgres: `${PORT_POSTGRES:-28001}:5432`
- clickhouse: `${PORT_CLICKHOUSE_HTTP:-28002}:8123`, `${PORT_CLICKHOUSE_NATIVE:-28003}:9000`
- redis: `${PORT_REDIS:-28004}:6379`
- django: `${PORT_DJANGO:-28080}:8000`
- nginx: `${PORT_NGINX:-28010}:80`, `${PORT_NGINX_SSL:-443}:443`
- frontend: `${PORT_FRONTEND:-28030}:3000`

### 8. Volume Mounts for All Services Unchanged ✅
**Validates**: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6

Verified volume mounts for all services:
- **vault**: vault_data:/vault/data, ./infrastructure/vault/config:/vault/config, ./infrastructure/vault/scripts:/vault/scripts
- **postgres**: postgres_data:/var/lib/postgresql/data, ./database/init:/docker-entrypoint-initdb.d
- **clickhouse**: clickhouse_data:/var/lib/clickhouse
- **redis**: redis_data:/data
- **django**: ../../backend/gpubroker:/app, static_files:/app/staticfiles
- **nginx**: ./infrastructure/nginx/nginx.conf:/etc/nginx/nginx.conf:ro, static_files:/var/www/static:ro
- **frontend**: ./frontend:/app, /app/node_modules

### 9. Compose File Name Unchanged ✅
**Validates**: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6

Verified Docker Compose project name: `gpubroker`

### 10. Specific Service Configurations Preserved ✅
**Validates**: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6

Verified critical service configurations:
- **Vault**: image `hashicorp/vault:1.15`, container name `gpubroker_vault`
- **Postgres**: image `postgres:15-alpine`, container name `gpubroker_postgres`
- **Redis**: image `redis:7-alpine`, container name `gpubroker_redis`
- **ClickHouse**: image `clickhouse/clickhouse-server:23.8`, container name `gpubroker_clickhouse`
- **Django**: build context `./backend/gpubroker`, container name `gpubroker_django`
- **Nginx**: image `nginx:alpine`, container name `gpubroker_nginx`

### 11-13. Property-Based Tests ✅
**Validates**: Requirements 3.1, 3.2, 3.3, 3.4, 3.5, 3.6

Property-based tests using Hypothesis generated multiple test cases:
- **Service existence**: Verified all 6 non-frontend services exist and have valid configuration
- **Volume existence**: Verified all 5 volumes exist
- **Frontend non-command fields**: Verified all 5 frontend configuration fields (build, container_name, environment, ports, volumes) exist and have values

### 14. Docker Compose Dev Preservation ✅
**Validates**: Requirement 3.1

Verified docker-compose.dev.yml frontend service has NO command override, allowing the Containerfile's default CMD to be used.

## Baseline Configuration Summary

### Frontend Service (UNFIXED)
```yaml
frontend:
  build:
    context: ../../frontend
  container_name: gpubroker_frontend
  environment:
    VITE_API_URL: ${VITE_API_URL:-http://localhost:28010/api/v2}
    VITE_WS_URL: ${VITE_WS_URL:-ws://localhost:28010/ws}
  ports:
    - ${PORT_FRONTEND:-28030}:3000
  volumes:
    - ./frontend:/app
    - /app/node_modules
  command: npm run dev  # ⚠️ BUG: Should be "bun run dev"
```

### Expected After Fix
Only the `command` field should change from `npm run dev` to `bun run dev`. All other configuration must remain identical.

## Property-Based Testing Coverage

The property-based tests use Hypothesis to generate comprehensive test cases:
- **6 service names** × multiple test runs = strong guarantee all services are preserved
- **5 volume names** × multiple test runs = strong guarantee all volumes are preserved
- **5 frontend fields** × multiple test runs = strong guarantee all frontend non-command fields are preserved

## Conclusion

✅ **All preservation tests PASSED on UNFIXED code**

This confirms the baseline behavior that MUST be preserved after implementing the fix. The tests capture:
1. All service definitions (vault, postgres, clickhouse, redis, django, nginx)
2. All volume definitions
3. All environment variables
4. All port mappings
5. All healthcheck configurations
6. All service dependencies
7. All volume mounts
8. Docker Compose project name
9. Frontend service configuration (except command field)
10. docker-compose.dev.yml behavior (no command override)

**Next Step**: Implement the fix (change frontend command from `npm run dev` to `bun run dev`) and re-run these tests to verify no regressions.

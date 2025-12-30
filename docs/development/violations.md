# Violations Log (Vibe Coding Rules)

This document tracks violations of the Vibe Coding Rules discovered during development. Each entry includes the date, description, and resolution status.

---

## 2025-12-11

- Root `Dockerfile` referenced non-existent monolith layout (`backend.app.main`, `/frontend/build`) — removed.
- Port literals scattered across compose files, scripts, and docs (3000/800x/9000/9090/etc.), causing drift and conflicts; no centralized port variables; requirement to use 28000+ unmet.
- `docker-compose.dev.yml` and `docker-compose.yml` diverge in services and ports; websocket gateway missing in dev; price-feed reuses provider image ambiguously. (resolved: dev compose aligned, price-feed service removed)
- `start-dev.sh` hardcodes old ports and health checks; will mislead once ports change; does not source .env.
- `.env.example` hardcodes legacy ports/URLs and suggests putting secrets locally despite Vault policy.
- `README.md` and `DEPLOYMENT_SETUP.md` contain outdated ports and unsafe guidance (copying API keys into .env, pushing with secrets).
- backend/README.md lists non-existent services (api-gateway, prediction-service, project-service, notification-service) and gRPC usage not reflected in code—outdated/incorrect docs.
- frontend `src/app/settings/page.tsx` hardcoded provider API base `http://localhost:8002`; fixed to env/proxy-driven URL.
- frontend `next.config.js` defaulted to legacy port 8080 for API/WS; fixed to require env (no wrong default).
- Duplicate roadmap file `SPRONTED_ROADMAP.md` removed; canonical `ROADMAP.md` retained.
- Backend service ports hardcoded to 8001/8002/8003; unified to env-driven ports with 8000 default.
- `start-dev.sh` assumed docker-compose default file and commands; now respects `COMPOSE_FILE` and prints correct commands.
- Frontend relied on Next internal proxy `/api/providers` and placeholder marketplace/detail stub; now requires real `NEXT_PUBLIC_PROVIDER_API_URL`, removed stub routes/components.
- README/DEPLOYMENT docs claimed Helm/K8s assets and wrong port mapping; aligned with actual stack and removed nonexistent artifacts.
- AWS SageMaker adapter contained dead duplicated block causing IndentationError; cleaned live pricing parser.

## 2025-12-12

- Removed hardcoded database DSN default from `backend/provider-service/db.py`; DATABASE_URL now required (no embedded secrets).
- Enforced explicit REDIS_URL for WebSocket gateway (was hardcoded with password); service now rejects missing env.
- Sanitized `docs/PROVIDER_API_KEYS_LINKS.md` by deleting inline internal credentials section to prevent secret leakage.
- Purged hardcoded dev passwords from `docker-compose.yml`/`.dev.yml`; all secrets now provided via required environment variables (POSTGRES_PASSWORD, CLICKHOUSE_PASSWORD, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY, database/redis URLs).
- Updated `infrastructure/vault/scripts/store-secrets.sh` to prompt for DB/Redis/ClickHouse passwords instead of defaulting to dev values; aligns with "no hardcoded secrets".
- `start-dev.sh` no longer prints example database credentials; points to env/Vault instead.
- Removed silent `pass` handlers in provider-service (lifespan cleanup, config save validation, cache get/set) and ingestion Kafka/Redis publishers; now validate credentials, log failures, and avoid swallowed errors.
- WebSocket gateway now logs Redis close failures instead of swallowing exceptions.
- Ranking engine abstract method now raises `NotImplementedError` to prevent stub behavior.
- Frontend FilterPanel expanded to full production filters (gpu_type, memory min/max, price min/max, region, availability, compliance tags, provider_name) with URL-driven state; removed placeholder two-option filter.
- `.env.example` updated to include required secret and connection variables (POSTGRES_PASSWORD, CLICKHOUSE_PASSWORD, REDIS_PASSWORD, JWT_PRIVATE_KEY, JWT_PUBLIC_KEY, DATABASE_URL_*, REDIS_URL_*, CLICKHOUSE_URL) without hardcoded defaults.
- Auth service now mandates RS256 JWTs with required `JWT_PRIVATE_KEY`/`JWT_PUBLIC_KEY`; removed shared-secret default and compose/env/Vault scripts updated accordingly.
- AI Assistant now requires SOMA_AGENT_BASE env (no localhost default) in both client and service; compose updated to require explicit value.
- Added AI Assistant service to dev compose with required env (SOMA_AGENT_BASE, LLM_PROVIDER) and removed missing-service gap; `.env.example`/README updated accordingly.
- Removed dev credential defaults from `.env.example` (DB/ClickHouse/Redis URLs) to eliminate hardcoded secrets; single source of env placeholders only.

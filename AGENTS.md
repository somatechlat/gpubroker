# AGENTS CONTEXT: GPUBROKER

This file captures project context and findings from a full repo read so the
next agent can pick up without re-scanning everything.

## Scope of reading
- Read source code and docs across backend, frontend, infrastructure, and tests.
- Skipped only lockfiles and binary images:
  - frontend/package-lock.json
  - frontend/bun.lock
  - backend/gpubroker/screenshots/*

## Key constraints (must follow)
- See: rules.md and docs/development/vibe-coding-rules.md
- Django 5 + Django Ninja only; use Django ORM (no raw SQL).
- Frontend UI must be Lit web components (no React).
- Do not guess requirements; read SRS/user journeys first.

## Repository map (high level)
- backend/gpubroker:
  - gpubrokeradmin (control plane, admin UI + Ninja API)
  - gpubrokerpod (data plane)
    - gpubrokerapp (user-facing)
    - gpubrokeragent (agentic layer wrapper)
  - config (main settings + API wiring)
- frontend (Lit UI with Tailwind tokens, Vite-style entry)
- backend/gpubroker/gpubrokerlandingpage (marketing site + enrollment modal)
- infrastructure (AWS, Vault, Redis, Postgres, Prometheus/Grafana, SpiceDB)
- docs (SRS, journeys, environment vars, OpenAPI, infra)

## Key entry points
- API wiring: backend/gpubroker/config/api/__init__.py
- Alternate API module exists (may be legacy): backend/gpubroker/gpubroker/api/v2/__init__.py

## Notable findings / risks
- Product scope note (user): full broker + pod deployment + monitoring in one place.
- Payments are external; platform needs configuration and ingestion only (no internal charge capture).
- Code currently mixes internal payment capture with deployment triggers; needs alignment:
  - backend/gpubroker/gpubrokeradmin/services/payments/paypal.py
  - backend/gpubroker/gpubrokeradmin/apps/subscriptions/services.py
  - backend/gpubroker/gpubrokeradmin/api/router.py
- Hardcoded PayPal sandbox creds and JWT RSA keys in backend/gpubroker/start_server.sh.
- Hardcoded PayPal sandbox creds in E2E tests:
  - backend/gpubroker/tests/e2e/test_paypal_sandbox.py
  - backend/gpubroker/tests/e2e/test_enrollment_flow.py
  - backend/gpubroker/tests/e2e/test_complete_e2e_flow.py
- apps/core/signals.py references .models.Provider but core has no models.py:
  - backend/gpubroker/apps/core/signals.py
- integration_test.py has stray text before shebang:
  - backend/gpubroker/integration_test.py
- Frontend stack mismatch:
  - frontend/README.md and frontend/package.json reference Next.js
  - actual entry is Lit + Vite (frontend/index.html, frontend/src/main.ts)
- Geo detection calls external IP APIs (needs prod allowlist/timeouts):
  - backend/gpubroker/gpubrokeradmin/services/geo.py
- PayPal pending transactions stored in memory (not persistent):
  - backend/gpubroker/gpubrokeradmin/services/payments/paypal.py
- Agent Zero source expected in gitignored TMP/agent-zero (stub integration):
  - backend/gpubroker/gpubrokerpod/gpubrokeragent/apps/agent_core/services.py

## Testing overview
- Playwright E2E:
  - backend/gpubroker/tests/e2e/*
  - frontend/tests/e2e/*
- Integration test script (hits live APIs):
  - backend/gpubroker/integration_test.py
- PayPal unit/property tests:
  - backend/gpubroker/tests/unit/test_paypal_service.py

## Docs to start with
- SRS: docs/srs/GPUBroker_SRS.md (plus related SRS files)
- Journeys: docs/user-journeys/*
- Env vars: docs/ENVIRONMENT-VARIABLES.md
- Vibe rules: rules.md and docs/development/vibe-coding-rules.md

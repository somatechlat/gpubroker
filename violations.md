# Violations Log (Vibe Coding Rules)

- 2025-12-11: Root `Dockerfile` referenced non-existent monolith layout (`backend.app.main`, `/frontend/build`) — removed.
- 2025-12-11: Port literals scattered across compose files, scripts, and docs (3000/800x/9000/9090/etc.), causing drift and conflicts; no centralized port variables; requirement to use 28000+ unmet.
- 2025-12-11: `docker-compose.dev.yml` and `docker-compose.yml` diverge in services and ports; websocket gateway missing in dev; price-feed reuses provider image ambiguously.
- 2025-12-11: `start-dev.sh` hardcodes old ports and health checks; will mislead once ports change; does not source .env.
- 2025-12-11: `.env.example` hardcodes legacy ports/URLs and suggests putting secrets locally despite Vault policy.
- 2025-12-11: `README.md` and `DEPLOYMENT_SETUP.md` contain outdated ports and unsafe guidance (copying API keys into .env, pushing with secrets).
- 2025-12-11: backend/README.md lists non-existent services (api-gateway, prediction-service, project-service, notification-service) and gRPC usage not reflected in code—outdated/incorrect docs.
- 2025-12-11: frontend `src/app/settings/page.tsx` hardcoded provider API base `http://localhost:8002`; fixed to env/proxy-driven URL.
- 2025-12-11: frontend `next.config.js` defaulted to legacy port 8080 for API/WS; fixed to require env (no wrong default).
- 2025-12-11: Duplicate roadmap file `SPRONTED_ROADMAP.md` removed; canonical `ROADMAP.md` retained.

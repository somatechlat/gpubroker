⚠️ **WARNING: REAL IMPLEMENTATION ONLY** ⚠️

> **We do NOT mock, bypass, or invent data. We use ONLY real servers, real APIs, and real data. This codebase follows principles of truth, simplicity, and elegance in every line of code.**

---

# GPUBROKER Backend Services

## Microservices Architecture

### Core Services (current codebase)
1. **auth-service** — FastAPI; JWT/MFA/RBAC; depends on PostgreSQL & Redis.
2. **provider-service** — FastAPI; provider adapters, ingestion, Kafka producer; uses PostgreSQL, Redis, Vault, Math Core.
3. **kpi-service** — FastAPI; KPIs/analytics; PostgreSQL, ClickHouse, Redis.
4. **math-core** — FastAPI; GPUMathBroker algorithms (TOPSIS/ALS/content/benchmarks/workload mapping).
5. **ai-assistant** — FastAPI; SomaAgent gateway proxy and workload parser.
6. **websocket-gateway** — FastAPI WebSocket bridge; Redis Pub/Sub → clients.
7. **shared** — common Python utilities (e.g., Vault client).

## Development Setup
```bash
# Run full stack (uses ports from .env; defaults 28xxx)
docker-compose -f docker-compose.dev.yml up --build

# Run individual service (example)
cd backend/auth-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## Service Communication
- **External**: REST APIs with OpenAPI docs.
- **Real-time**: WebSocket gateway subscribes to Redis Pub/Sub `price_updates`.
- **Async events**: Kafka (price updates, ingestion) where configured.

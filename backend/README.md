⚠️ **WARNING: REAL IMPLEMENTATION ONLY** ⚠️

> **We do NOT mock, bypass, or invent data. We use ONLY real servers, real APIs, and real data. This codebase follows principles of truth, simplicity, and elegance in every line of code.**

---

# GPUBROKER Backend Services

## Microservices Architecture

### Core Services
1. **api-gateway** - Envoy-based API gateway with routing and auth
2. **auth-service** - JWT, MFA, RBAC, user management  
3. **provider-service** - Provider SDK and adapter management
4. **kpi-service** - Cost calculations, analytics, KPI computation
5. **prediction-service** - ML-based cost prediction and recommendations
6. **project-service** - Project wizard and infrastructure planning
7. **notification-service** - Real-time updates via WebSocket

## Development Setup
```bash
# Run all services in development
docker-compose up --build

# Run individual service
cd backend/auth-service
poetry install
poetry run uvicorn main:app --reload --port 8001
```

## Service Communication
- **Internal**: gRPC for high-performance inter-service communication
- **External**: REST APIs with OpenAPI documentation
- **Real-time**: WebSocket for live price updates
- **Message Queue**: Redis Streams for async processing
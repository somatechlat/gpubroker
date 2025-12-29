# GPUBROKER Backend

## Architecture

GPUBROKER backend is built on **Django 5 + Django Ninja**, providing a unified API for GPU marketplace operations.

### Stack

- **Framework**: Django 5.x with Django Ninja for REST APIs
- **Database**: PostgreSQL 15 with Django ORM
- **Cache**: Redis 7 with django-redis
- **WebSocket**: Django Channels with channels-redis
- **Authentication**: JWT (RS256) with python-jose
- **Observability**: django-prometheus, OpenTelemetry

### Project Structure

```
backend/
├── gpubroker/                    # Django project
│   ├── apps/                     # Django applications
│   │   ├── auth_app/             # Authentication & users
│   │   ├── providers/            # GPU provider marketplace
│   │   ├── kpi/                  # KPI calculations
│   │   ├── math_core/            # Mathematical algorithms
│   │   ├── ai_assistant/         # AI chat integration
│   │   └── websocket_gateway/    # Real-time updates
│   ├── gpubroker/                # Project settings
│   │   ├── settings/
│   │   │   ├── base.py           # Common settings
│   │   │   ├── development.py    # Dev overrides
│   │   │   ├── production.py     # Prod settings
│   │   │   └── test.py           # Test settings
│   │   ├── api/v2/               # Django Ninja API
│   │   ├── asgi.py               # ASGI config
│   │   └── urls.py               # URL routing
│   ├── tests/                    # Test suite
│   ├── manage.py
│   ├── requirements.txt
│   └── Dockerfile
└── shared/                       # Shared utilities
    ├── vault_client.py           # HashiCorp Vault client
    └── audit_hash.py             # Audit log hashing
```

### API Endpoints

All endpoints are available at `/api/v2/`:

| Endpoint | Description |
|----------|-------------|
| `/api/v2/auth/` | Authentication (register, login, refresh, me) |
| `/api/v2/providers/` | GPU marketplace (list, filter, config) |
| `/api/v2/kpi/` | KPI metrics (overview, gpu, provider, insights) |
| `/api/v2/math/` | Calculations (cost-per-token, TOPSIS, workload) |
| `/api/v2/ai/` | AI assistant (chat, parse-workload) |
| `/ws/` | WebSocket (price updates, notifications) |

### Running Locally

```bash
# Install dependencies
pip install -r gpubroker/requirements.txt

# Set environment variables
export DATABASE_URL=postgresql://user:pass@localhost:5432/gpubroker
export REDIS_URL=redis://localhost:6379/0
export JWT_PRIVATE_KEY="..."
export JWT_PUBLIC_KEY="..."
export SECRET_KEY="your-secret-key"

# Run migrations
python gpubroker/manage.py migrate

# Start development server
python gpubroker/manage.py runserver

# Or with Daphne (for WebSocket support)
daphne -b 0.0.0.0 -p 8000 gpubroker.asgi:application
```

### Running Tests

```bash
cd gpubroker
pytest -v

# With coverage
pytest --cov=apps --cov-report=html
```

### Docker

```bash
# Build
docker build -t gpubroker-backend ./gpubroker

# Run
docker run -p 8000:8000 \
  -e DATABASE_URL=... \
  -e REDIS_URL=... \
  gpubroker-backend
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection URL |
| `REDIS_URL` | Yes | Redis connection URL |
| `SECRET_KEY` | Yes | Django secret key |
| `JWT_PRIVATE_KEY` | Yes | RS256 private key for JWT signing |
| `JWT_PUBLIC_KEY` | Yes | RS256 public key for JWT verification |
| `VAULT_ADDR` | No | HashiCorp Vault address |
| `SOMA_AGENT_BASE` | No | SomaAgent URL for AI features |
| `DEBUG` | No | Enable debug mode (default: False) |
| `ALLOWED_HOSTS` | No | Comma-separated allowed hosts |

# GPUBROKER

AI-Powered GPU Marketplace & Control Tower SaaS

A unified platform that aggregates GPU offers from multiple providers with real-time pricing, AI-powered recommendations, and intelligent cost optimization.

---

## Architecture

GPUBROKER is built on Django 5 + Django Ninja as the unified backend framework:

- **Backend**: Django 5 monolith with Django Ninja API (`/api/v2/`)
- **Database**: PostgreSQL 15 with Django ORM
- **Cache**: Redis 7 for sessions, caching, and real-time price feeds
- **WebSocket**: Django Channels for real-time updates
- **Observability**: Prometheus + Grafana

### Project Structure

```
gpubroker/
├── backend/
│   └── gpubroker/
│       ├── config/              # Django settings, URLs, ASGI
│       ├── gpubrokeradmin/      # Admin dashboard & enrollment flow
│       ├── gpubrokerlandingpage/# Landing page static files
│       ├── gpubrokerpod/        # GPU Agent POD management
│       └── shared/              # Shared utilities, middleware
├── docs/                        # Documentation
│   ├── development/             # Coding rules, violations log
│   ├── infrastructure/          # Deployment, roadmap
│   ├── srs/                     # Software Requirements Specs
│   ├── ui-ux/                   # UI/UX specifications
│   └── user-journeys/           # User journey documentation
├── frontend/                    # Lit 3 + Vite frontend
├── infrastructure/              # Vault, scripts
```

---

## Quick Start

### Option 1: Docker Compose (Recommended for Quick Testing)

**Prerequisites**: Docker & Docker Compose

```bash
# 1. Clone and setup
git clone https://github.com/somatechlat/gpubroker.git
cd gpubroker

# 2. Setup Docker environment
cd docker
./start.sh
```

The `start.sh` script will:
- Create `.env` file from template
- Validate all required secrets
- Build and start all services
- Wait for health checks
- Provide access URLs

**Access Points**:
- Main Dashboard: http://localhost:10355
- API: http://localhost:10355/api/v2
- Airflow: http://localhost:10355/airflow
- Grafana: http://localhost:10355/grafana

See [infrastructure/docker/README.md](infrastructure/docker/README.md) for full details.

### Option 2: Kubernetes + Tilt (Production-like Development)

**Prerequisites**:
- Minikube (vfkit driver)
- Tilt
- kubectl
- Python 3.11+
- Node.js 18+ (for frontend)

```bash
# 1. Clone and setup
git clone https://github.com/somatechlat/gpubroker.git
cd gpubroker

# 2. Configure environment
cp .env.example .env
# Edit .env with your secrets

# 3. Start Minikube (isolated profile)
minikube start -p gpubroker --driver=vfkit --container-runtime=containerd --disk=10g --memory=8g --cpus=4 --addons=ingress
kubectl config use-context gpubroker

# 4. Export required secrets (see docs/infrastructure/deployment-setup.md)
export POSTGRES_PASSWORD=...
export CLICKHOUSE_PASSWORD=...
export DJANGO_SECRET_KEY=...
export JWT_PRIVATE_KEY=...
export JWT_PUBLIC_KEY=...
export GRAFANA_PASSWORD=...
export SPICEDB_KEY=...
export AIRFLOW__CORE__FERNET_KEY=...
export AIRFLOW_ADMIN_PASSWORD=...
export VAULT_TOKEN=...

# 5. Start Tilt
tilt up
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Landing Page | http://localhost:10355/ | Public landing page |
| Admin Dashboard | http://localhost:10355/admin/ | Admin login & dashboard |
| API Docs | http://localhost:10355/api/v2/docs | OpenAPI documentation |
| Enrollment | http://localhost:10355/checkout | Subscription checkout |

### Default Admin Credentials

- **Email**: `admin@gpubroker.io`
- **Password**: `admin123`

---

## API Endpoints

All endpoints available at `/api/v2/`:

| Endpoint | Description |
|----------|-------------|
| `/api/v2/admin/public/admin/login` | Admin authentication |
| `/api/v2/subscription/plans` | Available subscription plans |
| `/api/v2/subscription/checkout` | Create PayPal order |
| `/api/v2/subscription/capture` | Capture PayPal payment |
| `/api/v2/subscription/activate` | Activate POD deployment |
| `/api/v2/providers/` | GPU marketplace (list, filter) |
| `/api/v2/kpi/` | KPI metrics |
| `/api/v2/math/` | TOPSIS calculations |

---

## Key Features

### GPUBROKER POD SaaS
- **Subscription Plans**: Starter ($49/mo), Professional ($149/mo), Enterprise ($499/mo)
- **PayPal Integration**: Sandbox and production payment processing
- **Automated Deployment**: AWS infrastructure provisioning
- **Admin Dashboard**: Customer management, billing, costs tracking

### Provider Adapters (Implemented)
- RunPod
- Vast.ai

### AI-Powered Intelligence
- Cost-per-Token / Cost-per-GFLOP KPIs
- TOPSIS + Ensemble Ranking algorithms
- Workload estimation and templates

### Real-Time Features
- Live price updates via WebSocket
- Django Channels for real-time communication
- Redis Pub/Sub for price broadcasts

---

## Development

### Running Tests

```bash
# Unit tests
cd backend/gpubroker
pytest tests/unit/ -v

# E2E tests (requires running server)
pytest tests/e2e/ -v --headed

# All tests
pytest -v
```

### Code Quality

```bash
# Linting
ruff check backend/

# Type checking
mypy backend/gpubroker/
```

### Django Commands

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Django shell
python manage.py shell
```

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection URL |
| `REDIS_URL` | Yes | Redis connection URL |
| `DJANGO_SECRET_KEY` | Yes | Django secret key |
| `PAYPAL_CLIENT_ID` | Yes | PayPal API client ID |
| `PAYPAL_CLIENT_SECRET` | Yes | PayPal API secret |
| `PAYPAL_MODE` | Yes | `sandbox` or `live` |

---

## Documentation

| Document | Location | Description |
|----------|----------|-------------|
| Roadmap | [docs/infrastructure/roadmap.md](docs/infrastructure/roadmap.md) | Development roadmap |
| Deployment | [docs/infrastructure/deployment-setup.md](docs/infrastructure/deployment-setup.md) | Deployment guide |
| Coding Rules | [docs/development/vibe-coding-rules.md](docs/development/vibe-coding-rules.md) | Development standards |
| UI/UX Specs | [docs/ui-ux/specifications.md](docs/ui-ux/specifications.md) | Interface specifications |
| User Journeys | [docs/user-journeys/](docs/user-journeys/) | User flow documentation |
| Agent Continuity | [docs/AGENT_CONTINUITY.md](docs/AGENT_CONTINUITY.md) | Knowledge transfer for agents |

---

## Tech Stack

- **Backend**: Django 5, Django Ninja, Django Channels
- **Database**: PostgreSQL 15, Redis 7
- **Frontend**: Lit 3, TypeScript, Tailwind CSS
- **Payments**: PayPal SDK
- **Infrastructure**: Kubernetes (Minikube + Tilt), Docker Compose, AWS
- **Testing**: Pytest, Playwright
- **Observability**: Prometheus, Grafana
- **Streaming**: Apache Kafka, Apache Flink
- **Orchestration**: Apache Airflow

## Docker Compose Architecture

The `infrastructure/docker/` directory provides a complete single-file Docker Compose setup:

**Services (17 total)**:
- **Core**: PostgreSQL, Redis
- **Streaming**: Kafka, Zookeeper
- **Analytics**: ClickHouse, Prometheus, Grafana
- **Backend**: Django API, WebSocket Gateway
- **Frontend**: Lit UI
- **Infrastructure**: Vault, SpiceDB
- **Orchestration**: Airflow (webserver + scheduler), Flink (jobmanager + taskmanager)
- **Proxy**: Nginx (port 10355)

**Memory Usage**: ~8GB (within 10GB constraint)

**Quick Start**:
```bash
cd docker
./start.sh
```

See [infrastructure/docker/README.md](infrastructure/docker/README.md) for complete documentation.

---

## Security

- **Authentication**: JWT (RS256), session-based for admin
- **Password Hashing**: Argon2id
- **API Security**: Rate limiting, CSRF protection
- **Secrets Management**: Environment variables, Vault (planned)

---

## License

Proprietary - SOMATECH

---

*Built with Django 5 + Django Ninja*
*No mocks. No fake data. Only real APIs and real results.*



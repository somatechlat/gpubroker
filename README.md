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
├── frontend/                    # Next.js 14 frontend (legacy)
├── infrastructure/              # Vault, scripts
└── database/                    # PostgreSQL init scripts
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (for frontend)

### Development Setup

```bash
# 1. Clone and setup
git clone https://github.com/somatechlat/gpubroker.git
cd gpubroker

# 2. Configure environment
cp .env.example .env
# Edit .env with your secrets

# 3. Start the stack
docker-compose -f docker-compose.dev.yml up --build

# 4. Run migrations
docker-compose exec django python manage.py migrate
```

### Access Points

| Service | URL | Description |
|---------|-----|-------------|
| Landing Page | http://localhost:28080/ | Public landing page |
| Admin Dashboard | http://localhost:28080/admin/ | Admin login & dashboard |
| API Docs | http://localhost:28080/api/v2/docs | OpenAPI documentation |
| Enrollment | http://localhost:28080/checkout | Subscription checkout |

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
- **Frontend**: Next.js 14, TypeScript, Tailwind CSS
- **Payments**: PayPal SDK
- **Infrastructure**: Docker, AWS
- **Testing**: Pytest, Playwright
- **Observability**: Prometheus, Grafana

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

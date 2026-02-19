# GPUBROKER - COMPREHENSIVE ONBOARDING GUIDE

**For AI Agents & Human Developers**  
**Last Updated**: January 8, 2026  
**Project Status**: Django 5 Migration + Security Hardening Complete

---

## 🎯 PROJECT OVERVIEW

### What is GPUBROKER?
A unified AI-powered GPU marketplace and control tower SaaS that:
- Aggregates GPU offers from multiple providers with real-time pricing
- Provides AI-powered recommendations and intelligent cost optimization
- Manages GPU deployment, monitoring, and billing in one platform
- Uses Django 5 + Django Ninja as unified backend framework

### Core Architecture
```
Frontend (Lit 3 + Vite) ←→ Django API (Ninja) ←→ PostgreSQL/Redis
         ↓
   Infrastructure (Vault, Kafka, ClickHouse, Prometheus)
         ↓
   GPU Agents (Pod Management)
```

---

## 🏗️ PROJECT STRUCTURE

### Root Directory
```
gpubroker/
├── backend/gpubroker/          # Django backend monolith
│   ├── config/                 # API wiring, settings, URLs
│   ├── gpubrokeradmin/         # Admin dashboard + enrollment
│   ├── gpubrokerlandingpage/   # Marketing site
│   ├── gpubrokerpod/           # GPU Agent POD management
│   ├── shared/                 # Utilities, middleware
│   ├── tests/                  # E2E and unit tests
│   └── TMP/agent-zero/         # AI agent integration (gitignored)
├── frontend/                   # Lit 3 web components UI
├── infrastructure/             # All infrastructure configs
│   ├── docker/                 # Docker Compose setup
│   ├── k8s/                    # Kubernetes manifests
│   ├── aws/                    # AWS infrastructure
│   ├── vault/                  # Vault configuration
│   └── ... (postgres, redis, etc.)
├── docs/                       # Documentation
│   ├── srs/                    # Software Requirements Specs
│   ├── user-journeys/          # User journey flows
│   ├── development/            # Coding rules, violations log
│   ├── infrastructure/         # Deployment, observability
│   └── ui-ux/                  # UI/UX specifications
├── dags/                       # Airflow DAGs (billing)
├── flink_jobs/                 # Flink streaming jobs
└── scripts/                    # Deployment scripts
```

---

## 🔧 TECH STACK

### Backend
- **Framework**: Django 5 + Django Ninja
- **Database**: PostgreSQL 15 (Django ORM)
- **Cache**: Redis 7 (sessions, caching, price feeds)
- **WebSocket**: Django Channels
- **API**: Django Ninja REST API (`/api/v2/`)

### Frontend
- **Framework**: Lit 3 (Web Components)
- **Build**: Vite
- **Styling**: Tailwind CSS tokens
- **Entry**: `frontend/index.html`

### Infrastructure
- **Container**: Docker + Docker Compose
- **Orchestration**: Kubernetes (Tilt for dev)
- **Secrets**: HashiCorp Vault
- **Messaging**: Apache Kafka + Zookeeper
- **Analytics**: ClickHouse 23.8
- **Monitoring**: Prometheus + Grafana
- **Auth**: SpiceDB (ReBAC)
- **Workflow**: Apache Airflow
- **Streaming**: Apache Flink

---

## 🚀 QUICK START

### Option 1: Docker Compose (Fastest)
```bash
# 1. Clone repository
git clone https://github.com/somatechlat/gpubroker.git
cd gpubroker

# 2. Navigate to Docker setup
cd infrastructure/docker

# 3. Start everything
./start.sh
```

**Access Points**:
- Main: http://localhost:10355
- API: http://localhost:10355/api/v2
- Airflow: http://localhost:10355/airflow
- Grafana: http://localhost:10355/grafana

### Option 2: Kubernetes + Tilt (Production-like)
```bash
# 1. Setup Minikube
minikube start -p gpubroker --driver=vfkit --memory=8g --cpus=4

# 2. Configure environment
cp .env.example .env
# Edit .env with your secrets

# 3. Start with Tilt
tilt up
```

---

## 🔐 CONFIGURATION SYSTEM

### Centralized Configuration (Django Pattern)
**Location**: `backend/gpubroker/gpubroker/settings/`

```
settings/
├── base.py              # Main Django settings
├── centralized.py       # Centralized config system
├── development.py       # Development overrides
├── staging.py          # Staging overrides
└── production.py       # Production overrides
```

### Configuration Hierarchy
1. **System Variables**: Environment variables (django-environ)
2. **Application Secrets**: HashiCorp Vault
3. **Centralized Access**: Django settings as single source of truth

### Usage Pattern
```python
# In Django settings
from .centralized import SECURITY_CONFIG, DATABASE_CONFIG, PAYPAL_CONFIG

SECRET_KEY = SECURITY_CONFIG.secret_key
DATABASE_URL = DATABASE_CONFIG.url
PAYPAL_CLIENT_ID = PAYPAL_CONFIG.client_id_sandbox
```

```python
# In application code
from django.conf import settings

paypal_config = settings.PAYPAL_CONFIG
client_id = paypal_config.client_id_sandbox
```

### Environment Variables
**System Variables** (in `.env` file):
- `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`
- `DATABASE_URL`, `REDIS_URL`
- `VAULT_ADDR`, `VAULT_TOKEN`

**Application Secrets** (in Vault):
- PayPal credentials
- JWT keys
- Database passwords
- API keys

---

## 📊 DATA FLOW

### User Registration Flow
```
1. User visits landing page → enrollment modal
2. OAuth provider authentication
3. User data → PostgreSQL (auth_app.User)
4. JWT token generation (RS256)
5. Session management in Redis
```

### GPU Deployment Flow
```
1. User requests GPU → API endpoint
2. Price aggregation → ClickHouse
3. AI recommendation → Agent Zero
4. Deployment → Kubernetes pod
5. Monitoring → Prometheus + Grafana
6. Billing → Airflow DAGs
```

### Payment Flow
```
1. User selects GPU → PayPal checkout
2. Payment verification → PayPal API
3. Webhook processing → Django endpoint
4. Subscription activation → PostgreSQL
5. Deployment trigger → Kubernetes
```

---

## 🔍 KEY ENTRY POINTS

### API Endpoints
- **Main API**: `backend/gpubroker/config/api/__init__.py`
- **Legacy API**: `backend/gpubroker/gpubroker/api/v2/__init__.py`
- **Admin API**: `backend/gpubroker/gpubrokeradmin/api/router.py`

### Application Modules
- **Auth**: `backend/gpubroker/apps/auth_app/`
- **Providers**: `backend/gpubroker/apps/providers/`
- **KPI**: `backend/gpubroker/apps/kpi/`
- **Math Core**: `backend/gpubroker/apps/math_core/`
- **AI Assistant**: `backend/gpubroker/apps/ai_assistant/`
- **WebSocket**: `backend/gpubroker/apps/websocket_gateway/`

### Infrastructure Services
- **Docker**: `infrastructure/docker/docker-compose.yml`
- **Kubernetes**: `infrastructure/k8s/local-prod.yaml`
- **Airflow**: `dags/billing_dag.py`
- **Flink**: `flink_jobs/price_aggregator.py`

---

## 🧪 TESTING

### Test Structure
```
backend/gpubroker/tests/
├── e2e/                      # Playwright E2E tests
│   ├── test_paypal_sandbox.py
│   ├── test_enrollment_flow.py
│   └── test_complete_e2e_flow.py
├── unit/                     # Unit tests
│   └── test_paypal_service.py
└── integration_test.py       # Live API integration test
```

### Running Tests
```bash
# E2E tests
cd backend/gpubroker
pytest tests/e2e/

# Unit tests
pytest tests/unit/

# Integration test (hits live APIs)
python integration_test.py
```

### Test Configuration
- All tests use environment variables (no hardcoded credentials)
- PayPal sandbox credentials from `PAYPAL_CLIENT_ID_SANDBOX` / `PAYPAL_CLIENT_SECRET_SANDBOX`
- JWT keys from `JWT_PRIVATE_KEY` / `JWT_PUBLIC_KEY`

---

## 📚 DOCUMENTATION

### Essential Reading (In Order)
1. **SRS**: `docs/srs/GPUBroker_SRS.md` - System requirements
2. **Journeys**: `docs/user-journeys/` - User flows
3. **Environment**: `docs/ENVIRONMENT-VARIABLES.md` - All variables
4. **Vibe Rules**: `rules.md` + `docs/development/vibe-coding-rules.md`
5. **Infrastructure**: `docs/infrastructure/deployment-setup.md`

### API Documentation
- **OpenAPI**: `docs/openapi.yaml`
- **Local**: http://localhost:10355/api/v2/docs (when running)

---

## ⚠️ CRITICAL CONSTRAINTS

### Must Follow
1. **Django 5 + Django Ninja only** - No other frameworks
2. **Django ORM only** - No raw SQL queries
3. **Lit 3 Web Components** - No React/Vue/Angular
4. **Centralized Configuration** - All config through Django settings
5. **No Hardcoded Credentials** - Everything in Vault or environment variables
6. **Port 10355** - Main ingress point for all services

### Vibe Coding Rules
- **No Guessing**: Read SRS and user journeys first
- **Real Code Only**: No placeholders, no stubs
- **Complete Context**: Understand full architecture before changes
- **Documentation First**: Document before implementing
- **Production Grade**: Proper error handling, health checks, logging

---

## 🔧 COMMON TASKS

### Adding New API Endpoint
1. Read SRS and user journeys
2. Add endpoint in appropriate router
3. Use Django Ninja decorators
4. Add tests in `tests/e2e/`
5. Update OpenAPI docs
6. Test with Docker Compose

### Updating Configuration
1. Add to `centralized.py` dataclasses
2. Update `base.py` settings
3. Add to Vault (if secret)
4. Update `.env.example`
5. Update documentation

### Modifying Frontend
1. Update Lit components in `frontend/src/`
2. Use Vite for building
3. Test with running backend
4. Check port 10355 integration

---

## 🚨 KNOWN ISSUES & RISKS

### Needs Alignment
- **Payment Capture**: Currently mixes internal payment with deployment triggers
  - Files: `gpubrokeradmin/services/payments/paypal.py`, `gpubrokeradmin/apps/subscriptions/services.py`
  - Solution: External payments only, platform handles configuration/ingestion

### Missing Files
- **Core Models**: `apps/core/signals.py` references Provider but no `models.py`
  - Impact: May cause import errors
  - Action: Add models or fix signals

### Integration Issues
- **Integration Test**: Has stray text before shebang
  - File: `backend/gpubroker/integration_test.py`
  - Action: Remove stray text

### External Dependencies
- **Geo Detection**: Calls external IP APIs
  - File: `gpubrokeradmin/services/geo.py`
  - Risk: Production allowlist/timeouts needed

### State Management
- **PayPal Transactions**: Stored in memory (not persistent)
  - File: `gpubrokeradmin/services/payments/paypal.py`
  - Risk: Data loss on restart

---

## 🎯 SUCCESS CRITERIA

### For Agents
- ✅ Understand complete architecture before making changes
- ✅ Follow Django patterns and vibe coding rules
- ✅ No hardcoded credentials anywhere
- ✅ All configuration centralized through Django settings
- ✅ Tests pass before committing
- ✅ Documentation updated

### For Humans
- ✅ Can start full stack with single command
- ✅ All services accessible via port 10355
- ✅ Configuration clear and centralized
- ✅ Development workflow documented
- ✅ Production deployment path clear

---

## 📞 SUPPORT & ESCALATION

### When Stuck
1. **Read the docs**: Start with SRS and user journeys
2. **Check AGENTS.md**: This file for project context
3. **Run tests**: See what's actually working
4. **Check logs**: Docker Compose logs for errors
5. **Review architecture**: Understand before coding

### Key Files to Check
- **Configuration**: `backend/gpubroker/gpubroker/settings/centralized.py`
- **API**: `backend/gpubroker/config/api/__init__.py`
- **Tests**: `backend/gpubroker/tests/e2e/`
- **Docker**: `infrastructure/docker/docker-compose.yml`

---

## 🔄 CURRENT STATE

### ✅ Completed
- Django 5 migration foundation
- Centralized configuration system
- Docker folder relocation
- Security hardening (credentials removed)
- AGENTS.md updated with comprehensive guide

### 🔄 In Progress
- Complete centralized configuration rollout
- Application code migration to new config system
- Environment-specific configuration files
- Deployment scripts and testing

### 📋 Next Steps
1. Update all application code to use centralized config
2. Create environment-specific settings (dev/staging/prod)
3. Complete Vault integration testing
4. Update all documentation
5. Production deployment preparation

---

**Remember**: This is a living document. Update AGENTS.md whenever you make significant changes to the project architecture or patterns.**

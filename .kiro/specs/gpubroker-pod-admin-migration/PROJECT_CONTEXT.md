# GPUBROKER Project Context Documentation

## Overview

GPUBROKER is a GPU brokerage SaaS platform built with Django 5 + Django Ninja. This document provides complete context for any agent working on this project.

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GPUBROKER PLATFORM                               │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    GPUBROKERADMIN (Control Plane)                │    │
│  │  - Admin Dashboard (Django Templates)                            │    │
│  │  - Subscription Management                                       │    │
│  │  - Pod Lifecycle Management                                      │    │
│  │  - Payment Processing (PayPal)                                   │    │
│  │  - AWS ECS Fargate Deployment                                    │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │                    GPUBROKERPOD (Data Plane)                     │    │
│  │  ┌─────────────────────┐  ┌─────────────────────┐               │    │
│  │  │   GPUBROKERAPP      │  │   GPUBROKERAGENT    │               │    │
│  │  │   (User-facing)     │  │   (Agentic Layer)   │               │    │
│  │  │   - Auth            │  │   - Agent Core      │               │    │
│  │  │   - Providers       │  │   - Decisions       │               │    │
│  │  │   - KPI             │  │   - Budgets         │               │    │
│  │  │   - Math Core       │  │                     │               │    │
│  │  │   - AI Assistant    │  │   BLACK BOX:        │               │    │
│  │  │   - WebSocket GW    │  │   Agent Zero        │               │    │
│  │  └─────────────────────┘  └─────────────────────┘               │    │
│  └─────────────────────────────────────────────────────────────────┘    │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend
- **Framework**: Django 5 + Django Ninja (NO FastAPI)
- **ORM**: Django ORM (NO SQLAlchemy)
- **Realtime**: Django Channels (WebSocket/SSE)
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Analytics**: ClickHouse
- **Message Queue**: Kafka

### Frontend
- **Framework**: Next.js (React - legacy, migrating to Lit 3.x)
- **UI Components**: Lit 3.x Web Components (target)

### Infrastructure
- **Container Orchestration**: AWS ECS Fargate
- **Secrets**: HashiCorp Vault
- **Monitoring**: Prometheus + Grafana
- **Logging**: JSON structured logging

## AWS Configuration

### ECS Fargate Settings
```python
# backend/gpubroker/gpubrokeradmin/services/deploy.py
AWS_REGION = "us-east-1"
ECS_CLUSTER = "gpubroker-pods"
ECS_TASK_DEFINITION = "gpubroker-agent-pod"
SUBNETS = ["subnet-04cc7be08489369a0", "subnet-01aa30d4017fc910b"]
SECURITY_GROUP = "sg-0661f12cee535a607"
CONTAINER_NAME = "agent-zero"
```

### Pod Deployment Configuration
- **vCPU**: 0.25 (Fargate)
- **Memory**: 0.5 GB
- **Launch Type**: FARGATE
- **Public IP**: ENABLED
- **Pod URL Format**: `https://{pod_id}.gpubroker.live`

### AWS Services Used
1. **ECS Fargate** - Pod container orchestration
2. **SES** - Email notifications
3. **SNS** - SMS verification (Ecuador +593)
4. **CloudWatch** - Metrics and logging
5. **S3** - Knowledge base storage (SRI data)
6. **DynamoDB** - (Legacy, migrated to PostgreSQL)

### Environment Variables (AWS)
```bash
AWS_REGION=us-east-1
AWS_ACCOUNT_ID=<your-account-id>
ECS_CLUSTER=gpubroker-pods
ECS_TASK_DEFINITION=gpubroker-agent-pod
ECS_SUBNETS=subnet-xxx,subnet-yyy
ECS_SECURITY_GROUP=sg-xxx
SES_FROM_EMAIL=noreply@gpubroker.live
VENDOR_EMAIL=admin@gpubroker.live
```

## Agent Zero Integration (BLACK BOX)

### CRITICAL: Agent Zero is READ-ONLY
- Location: `backend/gpubroker/TMP/agent-zero/` (reference only)
- **DO NOT MODIFY** Agent Zero code
- We build GPUBROKER components that COMMUNICATE WITH Agent Zero
- Agent Zero runs AS-IS in ECS containers

### Agent Zero Architecture
```
Agent Zero (Black Box)
├── agents/           # Agent profiles (default, developer, researcher, hacker)
├── conf/             # Model provider configurations
├── instruments/      # Tools and capabilities
├── knowledge/        # Knowledge base
├── memory/           # Agent memory storage
├── prompts/          # System prompts
├── python/           # Core Python modules
│   ├── api/          # API endpoints
│   ├── extensions/   # Extensions
│   ├── helpers/      # Utility functions
│   └── tools/        # Agent tools
└── webui/            # Web interface
```

### GPUBROKER Agent Integration Layer
We build these Django components to integrate:
- `gpubrokerpod.gpubrokeragent.apps.agent_core` - Session management
- `gpubrokerpod.gpubrokeragent.apps.decisions` - Decision logging
- `gpubrokerpod.gpubrokeragent.apps.budgets` - Token/cost budgets

## Directory Structure

```
backend/gpubroker/
├── config/                    # Django configuration
│   ├── settings/
│   │   ├── base.py           # Base settings
│   │   ├── sandbox.py        # Sandbox environment
│   │   ├── production.py     # Production environment
│   │   └── test.py           # Test environment
│   ├── urls.py               # URL routing
│   ├── asgi.py               # ASGI config (Channels)
│   └── api/
│       └── __init__.py       # Django Ninja API setup
│
├── gpubrokeradmin/            # CONTROL PLANE
│   ├── apps/
│   │   ├── auth/             # Admin authentication
│   │   │   ├── models.py     # AdminUser, AdminSession, AdminAuditLog
│   │   │   └── services.py   # AdminAuthService (JWT)
│   │   ├── subscriptions/    # Subscription management
│   │   │   ├── models.py     # Subscription, Payment, PodMetrics
│   │   │   └── services.py   # SubscriptionService
│   │   ├── pod_management/   # Pod lifecycle
│   │   ├── access_control/   # RBAC
│   │   ├── notifications/    # Alerts
│   │   └── monitoring/       # Metrics
│   ├── services/
│   │   ├── deploy.py         # AWS ECS deployment
│   │   ├── email.py          # AWS SES emails
│   │   └── payments/         # Payment integrations
│   │       └── paypal.py     # PayPal REST API v2
│   ├── api/
│   │   └── router.py         # Django Ninja API router
│   ├── templates/            # Django templates
│   │   ├── admin/            # Admin dashboard
│   │   ├── enrollment/       # Checkout, activate
│   │   └── deployment/       # Provisioning, ready
│   ├── static/               # CSS, JS
│   ├── views.py              # Template views
│   └── urls.py               # URL patterns
│
├── gpubrokerpod/              # DATA PLANE
│   ├── gpubrokerapp/         # User-facing apps
│   │   └── apps/
│   │       ├── auth_app/     # User authentication
│   │       ├── providers/    # GPU providers
│   │       ├── kpi/          # KPI tracking
│   │       ├── math_core/    # Calculations
│   │       ├── ai_assistant/ # AI features
│   │       └── websocket_gateway/
│   └── gpubrokeragent/       # Agent integration
│       └── apps/
│           ├── agent_core/   # Agent sessions
│           ├── decisions/    # Decision logging
│           └── budgets/      # Token budgets
│
├── shared/                    # Shared utilities
│   └── middleware/
│
└── TMP/                       # REFERENCE ONLY - DO NOT DEPLOY
    ├── agent-zero/           # Agent Zero source (BLACK BOX)
    └── SercopPODAdminREFERECENE/  # Flask reference (being migrated)
```

## Database Models

### GPUBROKERADMIN Models

#### AdminUser
```python
class AdminUser(models.Model):
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    name = models.CharField(max_length=100)
    role = models.CharField(choices=['super_admin', 'admin', 'viewer'])
    is_active = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True)
    last_login_ip = models.GenericIPAddressField(null=True)
```

#### Subscription
```python
class Subscription(models.Model):
    subscription_id = models.CharField(unique=True)  # sub_xxx
    api_key = models.CharField(unique=True)          # sk_live_xxx
    api_key_hash = models.CharField()
    email = models.EmailField()
    name = models.CharField()
    ruc = models.CharField()                         # Ecuador tax ID
    plan = models.CharField(choices=['trial', 'basic', 'pro', 'corp', 'enterprise'])
    status = models.CharField(choices=[
        'pending_activation', 'provisioning', 'running', 
        'active', 'suspended', 'cancelled', 'failed', 'destroyed'
    ])
    pod_id = models.CharField()                      # pod-xxx
    pod_url = models.URLField()
    task_arn = models.CharField()                    # ECS task ARN
    token_limit = models.IntegerField()
    tokens_used = models.IntegerField()
    amount_usd = models.DecimalField()
    payment_provider = models.CharField()            # paypal
    transaction_id = models.CharField()
    order_id = models.CharField()
    expires_at = models.DateTimeField()
```

## API Endpoints

### Public Endpoints (No Auth)
```
POST /api/v2/admin/public/admin/login     # Admin login
POST /api/v2/admin/public/subscription/create
POST /api/v2/admin/public/subscription/activate
GET  /api/v2/admin/public/pod/status?key=xxx
POST /api/v2/admin/public/validate/ruc
POST /api/v2/admin/public/validate/cedula
POST /api/v2/admin/public/validate/identity
GET  /api/v2/admin/public/health
```

### Admin Endpoints (JWT Required)
```
GET  /api/v2/admin/dashboard
GET  /api/v2/admin/pods
POST /api/v2/admin/pod/start
POST /api/v2/admin/pod/destroy
GET  /api/v2/admin/pod/{pod_id}/metrics
GET  /api/v2/admin/costs
GET  /api/v2/admin/customer/{email}
GET  /api/v2/admin/transaction/{tx_id}
POST /api/v2/admin/resend-receipt
```

## Payment Integration

### PayPal (Primary)
- **Mode**: Sandbox / Live (via PAYPAL_MODE env)
- **API**: REST API v2 (Orders)
- **Flow**:
  1. Create order → Get approval URL
  2. User approves on PayPal
  3. Capture order → Get transaction ID
  4. Create subscription → Deploy pod

### Environment Variables
```bash
PAYPAL_CLIENT_ID=xxx
PAYPAL_CLIENT_SECRET=xxx
PAYPAL_MODE=sandbox  # or 'live'
```

## Subscription Plans

| Plan       | Price USD | Tokens  |
|------------|-----------|---------|
| trial      | $0        | 1,000   |
| basic      | $20       | 5,000   |
| pro        | $40       | 10,000  |
| corp       | $99       | 50,000  |
| enterprise | $299      | 200,000 |

## Ecuador-Specific Features

### RUC Validation
- 13 digits
- Province code (01-24, 30 for foreigners)
- Third digit: entity type (0-5 natural, 6 public, 9 juridical)
- Must end in "001"

### Cedula Validation
- 10 digits
- Province code (01-24)
- Luhn-like checksum algorithm

### SMS Verification
- AWS SNS
- Ecuador only (+593)
- 6-digit OTP
- 10 minute expiry
- Rate limit: 3/hour

## Docker Services

### Development (docker-compose.dev.yml)
```yaml
services:
  - vault (HashiCorp Vault - secrets)
  - postgres (PostgreSQL 15)
  - redis (Redis 7)
  - kafka (Confluent Kafka)
  - zookeeper
  - django (Django 5 backend)
  - clickhouse (Analytics)
  - nginx (Reverse proxy)
  - frontend (Next.js)
  - prometheus (Metrics)
  - grafana (Dashboards)
  - storybook (Component dev)
```

### Port Assignments
```
28001 - PostgreSQL
28002 - ClickHouse HTTP
28003 - ClickHouse Native
28004 - Redis
28005 - Vault
28007 - Kafka
28008 - Zookeeper
28030 - Frontend
28031 - Prometheus
28032 - Grafana
28033 - Storybook
28080 - Django
```

## Vibe Coding Rules

### CRITICAL RULES
1. **NO mocks, NO placeholders, NO fake data**
2. **Check first, code second** - Read existing code before writing
3. **Real implementations only** - Production-grade code
4. **Django 5 + Django Ninja ONLY** - No FastAPI
5. **Django ORM ONLY** - No SQLAlchemy
6. **Agent Zero is BLACK BOX** - Do not modify

### Framework Policies
- API: Django Ninja `/api/v2/`
- Realtime: Django Channels
- UI: Lit 3.x Web Components (target)
- Vectors: Milvus (no Qdrant)
- Secrets: HashiCorp Vault

## Files to Read for Context

When starting work on this project, read these files:
1. `backend/gpubroker/config/settings/base.py` - Django settings
2. `backend/gpubroker/gpubrokeradmin/api/router.py` - API endpoints
3. `backend/gpubroker/gpubrokeradmin/apps/subscriptions/services.py` - Business logic
4. `backend/gpubroker/gpubrokeradmin/services/deploy.py` - AWS ECS deployment
5. `.kiro/specs/gpubroker-pod-saas/requirements.md` - Platform requirements
6. `vibe_coding_rules.md` - Coding standards

## Migration Status

### Completed
- [x] Admin authentication (Django)
- [x] Subscription management (Django ORM)
- [x] Pod deployment service (AWS ECS)
- [x] Email service (AWS SES)
- [x] API router (Django Ninja)
- [x] Basic templates (login, checkout, activate, provisioning, ready)

### In Progress
- [ ] Admin dashboard template (index.html)
- [ ] Billing template
- [ ] Customers template
- [ ] Costs template
- [ ] PayPal payment service
- [ ] Django settings registration
- [ ] URL routing integration

### Pending
- [ ] SMS verification service
- [ ] RUC/Cedula validation service
- [ ] Admin JS (admin.js)
- [ ] Delete TMP folder after migration

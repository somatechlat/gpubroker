# GPUBROKER Agent Continuity Document

This document provides essential context for AI agents and developers working on the GPUBROKER project. It captures the current state, completed work, and critical knowledge needed to continue development.

---

## Project Overview

GPUBROKER is an AI-Powered GPU Marketplace & Control Tower SaaS platform deployed on AWS. The project consists of:

1. **GPUBROKER Landing Page** - Public marketing site at gpubroker.site
2. **GPUBROKER Admin** - Admin dashboard for managing subscriptions, customers, billing
3. **GPUBROKER POD** - GPU Agent deployment and management system (deployed to AWS ECS Fargate)
4. **Provider API Gateway** - Aggregates GPU offers from multiple providers

---

## Critical Contact Information

### Notification Channels
- **Email**: ai@somatech.dev (AWS SES activated)
- **SMS/WhatsApp**: +593997202547 (Ecuador)
- **Support Email**: soporte@gpubroker.site

### Organization
- **Company**: SOMATECH DEV
- **Website**: https://www.somatech.dev
- **Jurisdiction**: República del Ecuador, Tribunales de Quito

---

## AWS Production Architecture

### Services Used
- **ECS Fargate**: POD deployment (pay-per-use containers)
- **RDS PostgreSQL**: Production database
- **ElastiCache Redis**: Production cache
- **ALB**: Application Load Balancer
- **CloudWatch**: Monitoring and logging
- **Secrets Manager**: Credential storage
- **S3**: Static assets and backups
- **CloudFront**: CDN for static content
- **SES**: Email notifications (ai@somatech.dev)
- **SNS**: SMS notifications (+593997202547)

### Local Development (Minikube + Tilt)
Local development runs in an isolated Minikube profile (vfkit) orchestrated by Tilt. Production uses AWS managed services.

Default local resource limits (8GB total):
- Postgres: 512MB
- Redis: 192MB
- Kafka: 768MB
- Zookeeper: 384MB
- Django: 1GB
- ClickHouse: 1GB
- Nginx: 128MB
- Frontend: 1GB
- Prometheus: 512MB
- Grafana: 256MB
- Vault: 256MB

---

## Current Architecture

### Backend Stack
- **Framework**: Django 5 + Django Ninja (REST API)
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **WebSocket**: Django Channels
- **Server**: Uvicorn/Daphne (ASGI)
- **Payments**: PayPal (sandbox and production)

### Key Django Apps
```
backend/gpubroker/
├── config/                  # Settings, URLs, ASGI config
├── gpubrokeradmin/          # Admin dashboard & enrollment
│   ├── apps/
│   │   ├── auth/            # Admin authentication
│   │   ├── subscriptions/   # Subscription management
│   │   ├── pod_management/  # POD lifecycle
│   │   ├── access_control/  # RBAC
│   │   ├── monitoring/      # System monitoring
│   │   └── notifications/   # Alert system
│   ├── api/                 # Django Ninja routers
│   ├── services/            # Business logic
│   │   ├── geo.py           # Geo-detection for country-specific validation
│   │   ├── payments/        # PayPal integration
│   │   ├── email.py         # Email notifications
│   │   └── deploy.py        # AWS ECS deployment
│   └── templates/           # HTML templates
├── gpubrokerlandingpage/    # Static landing page
└── gpubrokerpod/            # GPU Agent POD
    └── gpubrokeragent/      # Agent core, decisions, budgets
```

---

## Key Credentials (Development)

### Admin Dashboard
- **URL**: http://localhost:10355/admin/
- **Email**: admin@gpubroker.io
- **Password**: admin123

### PayPal Sandbox
- **Client ID**: [REDACTED - Use Vault or environment variables]
- **Client Secret**: [REDACTED - Use Vault or environment variables]
- **Mode**: sandbox
- **Test Buyer**: [REDACTED - Use PAYPAL_SANDBOX_EMAIL/PASSWORD env vars]

### Database (Development)
- **URL**: postgresql://gpubroker:gpubroker_dev_password@localhost:28001/gpubroker_dev
- **Redis**: redis://localhost:28004/0

---

## Enrollment Flow (Landing → POD Deployed)

### User Journey
1. **Landing Page** (gpubroker.site) → User clicks plan
2. **Checkout** (/checkout/?plan=pro) → Geo-detection determines country
3. **Ecuador Users**: Must validate RUC (13 digits) or Cédula (10 digits)
4. **Other Countries**: Standard email/name registration
5. **Payment** → PayPal integration
6. **Activation** (/activate) → Enter API key
7. **Provisioning** (/provisioning) → POD deploying to AWS ECS
8. **Ready** (/ready) → POD URL provided, user can start using

### Country-Specific Validation
- **Ecuador (EC)**: Requires RUC/Cédula validation
- **Other countries**: Standard registration (no tax ID required)
- Geo-detection via IP using free APIs (ipapi.co, ip-api.com, ipwho.is)
- Can force country via `GPUBROKER_FORCE_COUNTRY` setting

---

## API Endpoints

### Public Endpoints (No Auth)
```
GET  /api/v2/admin/public/health              # Health check
GET  /api/v2/admin/public/geo/detect          # Geo-detection for checkout
POST /api/v2/admin/public/admin/login         # Admin login
POST /api/v2/admin/public/subscription/create # Create subscription
POST /api/v2/admin/public/subscription/activate # Activate POD
GET  /api/v2/admin/public/pod/status          # Check deployment status
POST /api/v2/admin/public/validate/ruc        # Validate Ecuador RUC
POST /api/v2/admin/public/validate/cedula     # Validate Ecuador Cédula
POST /api/v2/admin/public/validate/identity   # Validate RUC or Cédula
POST /api/v2/admin/public/payment/paypal      # Create PayPal order
POST /api/v2/admin/public/payment/paypal/capture/{order_id} # Capture payment
GET  /api/v2/admin/public/payment/paypal/status # PayPal config status
```

### Protected Endpoints (Require Auth)
```
GET  /api/v2/admin/dashboard                  # Dashboard statistics
GET  /api/v2/admin/pods                       # List all pods
POST /api/v2/admin/pod/destroy                # Destroy pod
POST /api/v2/admin/pod/start                  # Start pod
GET  /api/v2/admin/pod/{pod_id}/metrics       # Pod metrics
GET  /api/v2/admin/costs                      # AWS costs
GET  /api/v2/admin/customers                  # List customers
GET  /api/v2/admin/customer/{email}           # Customer details
GET  /api/v2/admin/billing                    # List transactions
GET  /api/v2/admin/transaction/{tx_id}        # Transaction details
POST /api/v2/admin/resend-receipt             # Resend receipt email
```

---

## Template Locations

```
backend/gpubroker/gpubrokeradmin/templates/
├── admin/
│   ├── login.html       # Admin login page
│   ├── index.html       # Dashboard home
│   ├── billing.html     # Billing management
│   ├── customers.html   # Customer list
│   └── costs.html       # Cost analytics
├── enrollment/
│   ├── checkout.html    # Payment checkout (with geo-detection)
│   └── activate.html    # POD activation
└── deployment/
    ├── provisioning.html # Deployment progress
    └── ready.html        # Deployment complete
```

---

## Development Commands

### Start Minikube + Tilt (Dev Infrastructure)
```bash
minikube start -p gpubroker --driver=vfkit --container-runtime=containerd --disk=10g --memory=8g --cpus=4 --addons=ingress
kubectl config use-context gpubroker
tilt up
```

### Start Django Server
```bash
cd backend/gpubroker
python manage.py runserver 0.0.0.0:10355
```

### Run Tests
```bash
cd frontend
npx playwright test  # E2E tests (64 tests)
```

### Database
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

---

## Vibe Coding Rules (Summary)

1. **NO MOCKS** - Only real implementations, real APIs, real data
2. **CHECK FIRST** - Review existing code before writing new code
3. **NO UNNECESSARY FILES** - Modify existing files when possible
4. **REAL IMPLEMENTATIONS** - No placeholders, stubs, or TODOs
5. **DOCUMENTATION = TRUTH** - Read and cite real documentation
6. **COMPLETE CONTEXT** - Understand full data flow before changes
7. **REAL DATA ONLY** - No invented JSON structures or fake responses

### Framework Policies
- **API**: Django 5 + Django Ninja ONLY (no FastAPI)
- **Database**: Django ORM ONLY (no SQLAlchemy)
- **Realtime**: Django Channels for WebSocket
- **Testing**: Pytest + Playwright for E2E

---

## Completed Work

### GPUBROKER POD Admin Migration (Flask to Django 5)
**Status**: COMPLETE - All 13 tasks completed

### Geo-Detection for Country-Specific Validation
**Status**: COMPLETE
- Ecuador users must provide RUC/Cédula
- Other countries skip tax ID validation
- Geo-detection via IP with fallback

### Landing Page
**Status**: COMPLETE
- Responsive design with pricing section
- Legal pages (terms, privacy, cookies)
- Integration with enrollment flow

### POD SaaS Implementation (In Progress)
**Status**: IN PROGRESS - Tasks 1-15 completed

**Completed Tasks:**
1. ✅ POD Configuration System - SANDBOX/LIVE modes with CRUD
2. ✅ Agent Zero Integration (ADMIN ONLY) - Start/stop/pause/resume
3. ✅ AWS Serverless Infrastructure - CloudFormation template with:
   - VPC and Networking
   - API Gateway (REST + WebSocket)
   - Cognito User Pool
   - ECS Fargate with auto-scaling
   - Aurora Serverless v2
   - ElastiCache Redis
   - MSK Serverless (Kafka)
   - Secrets Manager
   - CloudWatch dashboards and alarms
4. ✅ Landing Page - Featured GPU pricing API with 60s cache
5. ✅ Plans & Pricing - Billing app with subscription plans
6. ✅ Registration Flow - Email verification, password reset, OAuth schemas
7. ✅ Payment Setup - Full Stripe integration:
   - SetupIntent for secure card storage
   - Subscription creation with Stripe
   - Invoice email via AWS SES
   - Sandbox mode with test keys
   - Payment failure handling with retry
8. ✅ Dashboard - User-facing dashboard:
   - Quick stats (active pods, spend, API calls)
   - Pod list with status
   - Billing summary
   - Activity log
   - Provider health status
   - Real-time WebSocket updates
9. ✅ Browse GPU/Services - GPU browsing with filtering, sorting, TOPSIS ranking
10. ✅ Configure Pod - Pod configuration with:
    - GPU selection (type, model, count)
    - Provider selection (manual or auto-select)
    - Resource configuration (vCPUs, RAM, storage)
    - Cost estimation (per hour/day/month)
    - Validation against provider limits
    - Draft saving before deployment

**New Apps Created:**
- `gpubrokerpod.gpubrokerapp.apps.pod_config` - POD configuration management
- `gpubrokerpod.gpubrokerapp.apps.billing` - Subscription and billing
- `gpubrokerpod.gpubrokerapp.apps.dashboard` - User dashboard
- `gpubrokerpod.gpubrokerapp.apps.deployment` - Pod deployment and lifecycle

**New API Endpoints:**
- `/api/v2/config/pods/` - POD configuration CRUD
- `/api/v2/agent/` - Agent Zero control (ADMIN ONLY)
- `/api/v2/billing/plans` - Subscription plans
- `/api/v2/billing/subscription` - User subscription
- `/api/v2/billing/setup-intent` - Stripe SetupIntent
- `/api/v2/billing/webhook` - Stripe webhook handler
- `/api/v2/providers/featured` - Featured GPU offers
- `/api/v2/providers/browse` - Browse GPU offers with filtering
- `/api/v2/dashboard/` - Dashboard data
- `/api/v2/dashboard/pods` - User pods
- `/api/v2/dashboard/providers/health` - Provider health
- `/api/v2/deployment/configs` - Pod deployment configuration CRUD
- `/api/v2/deployment/estimate` - Cost estimation
- `/api/v2/deployment/validate` - Configuration validation
- `/api/v2/deployment/deploy` - Deploy a configuration
- `/api/v2/deployment/activate/{id}` - Activate a pod
- `/api/v2/deployment/pods/{id}/action` - Pod lifecycle actions
- `/api/v2/deployment/limits` - Provider limits

**WebSocket Endpoints:**
- `/ws/` - Price updates
- `/ws/notifications/` - User notifications
- `/ws/dashboard/` - Dashboard real-time updates
- `/ws/gpu-availability/` - GPU availability updates

**Remaining Tasks (16-28):**
- Deployment flow
- Activation flow
- Admin Dashboards
- Metrics & Monitoring
- Provider Integration
- Billing & Invoicing
- Security & Authentication
- Real-Time Updates

---

## Troubleshooting

### Common Issues

1. **Geo endpoint 404**
   - Correct URL: `/api/v2/admin/public/geo/detect`
   - NOT `/api/v2/geo/detect`

2. **Login fails with JSON.parse error**
   - Check login endpoint URL: `/api/v2/admin/public/admin/login`
   - Ensure response is JSON, not HTML

3. **PayPal sandbox not working**
   - Verify PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in .env
   - Ensure PAYPAL_MODE=sandbox

4. **Database connection errors**
   - Check DATABASE_URL in .env
   - Ensure PostgreSQL is running on port 28001

5. **Static files not loading**
   - Run `python manage.py collectstatic`
   - Check STATIC_URL and STATICFILES_DIRS settings

---

## Infrastructure Files

### Production-Grade Configs Created
- `infrastructure/prometheus/prometheus.yml` - Monitoring
- `infrastructure/grafana/datasources/datasources.yml` - Data sources
- `infrastructure/grafana/dashboards/dashboards.yml` - Dashboard provisioning
- `infrastructure/redis/redis.conf` - Redis optimization (128MB)
- `infrastructure/postgres/postgresql.conf` - PostgreSQL tuning (512MB)
- `infrastructure/vault/config/vault.hcl` - Secret management
- `infrastructure/nginx/nginx.conf` - Reverse proxy with rate limiting

---

*Last Updated: January 1, 2026*
*Document Version: 2.3*

# GPUBROKER Agent Continuity Document

This document provides essential context for AI agents and developers working on the GPUBROKER project. It captures the current state, completed work, and critical knowledge needed to continue development.

---

## Project Overview

GPUBROKER is an AI-Powered GPU Marketplace & Control Tower SaaS platform. The project consists of:

1. **GPUBROKER Landing Page** - Public marketing site
2. **GPUBROKER Admin** - Admin dashboard for managing subscriptions, customers, billing
3. **GPUBROKER POD** - GPU Agent deployment and management system
4. **Provider API Gateway** - Aggregates GPU offers from multiple providers

---

## Current Architecture

### Backend Stack
- **Framework**: Django 5 + Django Ninja (REST API)
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **WebSocket**: Django Channels
- **Server**: Uvicorn (ASGI)

### Key Django Apps
```
backend/gpubroker/
├── config/                  # Settings, URLs, ASGI config
├── gpubrokeradmin/          # Admin dashboard
│   ├── apps/
│   │   ├── auth/            # Admin authentication
│   │   ├── subscriptions/   # Subscription management
│   │   ├── pod_management/  # POD lifecycle
│   │   ├── access_control/  # RBAC
│   │   ├── monitoring/      # System monitoring
│   │   └── notifications/   # Alert system
│   ├── api/                 # Django Ninja routers
│   ├── services/            # Business logic (PayPal, email, deploy)
│   └── templates/           # HTML templates
├── gpubrokerlandingpage/    # Static landing page
└── gpubrokerpod/            # GPU Agent POD
    └── gpubrokeragent/      # Agent core, decisions, budgets
```

---

## Completed Work

### GPUBROKER POD Admin Migration (Flask to Django 5)
**Status**: COMPLETE

All 13 tasks completed:
1. Project structure and Django Ninja API setup
2. Auth models and services (AdminUser, AdminSession)
3. Subscription models (Plan, Subscription, Payment)
4. PayPal integration service
5. Email service for notifications
6. Deployment service for AWS provisioning
7. Admin dashboard views and templates
8. Enrollment flow (checkout, activate, provisioning, ready)
9. Admin pages (index, billing, customers, costs)
10. API routers registered in config
11. E2E tests with Playwright (64 tests passing)
12. Property tests for API responses
13. Unit tests for PayPal service

### Landing Page
**Status**: COMPLETE

- Responsive design with pricing section
- Legal pages (terms, privacy, cookies)
- Integration with enrollment flow

---

## API Endpoints

### Public Endpoints (No Auth)
```
POST /api/v2/admin/public/admin/login     # Admin login
GET  /api/v2/subscription/plans           # List subscription plans
POST /api/v2/subscription/checkout        # Create PayPal order
POST /api/v2/subscription/capture         # Capture PayPal payment
POST /api/v2/subscription/activate        # Activate POD deployment
GET  /api/v2/subscription/status/{key}    # Check deployment status
```

### Protected Endpoints (Require Auth)
```
GET  /api/v2/admin/dashboard/stats        # Dashboard statistics
GET  /api/v2/admin/customers              # List customers
GET  /api/v2/admin/billing                # Billing information
```

---

## Key Credentials (Development)

### Admin Dashboard
- **URL**: http://localhost:28080/admin/
- **Email**: admin@gpubroker.io
- **Password**: admin123

### PayPal Sandbox
- **Client ID**: AdN8KE5YsUHHCpwKs8cdmzCBOH0BTymz-YhJ2h6Yz9QNZVm8VH-n5JHKJd5bbA11tdwmkoW52IWThOGb
- **Mode**: sandbox
- **Test Buyer**: sb-zp64z48418674@personal.example.com / mdEcL1$w

---

## Database Models

### Auth Models
```python
class AdminUser:
    id: UUID
    email: str (unique)
    password_hash: str
    full_name: str
    role: str (admin/operator/viewer)
    is_active: bool
    created_at: datetime
    last_login: datetime

class AdminSession:
    id: UUID
    user: ForeignKey(AdminUser)
    token: str (unique)
    expires_at: datetime
    created_at: datetime
```

### Subscription Models
```python
class Plan:
    id: UUID
    name: str
    slug: str (unique)
    price_monthly: Decimal
    features: JSONField
    is_active: bool

class Subscription:
    id: UUID
    email: str
    plan: ForeignKey(Plan)
    api_key: str (unique)
    status: str (pending/active/cancelled/expired)
    pod_id: str (nullable)
    created_at: datetime
    activated_at: datetime (nullable)

class Payment:
    id: UUID
    subscription: ForeignKey(Subscription)
    paypal_order_id: str
    amount: Decimal
    currency: str
    status: str (pending/completed/failed/refunded)
    created_at: datetime
    completed_at: datetime (nullable)
```

---

## File Locations

### Templates
```
backend/gpubroker/gpubrokeradmin/templates/
├── admin/
│   ├── login.html       # Admin login page
│   ├── index.html       # Dashboard home
│   ├── billing.html     # Billing management
│   ├── customers.html   # Customer list
│   └── costs.html       # Cost analytics
├── enrollment/
│   ├── checkout.html    # Payment checkout
│   └── activate.html    # POD activation
└── deployment/
    ├── provisioning.html # Deployment progress
    └── ready.html        # Deployment complete
```

### Static Files
```
backend/gpubroker/gpubrokeradmin/static/gpubrokeradmin/
├── css/admin.css        # Admin styles
└── js/admin.js          # Admin JavaScript
```

### API Routers
```
backend/gpubroker/gpubrokeradmin/api/router.py  # All API endpoints
backend/gpubroker/config/api/__init__.py        # Router registration
```

---

## Development Commands

### Start Server
```bash
cd backend/gpubroker
./start_server.sh
# Or directly:
uvicorn config.asgi:application --host 0.0.0.0 --port 28080 --reload
```

### Run Tests
```bash
cd backend/gpubroker
pytest tests/e2e/ -v --headed  # E2E with browser
pytest tests/unit/ -v          # Unit tests
pytest -v                      # All tests
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

## Next Steps / Pending Work

### Journey 1: Landing to Deployment
- Complete ISO SRS documentation
- Implement remaining user journey screens
- Add email verification flow

### Provider API Gateway
- Implement additional provider adapters
- Real-time price aggregation
- WebSocket price broadcasts

### Admin Dashboard Enhancements
- Customer detail views
- Invoice generation
- Usage analytics charts

---

## Troubleshooting

### Common Issues

1. **Login fails with JSON.parse error**
   - Check login endpoint URL: `/api/v2/admin/public/admin/login`
   - Ensure response is JSON, not HTML

2. **PayPal sandbox not working**
   - Verify PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET in .env
   - Ensure PAYPAL_MODE=sandbox

3. **Database connection errors**
   - Check DATABASE_URL in .env
   - Ensure PostgreSQL is running on port 28001

4. **Static files not loading**
   - Run `python manage.py collectstatic`
   - Check STATIC_URL and STATICFILES_DIRS settings

---

## Contact

- **Project**: GPUBROKER
- **Organization**: SOMATECH
- **Repository**: https://github.com/somatechlat/gpubroker

---

*Last Updated: December 30, 2025*
*Document Version: 1.0*

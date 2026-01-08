# GPUBROKER Roadmap (Canonical)

Changelog:
- 2025-12-29 | codex | Add repo status snapshot to reconcile docs with repo state.

This file is the canonical source of truth for the GPUBROKER development roadmap. All roadmap updates should be made only here. It maps work into 8 two-week sprints (16 weeks total) and includes acceptance criteria, dependencies, and immediate next steps.

Document version: 2.0
Last updated: 2025-12-29

---

## Architecture

GPUBROKER uses Django 5 + Django Ninja as the unified backend framework:
- **Backend**: Django 5 monolith with Django Ninja API (`/api/v2/`)
- **Frontend**: Lit 3 with TypeScript
- **Database**: PostgreSQL with Django ORM
- **Cache**: Redis
- **WebSocket**: Django Channels
- **Observability**: Prometheus, Grafana, Loki, Tempo

## Repository Status Snapshot (Code-Verified)

- Backend: Django 5 monolith with apps for auth, providers, kpi, math_core, ai_assistant, websocket_gateway. Migrations exist for auth/providers/math_core; kpi/ai_assistant/websocket apps define no models.
- Providers: adapter registry lists 20 providers, but only `runpod` and `vastai` adapter modules exist in repo; missing adapters are skipped at runtime.
- Frontend: Lit 3 components and Vite entry are present; analytics page remains a placeholder; imports reference missing `src/lib` modules for provider API, AI client, and realtime WebSocket.
- Booking/Billing: no backend apps or endpoints in repo; frontend booking proxy expects an external booking service.
- Vault: client exists in `backend/shared/vault_client.py`, but provider API keys are currently read from user preferences or environment variables.

---

## High-level Plan (16 weeks — 8 sprints)

Each sprint is two weeks. Keep this file updated with progress, owners, and any changes to acceptance criteria.

### Sprint 1 — Project & Core Scaffold (Weeks 1–2) COMPLETE

Goal: Finalize repository structure, CI, dev environments; complete Lit 3 + Tailwind frontend scaffold and core backend auth service integration points.

Deliverables:
- Working dev environment (Minikube + Tilt) and frontend dev server instructions
- Frontend scaffold with Header, Layout, Login/Register pages, KPI shell, Provider Grid wired to Django API
- API contracts (OpenAPI) for Auth and Provider endpoints
- CI pipeline skeleton (lint + build)

Acceptance criteria:
- `frontend` starts locally (documented commands) and pages render with live Django API data
- CI runs lint checks and build steps on PRs
- Dev environment documented in `frontend/README.md` and repo README

---

### Sprint 2 — Marketplace Core UI (Weeks 3–4)

Goals, deliverables, acceptance criteria: see detailed sprint list below.

---

### Sprint 3 — Dashboard & Analytics Basics (Weeks 5–6)

---

### Sprint 4 — Booking Flow & Provider Integration Interface (Weeks 7–8)

---

### Sprint 5 — AI Assistant MVP & Project Wizard (Weeks 9–10)

---

### Sprint 6 — KPI Engine & Cost Prediction Integration (Weeks 11–12)

---

### Sprint 7 — Observability, Security & Performance (Weeks 13–14)

---

### Sprint 8 — Polish, Testing & Release Prep (Weeks 15–16)

---

## Ongoing Backlog

- Provider adapters (RunPod, Vast.ai, etc.) — continuous onboarding.
- Observability extensions, enterprise integrations, compliance certifications.

## How to Update This File

1. Edit this file directly for roadmap-level changes.
2. For task-level changes, create issues or update project board and reference the sprint header.
3. Tag the change with a short changelog entry at the top of this file (date + author + summary).

---

## Immediate Commands to Start Development (Developer Local)

Run these from the repo root (macOS zsh):

```bash
cd frontend
npm install
npm run dev
```

Local stack is standardized on Minikube + Tilt. See `docs/infrastructure/deployment-setup.md`.

---

## Rapid Development Roadmap

### Sprint Structure: 1-Week Sprints with Parallel Tracks
- **Sprint Duration**: 7 days
- **Parallel Tracks**: 6 simultaneous development streams
- **Daily Standups**: Track coordination and blockers
- **Sprint Reviews**: Demo working features every Friday

---

## Phase 1: Foundation (Weeks 1-2) COMPLETE

### Sprint 1A: Core Infrastructure COMPLETE
**Track Lead**: Backend Infrastructure
- [x] Django 5 project structure with Django Ninja API
- [x] Minikube + Tilt setup with hot reload
- [x] PostgreSQL + Redis containers
- [x] Basic health checks and service discovery
- [x] Nginx reverse proxy configuration

### Sprint 1B: Frontend Foundation
**Track Lead**: Frontend Architecture
- [ ] Lit 3 project with TypeScript
- [ ] Tailwind CSS + shadcn/ui component library
- [ ] Basic routing and layout structure
- [ ] Dark/light theme support
- [ ] Responsive grid system for provider cards

### Sprint 1C: Database Schema COMPLETE
**Track Lead**: Data Architecture
- [x] PostgreSQL schema for users, providers, offers, predictions
- [x] Django ORM models with migrations
- [x] Seed data for development
- [x] Connection pooling and optimization

### Sprint 1D: Security Foundation COMPLETE
**Track Lead**: Security Architecture
- [x] JWT token generation and validation (RS256)
- [x] Argon2id password hashing implementation
- [x] Basic RBAC with user roles
- [x] API key encryption in Vault
- [x] Rate limiting middleware

### Sprint 1E: Provider SDK Base COMPLETE
**Track Lead**: Integration Architecture
- [x] Abstract `ProviderAdapter` definition
- [x] Provider registry and adapter pattern
- [x] HTTP client with retry logic and circuit breakers
- [x] Error handling and standardization
- [x] RunPod and Vast.ai adapter implementations

### Sprint 1F: DevOps Pipeline COMPLETE
**Track Lead**: Platform Engineering
- [x] GitHub Actions CI/CD pipeline
- [x] Automated testing framework setup (pytest-django)
- [x] Code quality checks (ruff, pytest, eslint)
- [x] Container image building and optimization
- [x] Development environment automation

---

## Phase 2: Core Features (Weeks 3-4)

### Sprint 2A: Authentication System
- [ ] MFA implementation (TOTP + WebAuthn)
- [ ] Session management with refresh tokens
- [ ] SSO connectors (Google, Azure AD)
- [ ] User registration and verification flow

### Sprint 2B: Provider Marketplace
- [ ] Provider card component with real-time data
- [ ] Advanced filtering and sorting system
- [ ] Search functionality
- [ ] Pagination and infinite scroll
- [ ] Favorite providers and saved searches

### Sprint 2C: Cost Prediction Engine
- [ ] PyTorch model for cost prediction
- [ ] XGBoost integration for hybrid predictions
- [ ] Feature engineering pipeline
- [ ] Model training and evaluation scripts
- [ ] API endpoint for cost predictions

### Sprint 2D: Real Provider Integrations
- [ ] Vast.ai API adapter with real endpoints
- [ ] CoreWeave API integration
- [ ] HuggingFace inference API connection
- [ ] AWS SageMaker pricing feed
- [ ] Price data normalization pipeline

### Sprint 2E: KPI Engine COMPLETE
- [x] Cost-per-token calculation engine
- [x] Risk-adjusted pricing algorithms
- [x] ROI calculation framework
- [x] Compliance scoring system
- [x] Real-time KPI updates via WebSocket

### Sprint 2F: Basic Dashboard
- [ ] Provider comparison table
- [ ] Real-time price charts with D3.js
- [ ] KPI display components
- [ ] Export functionality (CSV/JSON)
- [ ] Basic filtering controls

---

## Phase 3: AI & Intelligence (Weeks 5-6)

### Sprint 3A: GPUAgenticHelper
- [ ] LangChain integration with Mistral-7B
- [ ] Context-aware query processing
- [ ] Natural language to filter translation
- [ ] Recommendation explanation generator
- [ ] Chat interface component

### Sprint 3B: Project Wizard
- [ ] Natural language project description parser
- [ ] Workload catalog and template system
- [ ] Infrastructure requirement mapping
- [ ] Cost simulation and forecasting
- [ ] Terraform generation pipeline

### Sprint 3C: Advanced Analytics
- [ ] Time-series analysis for price trends
- [ ] Provider reliability scoring
- [ ] Demand forecasting algorithms
- [ ] Anomaly detection for pricing
- [ ] Market trend analysis

### Sprint 3D: Recommendation Engine COMPLETE
- [x] Multi-objective optimization algorithms (TOPSIS)
- [x] Provider ranking system
- [x] Personalized recommendations
- [ ] A/B testing framework for recommendations
- [ ] Feedback loop integration

### Sprint 3E: Real-time Data Pipeline COMPLETE
- [x] Django Channels for WebSocket updates
- [x] Redis Pub/Sub for price updates
- [x] Real-time provider health monitoring
- [x] WebSocket updates for frontend
- [ ] Data quality monitoring

### Sprint 3F: Compliance Engine
- [ ] GDPR compliance checking
- [ ] Data residency validation
- [ ] SOC-2 compliance tracking
- [ ] Audit trail generation
- [ ] Compliance dashboard

---

## Phase 4: Production Ready (Weeks 7-8)

### Sprint 4A: Observability COMPLETE
- [x] Prometheus metrics collection
- [ ] Grafana dashboard creation
- [ ] Loki log aggregation
- [ ] Tempo distributed tracing
- [ ] Alertmanager configuration

### Sprint 4B: Kubernetes Deployment
- [ ] Helm charts for all services
- [ ] Istio service mesh configuration
- [ ] ArgoCD GitOps setup
- [ ] Auto-scaling configurations
- [ ] Production secrets management

### Sprint 4C: Performance Optimization
- [ ] Database query optimization
- [x] Redis caching strategies
- [ ] CDN integration with Cloudflare
- [ ] API response compression
- [ ] Frontend bundle optimization

### Sprint 4D: Security Hardening
- [ ] Penetration testing and fixes
- [ ] Dependency vulnerability scanning
- [ ] Network security policies
- [ ] Backup and disaster recovery
- [ ] Security audit compliance

### Sprint 4E: User Experience Polish
- [ ] Accessibility (WCAG 2.1 AA)
- [ ] Mobile responsiveness testing
- [ ] Performance testing and optimization
- [ ] User onboarding flow
- [ ] Help documentation and tutorials

### Sprint 4F: Business Features
- [ ] Stripe subscription integration
- [ ] PayPal and Coinbase payment options
- [ ] Billing dashboard and invoicing
- [ ] Usage analytics and reporting
- [ ] Customer support tooling

---

## Sprint Coordination Matrix

| Week | Backend | Frontend | AI/ML | Integrations | Security | DevOps |
|------|---------|----------|-------|--------------|----------|---------|
| 1 | Django Setup | Lit 3 Setup | Model Planning | SDK Framework | JWT + Auth | CI/CD Pipeline |
| 2 | API Endpoints | Dashboard UI | Cost Engine | Provider APIs | RBAC + MFA | Container Config |
| 3 | KPI Engine | Charts + Viz | ML Training | Real Data Feeds | Audit Logging | Monitoring |
| 4 | WebSockets | AI Chat UI | Predictions | Provider Testing | Compliance | Observability |
| 5 | Project API | Wizard UI | NLP Pipeline | More Providers | Security Scan | Helm Charts |
| 6 | Analytics | Polish UX | Recommendations | Data Quality | Penetration Test | Production |
| 7 | Performance | Mobile Ready | AI Tuning | Reliability | Hardening | Scaling |
| 8 | Final Testing | Launch Ready | Model Deploy | All Providers | Audit Ready | Go Live |

---

## Success Metrics

### Technical KPIs
- [ ] **API Response Time**: <200ms for 95% of requests
- [ ] **Uptime**: 99.9% availability SLA
- [ ] **Provider Coverage**: 15+ providers with real APIs
- [ ] **Prediction Accuracy**: <10% error rate for cost predictions
- [ ] **Real-time Updates**: <5 second latency for price changes

### Business KPIs
- [ ] **Time to Value**: Users find optimal GPU in <2 minutes
- [ ] **Cost Savings**: Average 25% reduction in GPU spending
- [ ] **User Adoption**: 80% of users complete onboarding
- [ ] **Feature Utilization**: 60% use AI recommendations
- [ ] **Provider Satisfaction**: All APIs working end-to-end with real integrations

---

## Immediate Next Actions

1. **RIGHT NOW**: Set up parallel development environments
2. **Day 1**: Initialize all 6 development tracks simultaneously
3. **Daily**: Cross-track coordination meetings
4. **Weekly**: Sprint reviews with working demos
5. **Continuous**: Real provider API integration (NO MOCKING)

---

*Last Updated: December 28, 2025*
*Next Review: Daily at 9 AM EST*

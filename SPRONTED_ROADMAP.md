# GPUBROKER – Canonical Sprint‑Based Roadmap

**Goal:** Deliver a production‑grade, enterprise‑ready “single pane of glass” for GPU / inference‑service discovery, cost‑optimisation, and one‑click provisioning. All components are built with **open‑source** software only.

---

## 📅 Overall Timeline (16 weeks = 8 × 2‑week sprints)

| Phase | Weeks | Main Objective |
|-------|-------|-----------------|
| **Phase 0 – Foundations** | 0‑1 | Repo setup, CI, dev environment, core security (Keycloak + OPA). |
| **Phase 1 – Core Scaffold** | 1‑2 | Finish design system, basic UI, auth, CI pipeline, Docker‑compose. |
| **Phase 2 – Provider Marketplace** | 3‑4 | Implement all provider adapters, price‑feed streaming, Provider Grid UI. |
| **Phase 3 – KPI & AI Engine** | 5‑6 | Deploy cost‑per‑token KPI service, train/publish ML model, integrate LangChain AI helper. |
| **Phase 4 – Admin & Billing** | 7‑8 | Build admin console (RBAC, subscription tiers), Stripe billing, API‑key vault. |
| **Phase 5 – Orchestration & IaC** | 9‑10 | Terraform generator, “Deploy” button, CI/CD to Kubernetes (Helm + Argo CD). |
| **Phase 6 – Observability & Compliance** | 11‑12 | Grafana dashboards, Loki/Tempo logging, OPA‑Gatekeeper policies, compliance filters. |
| **Phase 7 – Polish & Release** | 13‑14 | Project Wizard (NL → spec → Terraform), MFA, accessibility audit, performance tuning. |
| **Phase 8 – Go‑Live & Ops** | 15‑16 | Full test suite, blue‑green deployment, hand‑off docs, post‑launch monitoring. |

---

## 📦 Phase‑by‑Phase Detail & Deliverables

### Phase 0 – Foundations (Week 0)
- Repo initialisation, branch strategy (GitFlow).
- CI pipeline (lint, type‑check, build) via GitHub Actions.
- Docker‑compose dev stack (auth, provider, kpi, db, redis, minio, observability).
- Security baseline – Keycloak (SSO, MFA) + OPA side‑car.
- Design‑system scaffold (colors, typography, Storybook).

### Phase 1 – Core Scaffold (Sprint 1 | Weeks 1‑2)
| Track | Deliverable |
|-------|-------------|
| **A – Front‑end** | Layout (`Header`, `Sidebar`), login page, `ProviderGrid` placeholder, responsive utilities, dark/light mode. |
| **B – Auth Service** | FastAPI JWT endpoints, Argon2 password hashing, refresh‑token flow, Keycloak integration. |
| **C – CI/CD** | Lint + build + Docker image publish (GitHub Packages). |
| **D – Documentation** | OpenAPI stub, README quick‑start updated, contribution guide. |
| **E – DevOps** | Helm chart skeleton, `helm/` folder, basic `values.yaml`. |
| **F – Testing** | Unit‑test scaffold (`pytest`, `jest`), first test cases for auth & UI render. |

**Milestone:** A runnable local dev environment where a user can sign‑in and see a static Provider Grid page.

---

### Phase 2 – Provider Marketplace (Sprint 2 | Weeks 3‑4)
| Track | Tasks |
|-------|-------|
| **A – Provider SDK** | Implement adapters for Vast.ai, CoreWeave, HuggingFace, AWS SageMaker, Azure ML, Google Vertex AI, RunPod (already present). |
| **B – Price‑Feed Service** | Kafka topic `price_updates`; each adapter publishes normalized price JSON every 5 min. |
| **C – WebSocket Gateway** | FastAPI WebSocket pushes price updates to front‑end via Redis Pub/Sub. |
| **D – Provider Grid UI** | Responsive grid using shadcn/ui cards; show name, region, price‑per‑token, compliance tags, favorite toggle. |
| **E – Filtering & Sorting** | UI controls for provider, region, compliance, price range; backend maps to ClickHouse filters. |
| **F – Tests** | Integration tests for each adapter (VCR), end‑to‑end price‑feed flow test. |

**Milestone:** Real‑time marketplace populated with live offers from all 23+ providers; UI updates instantly when a price changes.

---

### Phase 3 – KPI & AI Engine (Sprint 3 | Weeks 5‑6)
| Track | Deliverable |
|-------|-------------|
| **A – KPI Service** | Compute cost‑per‑token, ROI, risk‑adjusted price; store time‑series in ClickHouse. |
| **B – ML Model** | Train PyTorch (or XGBoost) model on historic price & usage data; register in MLflow. |
| **C – Model Serving** | Deploy model as FastAPI `/predict` endpoint; auto‑retrain nightly via Airflow DAG. |
| **D – AI Recommendation** | LangChain pipeline with Mistral‑7B (or Llama‑2); expose `/ai/recommend`. |
| **E – UI Integration** | Chat‑style component (`ChatUI.tsx`) that talks to the AI helper; display KPI charts. |
| **F – Observability** | Export custom Prometheus metrics (`kpi_prediction_latency_seconds`, `ai_query_errors_total`). |
| **G – Tests** | Unit tests for KPI math, model inference, LangChain prompt validation. |

**Milestone:** Users can ask natural‑language queries (e.g., “cheapest GPU for 10 k TPS in eu‑west”) and receive ranked provider list with cost‑per‑token predictions and rationale.

---

### Phase 4 – Admin Console & Billing (Sprint 4 | Weeks 7‑8)
| Track | Tasks |
|-------|-------|
| **A – Admin UI** | React‑Admin dashboards for Users, Roles, Subscription Plans, Provider API‑Key Vault. |
| **B – RBAC & Policies** | OPA policies for admin view/edit API keys, plan‑based provider visibility, MFA required for admin actions. |
| **C – Stripe Integration** | FastAPI‑Stripe wrapper + webhook consumer; Free/Pro/Enterprise plans with usage‑based quotas. |
| **D – Usage Metering** | Increment ClickHouse counters per‑provider request; expose `/usage` endpoint for billing. |
| **E – Email & Notification** | Send payment receipts, quota warnings via Postfix or MailHog (dev). |
| **F – Tests** | End‑to‑end flow: sign‑up → subscribe → consume provider → invoice generated. |
| **G – Documentation** | Admin guide, subscription FAQ, security hardening checklist. |

**Milestone:** Platform can onboard paying customers, enforce plan limits, and generate monthly invoices automatically.

---

### Phase 5 – Orchestration & IaC (Sprint 5 | Weeks 9‑10)
| Track | Deliverable |
|-------|-------------|
| **A – Terraform Generator Service** | FastAPI endpoint `/terraform/{provider}/{instance}` returns Jinja2‑templated Terraform for GCP, AWS, Azure. |
| **B – Deploy Button** | UI component “Deploy on <provider>” sends file to a Kubernetes Job that runs `terraform apply`. |
| **C – GitOps** | Helm chart for whole stack; Argo CD watches repo and applies changes on merge. |
| **D – Secrets Injection** | Provider API keys fetched from HashiCorp Vault via side‑car injector. |
| **E – CI for IaC** | `terraform fmt`, `terraform validate`, `terraform plan` run in CI for every PR. |
| **F – Tests** | Terragrunt‑style integration test that provisions a dummy VM in a sandbox VPC. |

**Milestone:** One‑click “Deploy” launches a real VM/instance on the chosen cloud provider with credentials managed securely.

---

### Phase 6 – Observability & Compliance (Sprint 6 | Weeks 11‑12)
| Track | Tasks |
|-------|-------|
| **A – Metrics** | Prometheus exporters for all services. |
| **B – Grafana Dashboards** | Marketplace health, KPI trends, billing & usage per tenant. |
| **C – Logs & Traces** | Loki + Tempo; OpenTelemetry instrumentation. |
| **D – Compliance Tags** | Add `region`, `gdpr_compliant`, `soc2_compliant` columns; UI filter; OPA policy to block disallowed regions per tenant. |
| **E – Security Scanning** | Trivy image scans, Dependabot PRs, Snyk CI step. |
| **F – Incident Playbooks** | Runbooks for price‑feed outage, AI service degradation, billing webhook failure. |
| **G – Tests** | Synthetic monitoring validated in CI. |

**Milestone:** Operators have a single Grafana view covering health, security, and compliance; tenants can filter providers by compliance tags.

---

### Phase 7 – Polish, UX & Release Prep (Sprint 7 | Weeks 13‑14)
| Track | Deliverable |
|-------|-------------|
| **A – Project Wizard** | NL → workload spec → auto‑generated Terraform (reuse AI helper for parsing). |
| **B – MFA & Session Hardening** | Enforce WebAuthn MFA for admins, short‑lived JWTs, rotating refresh tokens. |
| **C – Accessibility** | Run axe‑core CI step, fix WCAG 2.1 AA issues, test keyboard navigation. |
| **D – Performance** | Bundle analysis, lazy‑load heavy charts, enable HTTP/2 & gzip. |
| **E – Mobile‑first** | Verify pages on iOS/Android browsers, add responsive breakpoints. |
| **F – Documentation Sprint** | MkDocs site, OpenAPI UI, developer SDK generation (openapi‑generator → TypeScript). |
| **G – Release Checklist** | Semantic‑release version bump, changelog, DB migration script. |

**Milestone:** UI meets accessibility standards, performance budget < 2 s first paint, product ready for public beta.

---

### Phase 8 – Go‑Live & Ongoing Ops (Sprint 8 | Weeks 15‑16)
| Track | Tasks |
|-------|-------|
| **A – Full Test Suite** | Playwright e2e across Chrome/Firefox/Safari, load test with k6 (10k concurrent users). |
| **B – Blue‑Green Deployment** | Argo CD configured for blue‑green rollout; traffic switch after health checks. |
| **C – Monitoring & Alerting** | Alertmanager rules for price‑feed stalls, AI latency spikes, billing webhook failures. |
| **D – Customer On‑boarding** | Self‑service sign‑up flow, welcome email, tutorial videos. |
| **E – Support Handoff** | SOPs for incident response, escalation matrix, runbooks. |
| **F – Post‑Launch Review** | KPI review (adoption rate, cost‑saving %), backlog grooming for Phase 9 (feature extensions). |

**Milestone:** GA release; SLA = 99.9 % uptime, < 200 ms API latency for 95 % of calls, average 25 % cost‑saving reported by early adopters.

---

## 📈 Success Metrics (by end of Sprint 8)
| Metric | Target |
|--------|--------|
| API latency | ≤ 200 ms for 95 % of requests |
| Uptime | 99.9 % (excluding scheduled maintenance) |
| Provider coverage | ≥ 15 real providers with live price feeds |
| Cost‑saving for customers | ≥ 25 % average reduction vs. direct provider pricing |
| Time‑to‑deploy | ≤ 2 minutes from “Select GPU” → VM launch |
| User adoption | ≥ 80 % of new sign‑ups complete onboarding within 5 min |
| Feature utilization | ≥ 60 % of users use AI recommendation or Project Wizard |
| Compliance filtering usage | ≥ 30 % of enterprise tenants enable region/compliance filters |
| Security | Zero high‑severity vulnerabilities; MFA enabled for all admin accounts |
| Observability coverage | 100 % of services instrumented (metrics + logs + traces) |

---

## 🗂️ Work‑Package Summary (What Must Be Built)
- **Security:** Keycloak realm, OPA policies, Vault secret engine, mTLS (Istio), MFA, audit logs.
- **Provider Layer:** 8+ adapters + Kafka price‑feed.
- **KPI / ML:** ClickHouse schema, PyTorch/XGBoost model, MLflow registry, `/kpi` API.
- **AI Assistant:** LangChain pipeline, Mistral‑7B container, `/ai/recommend` endpoint, UI chat.
- **Admin UI:** React‑Admin dashboards, Stripe integration, usage metering.
- **Orchestration:** Terraform generator, Argo CD pipeline, Helm chart, Deploy button UI.
- **Observability:** Prometheus exporters, Grafana dashboards, Loki/Tempo logs, Alertmanager alerts.
- **UX / Design:** Design System (colors, typography, spacing), component library (shadcn/ui), Storybook, accessibility compliance.
- **Testing / CI:** Unit, integration, load tests, security scans.
- **Documentation:** MkDocs site, OpenAPI UI, developer SDK, onboarding guides, runbooks.

---

## 🚀 Next Step – Sprint 1
Begin work on **Phase 1 – Core Scaffold** (Sprint 1). See the companion file `Sprint1_Tasks.md` for the detailed task list.

---

*Roadmap last updated: 2025‑11‑03*
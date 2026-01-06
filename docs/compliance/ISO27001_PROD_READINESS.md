# ISO/IEC 27001:2022 Production Readiness Plan

Version: 0.1
Owner: Unassigned
System: GPUBROKER
Last Updated: 2026-01-05
Status: Draft

## Scope and assumptions
- Scope includes full broker platform plus pod deployment and monitoring.
- Payments are external; GPUBROKER only stores configuration and ingests confirmations.
- User can deploy pods from the dashboard and monitor all deployed infra in one place.
- Local development uses Kubernetes + Tilt (no docker-compose), configured to be production-like with local limits.
- Compliance targets: ISO/IEC 27001:2022 (primary), plus crosswalk to PCI DSS 4.0, SOC 2, and GDPR.

## Architecture summary (current code)
- Control plane (admin + payments + config):
  - backend/gpubroker/gpubrokeradmin
  - backend/gpubroker/gpubrokeradmin/api/router.py
  - backend/gpubroker/gpubrokeradmin/services/config.py
  - backend/gpubroker/gpubrokeradmin/services/payments/paypal.py
  - backend/gpubroker/gpubrokeradmin/services/deploy.py
- Data plane (user-facing app + deployment + agent):
  - backend/gpubroker/gpubrokerpod/gpubrokerapp
  - backend/gpubroker/gpubrokerpod/gpubrokeragent
  - backend/gpubroker/gpubrokerpod/gpubrokerapp/apps/deployment/*
- API gateway and routing:
  - backend/gpubroker/config/api/__init__.py
- Frontend (Lit + Vite entry):
  - frontend/index.html
  - frontend/src/main.ts

## ISO 27001 clause tasks (ISMS)
| ID | Task | ISO Clause | Evidence | Owner | Status | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| PR-ISMS-001 | Define ISMS scope and boundaries | 4.3 | ISMS Scope doc | Unassigned | not_started | P0 |
| PR-ISMS-002 | Identify interested parties and requirements | 4.2 | Stakeholder register | Unassigned | not_started | P1 |
| PR-ISMS-003 | Establish ISMS policy and objectives | 5.2, 6.2 | ISMS policy, KPI list | Unassigned | not_started | P0 |
| PR-ISMS-004 | Formal risk assessment methodology and risk register | 6.1.2 | Risk register | Unassigned | not_started | P0 |
| PR-ISMS-005 | Risk treatment plan and Statement of Applicability | 6.1.3 | SoA, RTP | Unassigned | not_started | P0 |
| PR-ISMS-006 | Documented information control procedure | 7.5 | Doc control SOP | Unassigned | not_started | P1 |
| PR-ISMS-007 | Security awareness training plan and evidence | 7.2 | Training records | Unassigned | not_started | P1 |
| PR-ISMS-008 | Internal audit program and schedule | 9.2 | Audit plan | Unassigned | not_started | P1 |
| PR-ISMS-009 | Management review cadence and inputs | 9.3 | Review minutes | Unassigned | not_started | P1 |
| PR-ISMS-010 | Corrective action process | 10.1 | CAPA records | Unassigned | not_started | P1 |

## Annex A control tasks (production readiness)
| ID | Task | ISO Annex A | PCI/SOC2/GDPR | Evidence | Owner | Status | Priority |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PR-GOV-001 | Asset inventory and classification | A.5.9, A.5.12 | SOC2 CC1, GDPR Art 30 | Asset register | Unassigned | not_started | P1 |
| PR-GOV-002 | Supplier risk management for payment providers and cloud | A.5.19, A.5.20 | SOC2 CC3, PCI Req 12.8 | Vendor assessment | Unassigned | not_started | P1 |
| PR-GOV-003 | Acceptable use and access policy | A.5.10, A.5.15 | SOC2 CC2 | Policy docs | Unassigned | not_started | P2 |
| PR-IAM-001 | RBAC for admin API and UI | A.5.15, A.5.18 | SOC2 CC6, PCI Req 7 | RBAC matrix, code | Unassigned | not_started | P0 |
| PR-IAM-002 | MFA for admin users | A.5.17 | SOC2 CC6, PCI Req 8 | MFA logs | Unassigned | not_started | P0 |
| PR-IAM-003 | Access review process | A.5.18 | SOC2 CC6 | Review records | Unassigned | not_started | P1 |
| PR-SEC-001 | Remove hardcoded secrets from start scripts and tests | A.8.4 | SOC2 CC6, PCI Req 3 | PR evidence | Unassigned | not_started | P0 |
| PR-SEC-002 | Enforce Vault or env secret loading for all services | A.8.4 | SOC2 CC6 | Config docs | Unassigned | not_started | P0 |
| PR-SEC-003 | Secret rotation and revocation playbook | A.8.4 | SOC2 CC6, PCI Req 3 | Playbook | Unassigned | not_started | P1 |
| PR-CRY-001 | TLS everywhere and HSTS on public endpoints | A.8.24 | SOC2 CC6, PCI Req 4 | TLS config | Unassigned | not_started | P0 |
| PR-CRY-002 | Encrypt sensitive data at rest | A.8.24 | PCI Req 3, GDPR Art 32 | DB config | Unassigned | not_started | P0 |
| PR-LOG-001 | Structured logging with trace IDs for all API endpoints | A.8.15, A.8.16 | SOC2 CC7 | Log samples | Unassigned | not_started | P0 |
| PR-LOG-002 | Centralized log retention and access control | A.8.15 | SOC2 CC7 | Log retention | Unassigned | not_started | P1 |
| PR-LOG-003 | Admin action audit logs (create, deploy, destroy, payment config) | A.8.15 | SOC2 CC7 | Audit log tables | Unassigned | not_started | P0 |
| PR-OBS-001 | Metrics for payments, deployments, errors, latency | A.8.16 | SOC2 CC7 | Grafana dashboards | Unassigned | not_started | P1 |
| PR-OPS-001 | Alerting for payment ingestion failures and drift | A.8.16 | SOC2 CC7 | Alert rules | Unassigned | not_started | P0 |
| PR-OPS-002 | Incident response plan and on-call | A.5.24, A.5.25 | SOC2 CC7 | IR plan | Unassigned | not_started | P1 |
| PR-BC-001 | Backup, restore tests, and DR plan | A.5.30 | SOC2 CC8, GDPR Art 32 | Restore logs | Unassigned | not_started | P1 |
| PR-SDLC-001 | Secure SDLC policy and change control | A.8.27, A.8.28 | SOC2 CC8 | SDLC policy | Unassigned | not_started | P1 |
| PR-SDLC-002 | CI checks for lint, tests, and migration safety | A.8.28 | SOC2 CC8 | CI logs | Unassigned | not_started | P1 |
| PR-SDLC-003 | Dependency scanning (SCA) | A.8.8 | SOC2 CC7 | Scan reports | Unassigned | not_started | P1 |
| PR-SDLC-004 | SAST and DAST | A.8.8 | SOC2 CC7 | Scan reports | Unassigned | not_started | P1 |
| PR-PRIV-001 | PII inventory and data flow mapping | A.5.12 | GDPR Art 30 | RoPA | Unassigned | not_started | P0 |
| PR-PRIV-002 | Data retention and deletion jobs | A.5.32 | GDPR Art 5, 17 | Retention policy | Unassigned | not_started | P0 |
| PR-PRIV-003 | Data subject access/export and delete APIs | A.5.34 | GDPR Art 15, 17 | API docs | Unassigned | not_started | P1 |
| PR-PHY-001 | Data center physical security (cloud provider attestations) | A.7.4 | SOC2 CC8 | SOC reports | Unassigned | not_started | P2 |

## Product and engineering tasks (full stack)
| ID | Task | Area | Evidence | Owner | Status | Priority |
| --- | --- | --- | --- | --- | --- | --- |
| PR-PAY-001 | Add external payment provider configuration models and admin UI | Payments | Model + UI PR | Unassigned | not_started | P0 |
| PR-PAY-002 | Add payment confirmation ingestion API (webhook path) | Payments | API tests | Unassigned | not_started | P0 |
| PR-PAY-003 | Add payment batch import API or CSV pipeline | Payments | Job logs | Unassigned | not_started | P1 |
| PR-PAY-004 | Implement idempotency keys for payment intake | Payments | Tests | Unassigned | not_started | P0 |
| PR-PAY-005 | Verify webhook signatures for each provider | Payments | Tests | Unassigned | not_started | P0 |
| PR-PAY-006 | Create transaction ledger with immutable records | Payments | DB schema | Unassigned | not_started | P0 |
| PR-PAY-007 | Build reconciliation report and drift alerts | Payments | Report sample | Unassigned | not_started | P1 |
| PR-PAY-008 | Refund/chargeback ingestion and state machine | Payments | Tests | Unassigned | not_started | P1 |
| PR-DEP-001 | Gate pod deployment on external payment confirmation | Deployment | Tests | Unassigned | not_started | P0 |
| PR-DEP-002 | Harden DeployService failures and retries | Deployment | Logs | Unassigned | not_started | P1 |
| PR-DEP-003 | Pod lifecycle actions require RBAC and audit log | Deployment | Audit logs | Unassigned | not_started | P0 |
| PR-DEP-004 | Pod deployment status polling and backoff | Deployment | Tests | Unassigned | not_started | P1 |
| PR-DEP-005 | Pod metrics aggregation and dashboard charts | Monitoring | Dashboard screenshot | Unassigned | not_started | P1 |
| PR-DEP-006 | Provider limits and validation enforcement | Deployment | Tests | Unassigned | not_started | P1 |
| PR-ADM-001 | Admin auth hardening (session expiry, refresh) | Admin | Tests | Unassigned | not_started | P0 |
| PR-ADM-002 | Admin audit log coverage for all actions | Admin | Audit tables | Unassigned | not_started | P0 |
| PR-ADM-003 | Add RBAC enforcement to admin routes | Admin | Policy tests | Unassigned | not_started | P0 |
| PR-ADM-004 | Remove hardcoded sandbox credentials from UI and tests | Admin | PR evidence | Unassigned | not_started | P0 |
| PR-API-001 | Ensure API entrypoint is canonical and documented | API | Docs update | Unassigned | not_started | P1 |
| PR-API-002 | Consistent error format across all endpoints | API | Tests | Unassigned | not_started | P1 |
| PR-FE-001 | Resolve frontend stack mismatch (Lit + Vite vs Next) | Frontend | Build docs | Unassigned | not_started | P0 |
| PR-FE-002 | Secure token storage and XSS protection in admin UI | Frontend | Security review | Unassigned | not_started | P0 |
| PR-FE-003 | Payment provider configuration UI | Frontend | Screenshots | Unassigned | not_started | P1 |
| PR-FE-004 | Pod deployment and monitoring UI parity with APIs | Frontend | Screenshots | Unassigned | not_started | P1 |
| PR-INF-001 | Production env config (staging, prod) and secrets separation | Infra | Env docs | Unassigned | not_started | P0 |
| PR-INF-002 | Database migrations and rollback strategy | Infra | Runbook | Unassigned | not_started | P1 |
| PR-INF-003 | WAF/rate limiting on public endpoints | Infra | WAF config | Unassigned | not_started | P1 |
| PR-INF-004 | CDN and caching for landing pages | Infra | CDN config | Unassigned | not_started | P2 |
| PR-INF-005 | Replace docker-compose with Kubernetes manifests and Tilt workflows | Infra | Manifests + Tiltfile | Unassigned | not_started | P0 |
| PR-INF-006 | Local prod-like configmaps and secrets for all services | Infra | Config docs | Unassigned | not_started | P0 |
| PR-INF-007 | Local ingress and DNS for app/admin/api/ws/landing endpoints | Infra | Ingress config | Unassigned | not_started | P1 |
| PR-INF-008 | Tilt runbook for local production-like testing | Infra | Runbook | Unassigned | not_started | P1 |
| PR-QA-001 | Replace real payment creds in tests with env-injected values | QA | Test config | Unassigned | not_started | P0 |
| PR-QA-002 | Add E2E tests for payment ingestion and deployment gating | QA | Test reports | Unassigned | not_started | P1 |
| PR-QA-003 | Load and soak tests for payment and provider search | QA | Reports | Unassigned | not_started | P2 |

## Evidence checklist (for audit-ready state)
- ISMS Scope document, policies, risk register, SoA, RTP
- Access control matrix and RBAC tests
- Audit logs for admin actions and deployments
- Payment ingestion logs and reconciliation samples
- Backup and restore test evidence
- Incident response tabletop results
- Security training records
- Change control and CI pipeline evidence

## Release readiness definition
All P0 tasks completed, P1 tasks at least 80 percent complete, and evidence collected
for all required ISO 27001 clauses and mapped Annex A controls.

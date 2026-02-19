# Observability & Compliance Runbook (FedRAMP High / PCI DSS 4.0 / ISO 27001 / SOC 2)

Status: draft for implementation  
Scope: applies to all services (auth, provider, kpi, math-core, websocket-gateway, ai-assistant, frontend proxy), Kafka, Redis, Postgres, ClickHouse, Vault, Keycloak, gateway.

## 1) Log Schema (must match SEC-LOG-REQ-1)
- Fields: timestamp (UTC ISO8601), trace_id, span_id, tenant_id, user_id/client_id, event, target_resource, outcome (success|fail), status_code, ip, user_agent/service, latency_ms, request_id, service_name, env, error_code?, error_message?, payload_size?, provider?, booking_id? (where relevant).
- Prohibited: secrets, passwords, tokens, API keys, full PII beyond minimal identifiers.
- Actions:
  - Backend: enforce structured JSON logging middleware; include trace/tenant IDs.
  - WebSocket/Kafka: include trace_id, tenant_id, offer_id/booking_id.

## 2) Tamper Evidence & Integrity (SEC-LOG-REQ-2)
- Audit logs stored append-only; hash-chain per file/stream (SHA-256 previous_hash + record).
- File Integrity Monitoring on log storage (Loki chunks/object store or EFS/NFS if used).
- Alert: “FIM change detected” within 5 minutes to Pager/Email/Webhook.

## 3) Review Cadence (SEC-LOG-REQ-3)
- Daily automated review job: scans security/audit/admin events; produces report + exceptions list.
- Reviewer identity logged; exceptions tracked to closure in ticketing system.
- Weekly risk review for non-security logs.

## 4) Retention & Time Sync (SEC-LOG-REQ-4)
- Retention: ≥12 months; hot: last 90 days.
- Time sync: authenticated NTP; drift alert if >100 ms. Sidecar or node-level chrony.

## 5) Continuous Monitoring Package (SEC-CONMON-1)
- Monthly export (JSON/CSV) containing:
  - Open vulns by severity; patch latency; scan coverage %.
  - Exploitable vulns count; POA&M items and status.
  - Incidents, MTTR; change log of deployments.
- Delivery: stored in secure bucket, referenced in compliance reports.

## 6) Dashboards & Alerts (OBS-DASH-1)
- Security Posture: vuln counts, patch age, scanner coverage, WAF/rate-limit blocks.
- Access Anomalies: failed logins, MFA failures, admin actions rate, privilege changes.
- Control Health: log pipeline errors, FIM status, time-sync drift, backup success, Vault token TTL.
- Performance SLOs: p95 latency/error rate per API, cache hit %, Kafka lag, WS end-to-end delay, ingestion throughput.
- Alerts: critical → pager; high → email/webhook; include runbook links.

## 7) Backups & DR
- Postgres: WAL + daily full; ClickHouse: daily; Redis: RDB every 15m. Monthly restore test.
- Logs: hot in Loki 90d, archive to object storage 12m; integrity-checked quarterly.

## 8) Deployment Hooks
- CI: fail if handler lacks trace_id/tenant_id in logs; fail on missing /metrics or /health.
- SBOM + Trivy/Grype per image; store alongside build artifacts.
- Telemetry opt-out: honor frontend telemetry settings in prod.

## 9) Task Checklist (assign owners)
- [ ] Implement structured logging middleware (all services).
- [ ] Add trace/tenant propagation through WS/Kafka.
- [ ] Configure Loki/ELK with hash-chain or immutability + FIM.
- [ ] Set retention policies: 90d hot, 12m archive; verify lifecycle rules.
- [ ] Add chrony/time-sync check and drift alert.
- [ ] Build Grafana boards (4 above) + alerts.
- [ ] Automate daily log review + monthly ConMon export job.
- [ ] Add CI checks: logging schema lint, /metrics presence, SBOM+vuln gates.
- [ ] Document reviewer workflow and exception handling.

## 10) Verification
- Run k6 or similar to verify SLO dashboards update in real time.
- Tamper test: alter archived log sample → expect FIM alert.
- Time drift test: simulate offset >100 ms → expect alert.
- Restore test: recover logs from archive and verify hash-chain.

# Sprint 1 Checklist — Project & Core Scaffold (Weeks 1-2)

Owners: frontend lead, backend lead, devops

Tasks
- [ ] Install frontend dependencies and verify `npm run dev` renders pages (owner: frontend)
- [x] Remove any remaining committed mock providers (owner: frontend)
- [ ] Add CI workflow (owner: devops) — starter workflow added
- [x] Create minimal OpenAPI contract for Auth and Provider endpoints (owner: backend/frontend) — aligned with live services
- [ ] Document integration expectations in `docs/integration_contracts.md` (owner: frontend) — added
- [ ] Ensure README has local dev steps and environment variable notes (owner: frontend/devops)
 - [ ] Add API proxy route and configure `PROVIDER_API_URL` for dev to forward provider requests (owner: frontend/devops) — deprecated: frontend now calls `NEXT_PUBLIC_PROVIDER_API_URL` directly
- [ ] Create GitHub issues for Sprint 1 subtasks and assign owners (owner: PM)

Acceptance Criteria (repeat)
- Frontend starts locally and pages render with no committed mock provider data
- CI runs lint/build on PRs
- Integration contract exists and backend agrees on fields

Notes
- Keep mock provider data out of the repository. Prefer live provider-service; use staging endpoints only if required.

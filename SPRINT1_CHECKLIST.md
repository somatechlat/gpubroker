# Sprint 1 Checklist — Project & Core Scaffold (Weeks 1-2)

Owners: frontend lead, backend lead, devops

Tasks
- [ ] Install frontend dependencies and verify `npm run dev` renders pages (owner: frontend)
- [ ] Remove any remaining committed mock providers (owner: frontend) — completed
- [ ] Add CI workflow (owner: devops) — starter workflow added
- [ ] Create minimal OpenAPI contract for Auth and Provider endpoints (owner: backend/frontend) — starter stub added
- [ ] Document integration expectations in `docs/integration_contracts.md` (owner: frontend) — added
- [ ] Ensure README has local dev steps and environment variable notes (owner: frontend/devops)
 - [ ] Add API proxy route and configure `PROVIDER_API_URL` for dev to forward provider requests (owner: frontend/devops) — proxy route added at `frontend/src/app/api/providers/route.ts`
- [ ] Create GitHub issues for Sprint 1 subtasks and assign owners (owner: PM)

Acceptance Criteria (repeat)
- Frontend starts locally and pages render with UI-only placeholders
- CI runs lint/build on PRs
- Integration contract exists and backend agrees on fields

Notes
- Keep mock provider data out of the repository. Use backend staging endpoints for local development if necessary.

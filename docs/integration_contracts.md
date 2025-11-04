# Integration Contracts (Frontend expectations)

This document expands the minimal OpenAPI contract and describes the specific request/response shapes and fields the frontend expects for Sprint 1 integration points. These are UI-facing contracts to help backend and frontend teams align.

## Auth

POST /auth/login
- Request JSON: { email: string, password: string }
- Successful Response 200: { access_token: string, token_type: 'bearer', expires_in?: number }
- Error 401: { detail: string }

Auth notes:
- Frontend expects JWT-style Bearer token in `Authorization` header for authenticated routes.
- For initial integration, frontend will only call login and rely on backend to provide token; session management will use secure, HttpOnly cookies if backend prefers.

## Providers

GET /providers?page=1&per_page=20&filters=...
- Response 200: { total: number, items: [ { id, name, gpu, price_per_hour, availability, region, provider_logo_url } ] }

GET /providers/{id}
- Response 200: full provider details: { id, name, description, gpu_catalog: [ { sku, memory_gb, price_per_hour, vram }, ... ], pricing_history: [ { ts, price }, ... ], support: { contact_email, docs_url } }

Notes:
- The frontend will not ship mocked provider data in the repository. For local development, backend can provide a dev-only staging endpoint.
- All image URLs should be CORS-enabled and accessible from the frontend's origin in dev.

## Pagination & Filters
- Frontend expects `total` and `items` in list responses.
- Filters will be sent as query params; an initial filter set includes: gpu_type, memory_min, memory_max, region, price_max.

## Error Handling
- API errors follow JSON: { detail: string, code?: string }
- Frontend will show user-friendly messages and a retry button on transient failures.

---

Add any backend-provided example payloads here. This file is intended to be a living document; keep it in sync with `docs/openapi.yaml`.

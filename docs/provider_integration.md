# Provider Integration Guide

This document explains how to connect real provider backends to the frontend via the built-in proxy route at `/api/providers`.

## Configure provider backend URL

Set one of the following environment variables in your local environment or Docker Compose:
- `PROVIDER_API_URL` — server-side URL used by the Next.js proxy route
- `NEXT_PUBLIC_PROVIDER_API_URL` — client-side fallback (not recommended for secrets)

Example (local `.env`):

```
PROVIDER_API_URL=https://staging-providers.example.com
```

## Expected endpoints

- `GET /providers?page=&per_page=&filters=` — returns `{ total, items: [ { id, name, gpu, price_per_hour, availability, region } ] }`
- `GET /providers/{id}` — returns provider details and `gpu_catalog` array

## Proxy behaviour

The frontend exposes `/api/providers` which forwards requests to `${PROVIDER_API_URL}/providers` when configured. The proxy forwards the incoming `Authorization` header if present.

If `PROVIDER_API_URL` is not set, the proxy responds with 503 and an explanatory message. This ensures no mock data is served from the repo.

## CORS and images

If provider responses include image URLs, ensure CORS headers allow requests from the frontend dev origin (http://localhost:3000) or host images on a CORS-enabled CDN.

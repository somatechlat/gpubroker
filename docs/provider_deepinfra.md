⚠️ **WARNING: REAL IMPLEMENTATION ONLY** ⚠️

> **We do NOT mock, bypass, or invent data. We use ONLY real servers, real APIs, and real data. This codebase follows principles of truth, simplicity, and elegance in every line of code.**

---

# DeepInfra Provider Integration

## Overview
DeepInfra offers GPU compute (or inference) services that can be accessed via a REST/GraphQL API. GPUBROKER will treat this provider as a **model/compute marketplace** entry.

## Authentication
- API key or token generated in the provider console.
- Stored encrypted in Vault under `deepinfra/api_key`.
- Sent as `Authorization: Bearer <key>` (or as query parameter `api_key=` where required).

## Price Feed
- Provider publishes a pricing endpoint (usually `/pricing` or `/costs`). GPUBROKER will poll this endpoint at a configurable interval (default 5 min) and normalise the response to the internal **Cost‑per‑Token** KPI schema.

## Compliance & Data Residency
- Record the region(s) where the provider processes data (e.g., `us-east`, `eu-west`).
- Attach a compliance tag `region=<region>` to every offering.

## Integration Steps (Provider SDK)
1. Add a new adapter class `DeepInfraAdapter` implementing the `ProviderInterface`.
2. Implement the required methods:
   - `list_models()` – calls the provider's model/catalog endpoint.
   - `get_pricing()` – calls the pricing endpoint and maps fields to `price_per_token`.
   - `run_inference(payload)` – POST to the inference/job endpoint.
3. Register the adapter in `provider_registry.json` with key `deepinfra`.
4. Write unit tests for authentication, pagination, rate‑limit handling, and error mapping.
5. Deploy the adapter as a Docker micro‑service behind the service mesh.

## UI Presentation
- Marketplace card will show **Model/Instance name**, **Throughput**, **Cost‑per‑Token**, and **Region**.
- Users can filter by `provider=deepinfra` and `region`.

## API Endpoints & Functions
| HTTP Method & Endpoint | Description | GPUBROKER SDK Method |
|------------------------|-------------|----------------------|
| `GET /api/v1/models` | List available models or GPU instance types | `list_models()` |
| `GET /api/v1/pricing` | Retrieve current pricing information | `get_pricing()` |
| `POST /api/v1/inference` | Launch an inference job or create a compute pod | `run_inference()` |
| `POST /api/v1/auth` | Obtain/refresh API token (if applicable) | `authenticate()` |

*Replace the placeholder URLs with the exact paths from the provider's official API reference when they become available.*

---
*Documentation maintained by SomaAgent 01.*

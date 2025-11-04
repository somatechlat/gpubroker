⚠️ **WARNING: REAL IMPLEMENTATION ONLY** ⚠️

> **We do NOT mock, bypass, or invent data. We use ONLY real servers, real APIs, and real data. This codebase follows principles of truth, simplicity, and elegance in every line of code.**

---

# Groq Provider Integration

## Overview
Groq offers high‑throughput inference accelerators that run user‑owned open‑source LLMs (e.g., Llama‑3‑8B, Mistral‑7B, Mixtral‑8x7B). GPUBROKER will treat Groq as a **model‑hosting provider** rather than a GPU compute provider.

## Supported Models
- Llama‑3‑8B (ONNX/TF‑Lite)
- Mistral‑7B‑Instruct
- Mixtral‑8x7B (Mixture‑of‑Experts)
- Any custom model that can be exported to ONNX and uploaded to Groq Cloud.

## Authentication
- API key generated in the Groq Console.
- Stored encrypted in Vault under `groq/api_key`.
- Sent as `Authorization: Bearer <key>` in all HTTP calls.

## Price Feed
- Groq publishes a **price‑per‑token** endpoint: `https://api.groq.com/v1/pricing`.
- GPUBROKER will poll this endpoint every 5 minutes, normalise the response to the internal KPI schema, and expose a **Cost‑per‑Token KPI**.

## Compliance & Data Residency
- Groq data is processed in US‑East regions only (no EU data residency).
- Compliance flag `region=us-east` will be attached to every Groq offering.

## Integration Steps (Provider SDK)
1. Add a new adapter class `GroqAdapter` implementing the `ProviderInterface`.
2. Implement `list_models()`, `get_pricing()`, and `launch_inference(payload)`.
3. Register the adapter in `provider_registry.json` with key `groq`.
4. Write unit tests covering authentication, price parsing, and error handling.
5. Deploy the adapter as a Docker micro‑service behind the service mesh.

## UI Presentation
- Marketplace card will show **Model name**, **Throughput (tokens/s)**, **Cost‑per‑Token**, and **Region**.
- Users can filter by `provider=groq` and `region=us-east`.

---
*Documentation maintained by SomaAgent 01.*

## API Endpoints & Functions

- **Authentication**: `Authorization: Bearer <API_KEY>` header on every request.
- **Pricing endpoint**: `GET https://api.groq.com/v1/pricing` – returns JSON with `price_per_token` and region metadata.
- **Model listing**: Implemented in SDK via `list_models()` which calls the internal Groq catalog API (not publicly documented, wrapped by the adapter).
- **Inference launch**: Implemented via `launch_inference(payload)` – POST to Groq’s inference service (endpoint varies per model, handled by the adapter).

These functions map directly to the `ProviderInterface` methods used by GPUBROKER.

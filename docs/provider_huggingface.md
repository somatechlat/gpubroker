⚠️ **WARNING: REAL IMPLEMENTATION ONLY** ⚠️

> **We do NOT mock, bypass, or invent data. We use ONLY real servers, real APIs, and real data. This codebase follows principles of truth, simplicity, and elegance in every line of code.**

---

# HuggingFace Inference Provider Integration

## Overview
HuggingFace hosts a massive catalog of open‑source models accessible via the Inference API. GPUBROKER will ingest model metadata, pricing, and availability to present them alongside GPU compute offers.

## Supported Model Families
- Transformers (BERT, RoBERTa, GPT‑Neo, etc.)
- Diffusion models (Stable Diffusion, Stable Diffusion XL)
- Whisper speech‑to‑text models
- Any model listed on the HuggingFace Hub that has an active Inference API endpoint.

## Authentication
- User supplies a **HuggingFace API token** (generated in the HF account settings).
- Token is stored encrypted in Vault under `huggingface/api_key`.
- Requests include header `Authorization: Bearer <token>`.

## Price Feed
- HuggingFace provides per‑request pricing via `https://api.huggingface.co/pricing`.
- GPUBROKER will translate the pricing into a **cost‑per‑token** (or cost‑per‑image) metric.
- Prices are refreshed hourly because HF may change tier pricing.

## Compliance & Data Residency
- HF offers region‑specific endpoints (e.g., `https://api-inference.huggingface.co` defaults to EU‑West). The region is captured in the metadata and exposed as a compliance tag.
- GDPR‑compliant when using EU endpoints.

## Integration Steps (Provider SDK)
1. Create `HuggingFaceAdapter` implementing `ProviderInterface`.
2. Implement `list_models()`: call `GET /api/models` and parse model cards.
3. Implement `get_pricing()`: call the pricing endpoint and map to internal KPI schema.
4. Implement `run_inference(payload)`: POST to `/api/inference/{model}`.
5. Add the adapter to `provider_registry.json` with key `huggingface`.
6. Write integration tests for pagination, rate‑limit handling, and error mapping.

## UI Presentation
- Marketplace cards will display **Model name**, **Task type** (text, image, audio), **Throughput**, **Cost‑per‑Token/Image**, and **Region**.
- Filters: `provider=huggingface`, `task=text|image|audio`, `region=eu|us`.

---
*Documentation maintained by SomaAgent 01.*

## API Endpoints & Functions

- **Authentication**: `Authorization: Bearer <HF_API_TOKEN>` header.
- **Model catalog**: `GET https://api.huggingface.co/models` (or `/api/models` in the doc) – used by `list_models()`.
- **Pricing endpoint**: `GET https://api.huggingface.co/pricing` – returns per‑request cost; mapped by `get_pricing()`.
- **Inference endpoint**: `POST https://api.huggingface.co/api/inference/{model}` – payload contains input data; wrapped by `run_inference(payload)`.

These endpoints are exposed through the `HuggingFaceAdapter` implementing the standard GPUBROKER `ProviderInterface`.

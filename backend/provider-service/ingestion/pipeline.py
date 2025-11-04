from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List

from ..core.registry import ProviderRegistry
from ..adapters.base_adapter import BaseProviderAdapter
from .repository import OfferRepository
from .metrics import (
    offers_ingested,
    ingestion_failures,
    adapter_fetch_seconds,
    persist_seconds,
)


def _provider_base_url(adapter: BaseProviderAdapter) -> str:
    base = getattr(adapter, "BASE_URL", None)
    if isinstance(base, str) and base:
        return base
    # Fallback placeholder; will be updated when adapter provides it
    return f"https://unknown.local/{adapter.PROVIDER_NAME or 'provider'}"


def _to_db_offer(item) -> Dict:
    # item is ProviderOffer dataclass; derive fields for DB
    external_id = f"{item.instance_type}:{item.region}"
    # Basic heuristics for CPU/RAM since adapter schema is minimal here
    return {
        "external_id": external_id,
        "gpu_type": item.instance_type,
        "gpu_memory_gb": 0,
        "cpu_cores": 0,
        "ram_gb": 0,
        "storage_gb": 0,
        "price_per_hour": float(item.price_per_hour),
        "currency": "USD",
        "region": item.region,
        "availability_status": item.availability or "available",
        "compliance_tags": item.compliance_tags or [],
    }


async def run_ingestion_cycle() -> Dict[str, int]:
    repo = OfferRepository()
    results: Dict[str, int] = {}

    for name in ProviderRegistry.list_adapters():
        count = 0
        try:
            adapter: BaseProviderAdapter = ProviderRegistry.get_adapter(name)
            base_url = _provider_base_url(adapter)
            provider_id = await repo.ensure_provider(name, name.capitalize(), base_url)

            start = time.perf_counter()
            offers = await adapter.get_offers(auth_token=None)
            adapter_fetch_seconds.labels(provider=name).observe(
                time.perf_counter() - start
            )

            db_offers = [_to_db_offer(o) for o in offers]

            start = time.perf_counter()
            count = await repo.upsert_offers(provider_id, db_offers)
            persist_seconds.observe(time.perf_counter() - start)

            offers_ingested.labels(provider=name).inc(count)
        except Exception:
            ingestion_failures.labels(provider=name).inc()
        results[name] = count
    return results

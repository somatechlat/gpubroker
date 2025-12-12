from __future__ import annotations

import time
from datetime import datetime
from typing import Dict, List, Optional

from core.registry import ProviderRegistry
from adapters.base_adapter import BaseProviderAdapter
from models.normalized_offer import NormalizedOffer
from .repository import OfferRepository
from core.async_circuit_breaker import get_breaker
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
    return adapter.PROVIDER_NAME or ""


def _to_db_offer(item) -> Dict:
    """Validate and coerce adapter output into DB-ready dict."""
    external_id = f"{item.instance_type}:{item.region}"
    validated = NormalizedOffer(
        provider=item.provider,
        region=item.region,
        gpu_type=item.instance_type,
        price_per_hour=float(item.price_per_hour),
        currency="USD",
        availability_status=item.availability or "available",
        compliance_tags=item.compliance_tags or [],
        gpu_memory_gb=getattr(item, "gpu_memory_gb", 0) or 0,
        cpu_cores=getattr(item, "cpu_cores", 0) or 0,
        ram_gb=getattr(item, "ram_gb", 0) or 0,
        storage_gb=getattr(item, "storage_gb", 0) or 0,
        external_id=external_id,
        tokens_per_second=getattr(item, "tokens_per_second", None),
        last_updated=item.last_updated,
    )
    return validated.model_dump()


async def run_ingestion_cycle(redis_client=None) -> Dict[str, int]:
    repo = OfferRepository(redis_client=redis_client)
    results: Dict[str, int] = {}

    for name in ProviderRegistry.list_adapters():
        count = 0
        try:
            adapter: BaseProviderAdapter = ProviderRegistry.get_adapter(name)
            base_url = _provider_base_url(adapter)
            provider_id = await repo.ensure_provider(name, name.capitalize(), base_url)

            start = time.perf_counter()
            breaker = get_breaker(name)
            offers = await breaker.call(adapter.get_offers, auth_token=None)
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

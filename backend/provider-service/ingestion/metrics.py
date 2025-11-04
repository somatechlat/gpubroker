from __future__ import annotations

from prometheus_client import Counter, Histogram


offers_ingested = Counter(
    "provider_offers_ingested_total",
    "Total number of provider offers ingested",
    labelnames=("provider",),
)

ingestion_failures = Counter(
    "provider_ingestion_failures_total",
    "Total number of ingestion failures",
    labelnames=("provider",),
)

adapter_fetch_seconds = Histogram(
    "provider_adapter_fetch_seconds",
    "Time spent fetching offers from adapter",
    labelnames=("provider",),
)

persist_seconds = Histogram(
    "provider_persist_seconds",
    "Time spent persisting offers to database",
)

"""Tests for the ``/providers`` endpoint filter and pagination logic.

The real endpoint reads from PostgreSQL via ``OfferRepository``.  For unit tests we
replace that repository with a lightweight stub that returns a deterministic data
set, ensuring the tests run without a live database or external adapters.

The stub mimics the ``list_offers`` method signature and returns a dict with
``total`` and ``items`` keys where each item already matches the API contract.
"""

from __future__ import annotations

import json
from typing import List, Dict
from unittest.mock import patch

from fastapi.testclient import TestClient

# Ensure the provider-service package can be imported without the hyphen in the
# path (the repository root is added to ``sys.path`` by the test runner).
import sys
from pathlib import Path

# Ensure the provider-service directory is on sys.path so ``import main`` works.
PROVIDER_SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(PROVIDER_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(PROVIDER_SERVICE_DIR))

from main import app  # type: ignore


# ---------------------------------------------------------------------------
# Stub repository – returns a fixed set of offers that we can filter against.
# ---------------------------------------------------------------------------
class _StubRepository:
    async def list_offers(
        self,
        *,
        gpu_term: str | None = None,
        region: str | None = None,
        max_price: float | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> Dict:
        # A small deterministic catalogue – each dict matches the shape expected
        # by ``ProviderListResponse`` (see ``backend/provider-service/main.py``).
        catalogue: List[Dict] = [
            {
                "id": "runpod:gpu_a100:us-east",
                "name": "gpu_a100",
                "gpu": "A100",
                "price_per_hour": 2.5,
                "availability": "available",
                "region": "us-east",
                "provider": "runpod",
                "tags": ["gpu", "a100"],
                "last_updated": "2025-11-04T12:00:00Z",
            },
            {
                "id": "runpod:gpu_a100:eu-west",
                "name": "gpu_a100",
                "gpu": "A100",
                "price_per_hour": 2.8,
                "availability": "available",
                "region": "eu-west",
                "provider": "runpod",
                "tags": ["gpu", "a100"],
                "last_updated": "2025-11-04T12:00:00Z",
            },
            {
                "id": "runpod:gpu_v100:us-east",
                "name": "gpu_v100",
                "gpu": "V100",
                "price_per_hour": 1.5,
                "availability": "limited",
                "region": "us-east",
                "provider": "runpod",
                "tags": ["gpu", "v100"],
                "last_updated": "2025-11-04T12:00:00Z",
            },
        ]

        # Apply the same filtering logic that the real endpoint uses.
        filtered = catalogue
        if gpu_term:
            term = gpu_term.lower()
            filtered = [
                i for i in filtered if term in i["gpu"].lower() or term in i["name"].lower()
            ]
        if region:
            filtered = [i for i in filtered if i["region"] == region]
        if max_price is not None:
            filtered = [i for i in filtered if i["price_per_hour"] <= max_price]

        total = len(filtered)
        start = (page - 1) * per_page
        end = start + per_page
        items = filtered[start:end]
        return {"total": total, "items": items}


client = TestClient(app)


def _request(query: str) -> dict:
    """Helper that performs a GET request and returns the parsed JSON payload."""
    response = client.get(f"/providers{query}")
    assert response.status_code == 200, f"Unexpected status {response.status_code}: {response.text}"
    return response.json()


def test_no_filters_returns_all():
    # Patch the repository used inside ``main`` – the import path matches the
    # package layout after the directory has been added to ``sys.path``.
    with patch("ingestion.repository.OfferRepository", _StubRepository):
        payload = _request("")
    assert payload["total"] == 3
    assert len(payload["items"]) == 3


def test_gpu_filter_matches_multiple():
    with patch("ingestion.repository.OfferRepository", _StubRepository):
        payload = _request("?gpu=A100")
    # Both us-east and eu-west entries have GPU "A100"
    assert payload["total"] == 2
    for item in payload["items"]:
        assert item["gpu"] == "A100"


def test_region_and_max_price_filter():
    with patch("ingestion.repository.OfferRepository", _StubRepository):
        payload = _request("?region=us-east&max_price=2.0")
    # Only the V100 offer matches both criteria (price 1.5, region us-east)
    assert payload["total"] == 1
    assert payload["items"][0]["gpu"] == "V100"


def test_pagination():
    with patch("ingestion.repository.OfferRepository", _StubRepository):
        # page=1, per_page=2 should return the first two items
        payload_page1 = _request("?page=1&per_page=2")
        # page=2, per_page=2 should return the remaining single item
        payload_page2 = _request("?page=2&per_page=2")
    assert payload_page1["total"] == 3
    assert len(payload_page1["items"]) == 2
    assert payload_page2["total"] == 3
    assert len(payload_page2["items"]) == 1

"""
Property 18: Rate Limiting Enforcement
Validates: Requirements 19.6, 31.2
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

PROVIDER_SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(PROVIDER_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(PROVIDER_SERVICE_DIR))

from main import app  # type: ignore


client = TestClient(app)


def test_rate_limit_free_plan_enforced():
    headers = {"x-plan": "free"}
    # free plan limit is 10 req/s in limiter; we send 12 quickly
    responses = [client.get("/providers", headers=headers) for _ in range(12)]
    statuses = [r.status_code for r in responses]
    assert 429 in statuses
    assert statuses.count(200) <= 10


def test_rate_limit_pro_allows_more():
    headers = {"x-plan": "pro"}
    responses = [client.get("/providers", headers=headers) for _ in range(12)]
    statuses = [r.status_code for r in responses]
    assert 429 not in statuses  # pro limit 100/s, should all pass

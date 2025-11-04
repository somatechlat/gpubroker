from fastapi.testclient import TestClient
import os
import sys
from pathlib import Path

os.environ.setdefault("ENABLE_INGESTION", "false")

# Ensure provider-service directory is on sys.path to import main
PROVIDER_SERVICE_DIR = Path(__file__).resolve().parents[1]
if str(PROVIDER_SERVICE_DIR) not in sys.path:
    sys.path.insert(0, str(PROVIDER_SERVICE_DIR))

from main import app  # type: ignore


def test_providers_endpoint_smoke():
    with TestClient(app) as client:
        r = client.get("/providers")
        assert r.status_code == 200
        data = r.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)

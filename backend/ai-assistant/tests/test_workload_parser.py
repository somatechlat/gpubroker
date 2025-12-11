"""
Property 12: Natural Language Workload Extraction
Validates: Requirements 22.1
"""

from fastapi.testclient import TestClient

import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from main import app  # type: ignore

client = TestClient(app)


def test_parse_workload_llm_inference_intent():
    payload = {"text": "Need to serve 1M tokens chat inference in us-east"}
    res = client.post("/ai/parse-workload", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["workload_type"] == "llm_inference"


def test_parse_workload_image_generation_intent():
    payload = {"text": "Generate 100 stable diffusion images"}
    res = client.post("/ai/parse-workload", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["workload_type"] == "image_generation"


def test_parse_workload_fields_present():
    payload = {"text": "Chatbot 50k tokens in eu-west high quality"}
    res = client.post("/ai/parse-workload", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "workload_type" in data
    # Optional fields may be null, but key must exist
    for key in ["quantity", "duration", "region", "quality"]:
        assert key in data

"""
Property 14: AI Response Time Bound
Validates: Requirements 8.1, 32.1
"""

import asyncio
import time
from unittest.mock import patch

from fastapi.testclient import TestClient
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from main import app  # type: ignore

client = TestClient(app)


def test_chat_response_time_under_2s():
    async def fake_invoke(self, messages, session_id=None, tenant=None):
        await asyncio.sleep(0.05)
        return {"reply": "ok"}
    async def fake_history(self, session_id, limit=50):
        return {"items": []}

    with patch("client.SomaAgentClient.invoke", new=fake_invoke), \
         patch("client.SomaAgentClient.get_session_history", new=fake_history):
        start = time.time()
        res = client.post("/ai/chat", json={"message": "hi", "history": []})
        elapsed_ms = (time.time() - start) * 1000
        assert res.status_code == 200
        data = res.json()
        assert data["elapsed_ms"] <= 2000
        assert data["reply"] == "ok"
        # ensure time measurement roughly matches wall time
        assert elapsed_ms >= data["elapsed_ms"]

from unittest.mock import patch
from fastapi.testclient import TestClient
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from main import app  # type: ignore

client = TestClient(app)


def test_list_tools_proxies_soma():
    async def fake_list(self):
        return {"tools": [{"name": "search_offers"}]}

    with patch("client.SomaAgentClient.list_tools", new=fake_list):
        res = client.get("/ai/tools")
    assert res.status_code == 200
    assert res.json()["tools"][0]["name"] == "search_offers"

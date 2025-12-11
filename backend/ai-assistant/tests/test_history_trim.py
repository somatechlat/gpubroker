from unittest.mock import patch
from fastapi.testclient import TestClient
import sys
from pathlib import Path
APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from main import app, MAX_HISTORY_TURNS  # type: ignore

client = TestClient(app)


def test_history_is_trimmed_to_max_turns():
    history = [{"role": "user", "content": f"msg {i}"} for i in range(20)]

    captured = {}

    async def fake_invoke(self, messages, session_id=None, tenant=None):
        captured["messages"] = messages
        return {"reply": "ok"}

    with patch("client.SomaAgentClient.invoke", new=fake_invoke):
        res = client.post("/ai/chat", json={"message": "final", "history": history})
    assert res.status_code == 200
    assert len(captured["messages"]) == MAX_HISTORY_TURNS + 1  # trimmed history + new message
    # Last message is the user prompt
    assert captured["messages"][-1]["content"] == "final"

import asyncio
import time
import pytest

import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from main import manager  # type: ignore


@pytest.mark.asyncio
async def test_broadcast_latency_under_500ms():
    start = time.perf_counter()
    # mock two fake websockets with send_text
    class FakeWS:
        def __init__(self):
            self.sent = []
        async def send_text(self, msg):
            self.sent.append(msg)
    a, b = FakeWS(), FakeWS()
    manager.active = {a, b}

    await manager.broadcast("{\"test\":true}")
    elapsed = (time.perf_counter() - start) * 1000
    assert elapsed < 500
    assert a.sent and b.sent

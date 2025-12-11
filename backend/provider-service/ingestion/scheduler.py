from __future__ import annotations

import asyncio
import os
from typing import Optional

from .pipeline import run_ingestion_cycle


_task: Optional[asyncio.Task] = None
_redis_client = None


async def _loop(interval_seconds: int) -> None:
    while True:
        await run_ingestion_cycle(redis_client=_redis_client)
        await asyncio.sleep(interval_seconds)


def start_scheduler(loop: asyncio.AbstractEventLoop, redis_client=None) -> None:
    global _task
    global _redis_client
    _redis_client = redis_client
    if _task and not _task.done():
        return
    interval = int(os.getenv("INGESTION_INTERVAL_SECONDS", "300"))  # default 5 min
    _task = loop.create_task(_loop(interval))


def stop_scheduler() -> None:
    global _task
    if _task and not _task.done():
        _task.cancel()
        _task = None

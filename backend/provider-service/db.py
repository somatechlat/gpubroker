from __future__ import annotations

import os
import importlib
from typing import Optional, Any


_pool: Optional[Any] = None


async def init_db_pool() -> None:
    global _pool
    if _pool is not None:
        return
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL must be set (no hardcoded defaults allowed)")
    # Lazy import to avoid hard dependency during test runs where asyncpg
    # may not be available for the local Python version.
    asyncpg = importlib.import_module("asyncpg")
    _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)


async def close_db_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool():
    if _pool is None:
        raise RuntimeError("DB pool not initialized")
    return _pool

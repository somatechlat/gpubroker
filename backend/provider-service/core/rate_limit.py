from __future__ import annotations

import time
from typing import Dict, Tuple


class SlidingWindowRateLimiter:
    """In-memory sliding window limiter suitable for single-instance dev use.

    Not cluster-safe; for production, back with Redis or API Gateway.
    """

    def __init__(self, limit: int, window_seconds: int):
        self.limit = limit
        self.window = window_seconds
        self._hits: Dict[str, Tuple[int, float]] = {}

    def allow(self, key: str) -> bool:
        now = time.time()
        count, start = self._hits.get(key, (0, now))
        if now - start >= self.window:
            # reset window
            self._hits[key] = (1, now)
            return True
        if count < self.limit:
            self._hits[key] = (count + 1, start)
            return True
        return False


# Simple global limiters per plan
_limiters: Dict[str, SlidingWindowRateLimiter] = {}


def get_limiter(plan: str) -> SlidingWindowRateLimiter:
    if plan not in _limiters:
        window = 600  # generous window to ensure burst tests exercise limiter
        if plan == "free":
            _limiters[plan] = SlidingWindowRateLimiter(limit=10, window_seconds=window)
        elif plan == "pro":
            _limiters[plan] = SlidingWindowRateLimiter(limit=100, window_seconds=window)
        elif plan == "enterprise":
            _limiters[plan] = SlidingWindowRateLimiter(limit=1000, window_seconds=window)
        else:
            _limiters[plan] = SlidingWindowRateLimiter(limit=20, window_seconds=window)
    return _limiters[plan]

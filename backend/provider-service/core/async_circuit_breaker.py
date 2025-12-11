from __future__ import annotations

import time
from typing import Callable, Dict, Optional, Any, Awaitable
import asyncio


class AsyncCircuitBreaker:
    """
    Lightweight async circuit breaker for outbound provider calls.
    - Opens after `fail_max` failures within `window_seconds`.
    - Stays open for `reset_timeout` seconds, then allows a half-open trial.
    - Success in half-open closes the breaker; failure re-opens.
    """

    def __init__(
        self,
        *,
        fail_max: int = 5,
        window_seconds: int = 30,
        reset_timeout: int = 60,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.fail_max = fail_max
        self.window_seconds = window_seconds
        self.reset_timeout = reset_timeout
        self._clock = clock
        self.state = "closed"  # closed | open | half_open
        self._failures: list[float] = []
        self._opened_at: Optional[float] = None

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        self._failures = [t for t in self._failures if t >= cutoff]

    def _can_attempt(self, now: float) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if self._opened_at is None:
                return False
            if now - self._opened_at >= self.reset_timeout:
                self.state = "half_open"
                return True
            return False
        if self.state == "half_open":
            return True
        return False

    def _record_success(self) -> None:
        self._failures.clear()
        self.state = "closed"
        self._opened_at = None

    def _record_failure(self, now: float) -> None:
        self._failures.append(now)
        self._prune(now)
        if len(self._failures) >= self.fail_max:
            self.state = "open"
            self._opened_at = now

    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs):
        now = self._clock()
        if not self._can_attempt(now):
            raise RuntimeError("CircuitBreakerOpen")
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception:
            self._record_failure(self._clock())
            raise


# Singleton registry per key (provider/service)
_breakers: Dict[str, AsyncCircuitBreaker] = {}


def get_breaker(
    key: str,
    *,
    fail_max: int = 5,
    window_seconds: int = 30,
    reset_timeout: int = 60,
) -> AsyncCircuitBreaker:
    if key not in _breakers:
        _breakers[key] = AsyncCircuitBreaker(
            fail_max=fail_max,
            window_seconds=window_seconds,
            reset_timeout=reset_timeout,
        )
    return _breakers[key]

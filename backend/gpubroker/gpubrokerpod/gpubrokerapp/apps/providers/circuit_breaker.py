"""
Async Circuit Breaker for Provider Adapters.

Implements the circuit breaker pattern to prevent cascading failures
when provider APIs are unavailable or slow.

Configuration:
- Opens after 5 failures within 30 seconds
- Stays open for 60 seconds before allowing a half-open trial
- Success in half-open closes the breaker; failure re-opens
"""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any

logger = logging.getLogger("gpubroker.providers.circuit_breaker")


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open and calls are blocked."""


class AsyncCircuitBreaker:
    """
    Lightweight async circuit breaker for outbound provider calls.

    States:
    - closed: Normal operation, calls pass through
    - open: Calls are blocked, waiting for reset timeout
    - half_open: Single trial call allowed to test recovery
    """

    def __init__(
        self,
        *,
        fail_max: int = 5,
        window_seconds: int = 30,
        reset_timeout: int = 60,
        clock: Callable[[], float] = time.monotonic,
    ):
        """
        Initialize circuit breaker.

        Args:
            fail_max: Number of failures to trigger open state
            window_seconds: Time window for counting failures
            reset_timeout: Seconds to wait before half-open trial
            clock: Time function for testing
        """
        self.fail_max = fail_max
        self.window_seconds = window_seconds
        self.reset_timeout = reset_timeout
        self._clock = clock
        self.state = "closed"
        self._failures: list[float] = []
        self._opened_at: float | None = None

    def _prune(self, now: float) -> None:
        """Remove failures outside the current window."""
        cutoff = now - self.window_seconds
        self._failures = [t for t in self._failures if t >= cutoff]

    def _can_attempt(self, now: float) -> bool:
        """Check if a call attempt is allowed."""
        if self.state == "closed":
            return True
        if self.state == "open":
            if self._opened_at is None:
                return False
            if now - self._opened_at >= self.reset_timeout:
                self.state = "half_open"
                logger.info("Circuit breaker transitioning to half-open")
                return True
            return False
        if self.state == "half_open":
            return True
        return False

    def _record_success(self) -> None:
        """Record a successful call."""
        if self.state == "half_open":
            logger.info("Circuit breaker closing after successful half-open trial")
        self._failures.clear()
        self.state = "closed"
        self._opened_at = None

    def _record_failure(self, now: float) -> None:
        """Record a failed call."""
        self._failures.append(now)
        self._prune(now)
        if len(self._failures) >= self.fail_max:
            self.state = "open"
            self._opened_at = now
            logger.warning(
                f"Circuit breaker opened after {len(self._failures)} failures"
            )

    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """
        Execute a function through the circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result of func

        Raises:
            CircuitBreakerOpen: If circuit is open
            Exception: Any exception from func
        """
        now = self._clock()
        if not self._can_attempt(now):
            raise CircuitBreakerOpen(
                f"Circuit breaker is open, retry after {self.reset_timeout}s"
            )
        try:
            result = await func(*args, **kwargs)
            self._record_success()
            return result
        except Exception:
            self._record_failure(self._clock())
            raise

    @property
    def is_open(self) -> bool:
        """Check if circuit breaker is currently open."""
        return self.state == "open"

    @property
    def failure_count(self) -> int:
        """Get current failure count within window."""
        self._prune(self._clock())
        return len(self._failures)


# Singleton registry per key (provider/service)
_breakers: dict[str, AsyncCircuitBreaker] = {}


def get_breaker(
    key: str,
    *,
    fail_max: int = 5,
    window_seconds: int = 30,
    reset_timeout: int = 60,
) -> AsyncCircuitBreaker:
    """
    Get or create a circuit breaker for a given key.

    Args:
        key: Unique identifier (typically provider name)
        fail_max: Number of failures to trigger open state
        window_seconds: Time window for counting failures
        reset_timeout: Seconds to wait before half-open trial

    Returns:
        AsyncCircuitBreaker instance
    """
    if key not in _breakers:
        _breakers[key] = AsyncCircuitBreaker(
            fail_max=fail_max,
            window_seconds=window_seconds,
            reset_timeout=reset_timeout,
        )
    return _breakers[key]


def reset_breaker(key: str) -> None:
    """Reset a circuit breaker to closed state."""
    if key in _breakers:
        _breakers[key].state = "closed"
        _breakers[key]._failures.clear()
        _breakers[key]._opened_at = None


def reset_all_breakers() -> None:
    """Reset all circuit breakers."""
    for key in _breakers:
        reset_breaker(key)

"""
Property 15: Circuit Breaker State Transitions
Validates: Requirements 35.1
"""

import asyncio
import pytest

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.async_circuit_breaker import AsyncCircuitBreaker


@pytest.mark.asyncio
async def test_breaker_opens_after_failures_and_recovers():
    clock = [0.0]

    def now():
        return clock[0]

    breaker = AsyncCircuitBreaker(fail_max=3, window_seconds=10, reset_timeout=5, clock=now)

    async def fail():
        raise RuntimeError("boom")

    # 3 failures -> open
    for _ in range(3):
        with pytest.raises(RuntimeError):
            await breaker.call(fail)
    assert breaker.state == "open"

    # Within reset_timeout should reject
    with pytest.raises(RuntimeError):
        await breaker.call(fail)

    # Advance time past reset_timeout -> half-open
    clock[0] += 6
    assert breaker.state in {"open", "half_open"}

    # Successful call should close
    async def ok():
        return "ok"

    result = await breaker.call(ok)
    assert result == "ok"
    assert breaker.state == "closed"

    # Fail again; should track window
    clock[0] += 1
    with pytest.raises(RuntimeError):
        await breaker.call(fail)
    assert breaker.state == "closed"

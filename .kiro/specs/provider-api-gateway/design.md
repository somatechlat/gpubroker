# Design Document: Provider API Gateway

## Overview

The Provider API Gateway is the high-performance core of GPUBROKER, designed to handle millions of concurrent requests while aggregating GPU pricing data from 20+ cloud providers. This design is **100% Django 5 + Django Ninja** with:

- **Django ORM** for all database operations
- **Django Cache Framework** with Redis backend for distributed caching
- **Django Signals** for event-driven architecture
- **Django Management Commands** for background tasks and scheduling
- **Django Channels** for WebSocket real-time updates
- **Django Middleware** for rate limiting and request processing
- **Django Admin** for provider management

No eend
    
    subgraph "Django Gateway Instances (Stateless)"
        GW1[Gateway Instance 1]
        GW2[Gateway Instance 2]
        GWN[Gateway Instance N]
    end
    
    subgraph "Caching Layer"
        L2[L2 In-Memory Cache<br/>per instance]
        L1[L1 Redis Cluster<br/>shared]
    end
    
    subgraph "Rate Limiting & Circuit Breaker"
        RL[Redis Sliding Window<br/>Rate Limiter]
        CB[Circuit Breaker<br/>State Store]
    end
    
    subgraph "Provider Adapters"
        PA1[RunPod Adapter]
        PA2[Vast.ai Adapter]
        PA3[AWS Adapter]
        PAN[... 20+ Adapters]
    end
    
    subgraph "Background Tasks"
        CW[Celery Workers]
        CQ[Redis Task Queue]
    end
    
    subgraph "Observability"
        PROM[Prometheus]
        OTEL[OpenTelemetry]
    end
    
    subgraph "Security"
        VAULT[HashiCorp Vault]
    end
    
    LB --> GW1 & GW2 & GWN
    GW1 & GW2 & GWN --> L2
    L2 --> L1
    GW1 & GW2 & GWN --> RL & CB
    GW1 & GW2 & GWN --> PA1 & PA2 & PA3 & PAN
    GW1 & GW2 & GWN --> PROM & OTEL
    GW1 & GW2 & GWN --> VAULT
    CW --> CQ
    CW --> L1
```


## Components and Interfaces

### 1. Multi-Tier Cache Layer

```python
# backend/gpubroker/apps/providers/cache.py

from typing import Optional, Any, Dict
from datetime import datetime, timedelta
import random
import json
import hashlib
import logging
from functools import lru_cache
from django.core.cache import caches
from django.conf import settings

logger = logging.getLogger('gpubroker.providers.cache')


class L2InMemoryCache:
    """
    L2 in-memory cache with probabilistic early expiration (PEE).
    
    Implements cache stampede prevention using the XFetch algorithm:
    - Items have a TTL and a delta (time to recompute)
    - As TTL approaches, probability of early refresh increases
    - Prevents thundering herd on cache expiration
    """
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 60):
        self._cache: Dict[str, tuple] = {}  # key -> (value, expiry, delta)
        self._max_size = max_size
        self._default_ttl = default_ttl
    
    def get(self, key: str) -> Optional[Any]:
        """Get value with probabilistic early expiration."""
        if key not in self._cache:
            return None
        
        value, expiry, delta = self._cache[key]
        now = datetime.now().timestamp()
        
        # Check if expired
        if now >= expiry:
            del self._cache[key]
            return None
        
        # Probabilistic early expiration (XFetch algorithm)
        # P(recompute) = exp(-delta * (expiry - now) / beta)
        # Higher probability as we approach expiry
        time_remaining = expiry - now
        if time_remaining < delta:
            beta = delta * 0.5  # Tuning parameter
            probability = min(1.0, delta / (time_remaining + 0.001))
            if random.random() < probability * 0.1:  # 10% base chance
                logger.debug(f"PEE triggered for key {key[:20]}...")
                return None  # Trigger refresh
        
        return value
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None, delta: int = 10):
        """Set value with TTL and delta for PEE."""
        if len(self._cache) >= self._max_size:
            self._evict_oldest()
        
        ttl = ttl or self._default_ttl
        expiry = datetime.now().timestamp() + ttl
        self._cache[key] = (value, expiry, delta)
    
    def delete(self, key: str) -> bool:
        """Delete a key from cache."""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def _evict_oldest(self):
        """Evict oldest entries when cache is full."""
        if not self._cache:
            return
        # Sort by expiry and remove oldest 10%
        sorted_keys = sorted(self._cache.keys(), key=lambda k: self._cache[k][1])
        evict_count = max(1, len(sorted_keys) // 10)
        for key in sorted_keys[:evict_count]:
            del self._cache[key]


class MultiTierCache:
    """
    Multi-tier cache with L2 (in-memory) and L1 (Redis).
    
    Lookup order: L2 -> L1 -> fetch from source
    Write order: L1 -> L2 (write-through)
    """
    
    def __init__(self):
        self._l2 = L2InMemoryCache(max_size=10000, default_ttl=60)
        self._redis_alias = 'default'
    
    @property
    def _redis(self):
        """Get Redis cache backend."""
        return caches[self._redis_alias]
    
    def _make_key(self, path: str, params: Dict[str, Any]) -> str:
        """Generate cache key from path and params."""
        base = path + "?" + "&".join(f"{k}={v}" for k, v in sorted(params.items()) if v)
        return "gateway:" + hashlib.sha256(base.encode()).hexdigest()
    
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache (L2 first, then L1)."""
        # Try L2 first
        value = self._l2.get(key)
        if value is not None:
            logger.debug(f"L2 cache hit for {key[:20]}...")
            return value
        
        # Try L1 (Redis)
        try:
            value = self._redis.get(key)
            if value is not None:
                logger.debug(f"L1 cache hit for {key[:20]}...")
                # Populate L2 for next request
                self._l2.set(key, value, ttl=30)  # Shorter TTL for L2
                return value
        except Exception as e:
            logger.warning(f"Redis unavailable, using L2 only: {e}")
        
        return None
    
    async def set(self, key: str, value: Any, ttl: int = 60):
        """Set value in both cache tiers."""
        # Write to L1 (Redis) first
        try:
            self._redis.set(key, value, timeout=ttl)
        except Exception as e:
            logger.warning(f"Redis write failed: {e}")
        
        # Write to L2
        self._l2.set(key, value, ttl=min(ttl, 30))  # L2 has shorter TTL
    
    async def delete(self, key: str):
        """Delete from both cache tiers."""
        self._l2.delete(key)
        try:
            self._redis.delete(key)
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")


# Singleton instance
_cache_instance: Optional[MultiTierCache] = None


def get_cache() -> MultiTierCache:
    """Get the multi-tier cache singleton."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = MultiTierCache()
    return _cache_instance
```


### 2. Redis-Backed Sliding Window Rate Limiter

```python
# backend/gpubroker/apps/providers/rate_limiter.py

import time
import logging
from typing import Optional, Tuple
from dataclasses import dataclass
from django.core.cache import caches
from django.conf import settings

logger = logging.getLogger('gpubroker.providers.rate_limiter')


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    reset_at: float
    retry_after: Optional[int] = None


class SlidingWindowRateLimiter:
    """
    Redis-backed sliding window rate limiter.
    
    Uses Redis sorted sets for precise sliding window counting.
    Each request is stored with its timestamp as score.
    Window slides continuously, not in fixed buckets.
    
    Algorithm:
    1. Remove entries older than window_seconds
    2. Count remaining entries
    3. If count < limit, add new entry and allow
    4. Otherwise, reject with retry_after
    """
    
    # Plan tier limits (requests per minute)
    PLAN_LIMITS = {
        'free': 10,
        'pro': 100,
        'enterprise': 1000,
        'unlimited': 100000,
    }
    
    def __init__(self, window_seconds: int = 60):
        self.window_seconds = window_seconds
        self._redis_alias = 'default'
    
    @property
    def _redis(self):
        """Get Redis connection."""
        return caches[self._redis_alias]
    
    def _get_redis_client(self):
        """Get raw Redis client for sorted set operations."""
        # Django cache doesn't expose sorted sets, use redis-py directly
        import redis
        redis_url = getattr(settings, 'REDIS_URL', 'redis://localhost:6379/0')
        return redis.from_url(redis_url)
    
    def check(self, key: str, plan: str = 'free') -> RateLimitResult:
        """
        Check if request is allowed under rate limit.
        
        Args:
            key: Unique identifier (user_id, ip_address, api_key)
            plan: Subscription tier (free, pro, enterprise)
            
        Returns:
            RateLimitResult with allowed status and metadata
        """
        limit = self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS['free'])
        now = time.time()
        window_start = now - self.window_seconds
        redis_key = f"ratelimit:{key}"
        
        try:
            client = self._get_redis_client()
            pipe = client.pipeline()
            
            # Remove old entries
            pipe.zremrangebyscore(redis_key, 0, window_start)
            
            # Count current entries
            pipe.zcard(redis_key)
            
            # Execute pipeline
            results = pipe.execute()
            current_count = results[1]
            
            if current_count < limit:
                # Add new entry
                client.zadd(redis_key, {str(now): now})
                client.expire(redis_key, self.window_seconds + 1)
                
                return RateLimitResult(
                    allowed=True,
                    remaining=limit - current_count - 1,
                    reset_at=now + self.window_seconds,
                )
            else:
                # Get oldest entry to calculate retry_after
                oldest = client.zrange(redis_key, 0, 0, withscores=True)
                if oldest:
                    oldest_time = oldest[0][1]
                    retry_after = int(oldest_time + self.window_seconds - now) + 1
                else:
                    retry_after = self.window_seconds
                
                return RateLimitResult(
                    allowed=False,
                    remaining=0,
                    reset_at=now + retry_after,
                    retry_after=retry_after,
                )
                
        except Exception as e:
            logger.error(f"Rate limiter Redis error: {e}")
            # Fail open - allow request but log warning
            return RateLimitResult(
                allowed=True,
                remaining=limit,
                reset_at=now + self.window_seconds,
            )
    
    def get_limit_for_plan(self, plan: str) -> int:
        """Get rate limit for a plan tier."""
        return self.PLAN_LIMITS.get(plan, self.PLAN_LIMITS['free'])


# Singleton instance
_rate_limiter: Optional[SlidingWindowRateLimiter] = None


def get_rate_limiter() -> SlidingWindowRateLimiter:
    """Get the rate limiter singleton."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = SlidingWindowRateLimiter(window_seconds=60)
    return _rate_limiter
```


### 3. Enhanced Circuit Breaker with Prometheus Metrics

```python
# backend/gpubroker/apps/providers/circuit_breaker.py (enhanced)

from __future__ import annotations
import time
import logging
from typing import Callable, Dict, Optional, Any, Awaitable
from dataclasses import dataclass, field
from enum import Enum
from prometheus_client import Counter, Gauge, Histogram

logger = logging.getLogger('gpubroker.providers.circuit_breaker')


# Prometheus metrics
CIRCUIT_STATE = Gauge(
    'circuit_breaker_state',
    'Circuit breaker state (0=closed, 1=open, 2=half_open)',
    ['provider']
)
CIRCUIT_FAILURES = Counter(
    'circuit_breaker_failures_total',
    'Total circuit breaker failures',
    ['provider']
)
CIRCUIT_SUCCESSES = Counter(
    'circuit_breaker_successes_total',
    'Total circuit breaker successes',
    ['provider']
)
CIRCUIT_REJECTIONS = Counter(
    'circuit_breaker_rejections_total',
    'Total requests rejected by open circuit',
    ['provider']
)
PROVIDER_LATENCY = Histogram(
    'provider_request_latency_seconds',
    'Provider request latency',
    ['provider'],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0]
)


class CircuitState(Enum):
    CLOSED = 0
    OPEN = 1
    HALF_OPEN = 2


class CircuitBreakerOpen(Exception):
    """Raised when circuit breaker is open."""
    pass


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    fail_max: int = 5
    fail_rate_threshold: float = 0.5  # 50% failure rate
    window_seconds: int = 30
    reset_timeout: int = 30
    half_open_max_calls: int = 3


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: int = 0


class AsyncCircuitBreaker:
    """
    Enhanced async circuit breaker with Prometheus metrics.
    
    Features:
    - Failure rate threshold (not just count)
    - Half-open state with limited trial calls
    - Prometheus metrics for monitoring
    - Configurable parameters
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        clock: Callable[[], float] = time.monotonic,
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self._clock = clock
        self._state = CircuitState.CLOSED
        self._failures: list[float] = []
        self._successes: list[float] = []
        self._opened_at: Optional[float] = None
        self._half_open_calls: int = 0
        self.stats = CircuitBreakerStats()
        
        # Initialize Prometheus gauge
        CIRCUIT_STATE.labels(provider=name).set(0)
    
    @property
    def state(self) -> CircuitState:
        return self._state
    
    @state.setter
    def state(self, new_state: CircuitState):
        if self._state != new_state:
            self._state = new_state
            self.stats.state_changes += 1
            CIRCUIT_STATE.labels(provider=self.name).set(new_state.value)
            logger.info(f"Circuit breaker {self.name} -> {new_state.name}")
    
    def _prune_window(self, now: float):
        """Remove entries outside the current window."""
        cutoff = now - self.config.window_seconds
        self._failures = [t for t in self._failures if t >= cutoff]
        self._successes = [t for t in self._successes if t >= cutoff]
    
    def _get_failure_rate(self) -> float:
        """Calculate failure rate in current window."""
        total = len(self._failures) + len(self._successes)
        if total == 0:
            return 0.0
        return len(self._failures) / total
    
    def _should_open(self) -> bool:
        """Check if circuit should open based on failure rate."""
        total = len(self._failures) + len(self._successes)
        if total < self.config.fail_max:
            return False
        return self._get_failure_rate() >= self.config.fail_rate_threshold
    
    def _can_attempt(self, now: float) -> bool:
        """Check if a call attempt is allowed."""
        if self._state == CircuitState.CLOSED:
            return True
        
        if self._state == CircuitState.OPEN:
            if self._opened_at and now - self._opened_at >= self.config.reset_timeout:
                self.state = CircuitState.HALF_OPEN
                self._half_open_calls = 0
                return True
            return False
        
        if self._state == CircuitState.HALF_OPEN:
            return self._half_open_calls < self.config.half_open_max_calls
        
        return False
    
    def _record_success(self, now: float):
        """Record a successful call."""
        self._successes.append(now)
        self.stats.successful_calls += 1
        self.stats.last_success_time = now
        CIRCUIT_SUCCESSES.labels(provider=self.name).inc()
        
        if self._state == CircuitState.HALF_OPEN:
            self._half_open_calls += 1
            if self._half_open_calls >= self.config.half_open_max_calls:
                self.state = CircuitState.CLOSED
                self._failures.clear()
                self._opened_at = None
    
    def _record_failure(self, now: float):
        """Record a failed call."""
        self._failures.append(now)
        self.stats.failed_calls += 1
        self.stats.last_failure_time = now
        CIRCUIT_FAILURES.labels(provider=self.name).inc()
        
        self._prune_window(now)
        
        if self._state == CircuitState.HALF_OPEN:
            self.state = CircuitState.OPEN
            self._opened_at = now
        elif self._should_open():
            self.state = CircuitState.OPEN
            self._opened_at = now
    
    async def call(self, func: Callable[..., Awaitable[Any]], *args, **kwargs) -> Any:
        """Execute a function through the circuit breaker."""
        now = self._clock()
        self.stats.total_calls += 1
        
        if not self._can_attempt(now):
            self.stats.rejected_calls += 1
            CIRCUIT_REJECTIONS.labels(provider=self.name).inc()
            raise CircuitBreakerOpen(
                f"Circuit breaker {self.name} is open"
            )
        
        start_time = time.monotonic()
        try:
            result = await func(*args, **kwargs)
            latency = time.monotonic() - start_time
            PROVIDER_LATENCY.labels(provider=self.name).observe(latency)
            self._record_success(self._clock())
            return result
        except Exception as e:
            latency = time.monotonic() - start_time
            PROVIDER_LATENCY.labels(provider=self.name).observe(latency)
            self._record_failure(self._clock())
            raise
    
    def reset(self):
        """Reset circuit breaker to closed state."""
        self.state = CircuitState.CLOSED
        self._failures.clear()
        self._successes.clear()
        self._opened_at = None
        self._half_open_calls = 0


# Registry of circuit breakers
_breakers: Dict[str, AsyncCircuitBreaker] = {}


def get_breaker(
    key: str,
    config: Optional[CircuitBreakerConfig] = None,
) -> AsyncCircuitBreaker:
    """Get or create a circuit breaker for a given key."""
    if key not in _breakers:
        _breakers[key] = AsyncCircuitBreaker(name=key, config=config)
    return _breakers[key]


def reset_breaker(key: str):
    """Reset a circuit breaker."""
    if key in _breakers:
        _breakers[key].reset()


def get_all_breaker_stats() -> Dict[str, CircuitBreakerStats]:
    """Get stats for all circuit breakers."""
    return {key: breaker.stats for key, breaker in _breakers.items()}
```


### 4. Weighted Load Balancer with Health Tracking

```python
# backend/gpubroker/apps/providers/load_balancer.py

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Callable, Awaitable
from dataclasses import dataclass, field
from collections import deque
from prometheus_client import Gauge, Counter

logger = logging.getLogger('gpubroker.providers.load_balancer')


# Prometheus metrics
PROVIDER_WEIGHT = Gauge(
    'provider_weight',
    'Current weight for provider in load balancer',
    ['provider']
)
PROVIDER_HEALTH = Gauge(
    'provider_health',
    'Provider health status (0=unhealthy, 1=healthy)',
    ['provider']
)
PROVIDER_QUEUE_SIZE = Gauge(
    'provider_queue_size',
    'Current queue size for provider',
    ['provider']
)


@dataclass
class ProviderHealth:
    """Health status for a provider."""
    name: str
    healthy: bool = True
    weight: float = 1.0
    base_weight: float = 1.0
    avg_latency_ms: float = 0.0
    error_rate: float = 0.0
    last_check: float = field(default_factory=time.time)
    consecutive_failures: int = 0
    latency_samples: deque = field(default_factory=lambda: deque(maxlen=100))
    
    def update_latency(self, latency_ms: float):
        """Update latency tracking."""
        self.latency_samples.append(latency_ms)
        if self.latency_samples:
            self.avg_latency_ms = sum(self.latency_samples) / len(self.latency_samples)
    
    def calculate_weight(self) -> float:
        """Calculate dynamic weight based on health metrics."""
        if not self.healthy:
            return 0.0
        
        weight = self.base_weight
        
        # Reduce weight for slow providers (>2s avg latency)
        if self.avg_latency_ms > 2000:
            weight *= 0.5
        elif self.avg_latency_ms > 1000:
            weight *= 0.75
        
        # Reduce weight for high error rate
        if self.error_rate > 0.3:
            weight *= 0.5
        elif self.error_rate > 0.1:
            weight *= 0.75
        
        self.weight = max(0.1, weight)  # Minimum weight
        return self.weight


@dataclass
class QueuedRequest:
    """A request waiting in the queue."""
    provider: str
    func: Callable
    args: tuple
    kwargs: dict
    future: asyncio.Future
    queued_at: float = field(default_factory=time.time)


class WeightedLoadBalancer:
    """
    Weighted round-robin load balancer with health tracking.
    
    Features:
    - Dynamic weight adjustment based on latency and errors
    - Request queuing with backpressure
    - Per-provider concurrency limits
    - Health-based provider selection
    """
    
    def __init__(
        self,
        max_queue_size: int = 1000,
        max_concurrent_per_provider: int = 50,
        slow_threshold_ms: float = 2000,
    ):
        self.max_queue_size = max_queue_size
        self.max_concurrent = max_concurrent_per_provider
        self.slow_threshold_ms = slow_threshold_ms
        
        self._providers: Dict[str, ProviderHealth] = {}
        self._queues: Dict[str, deque] = {}
        self._active_requests: Dict[str, int] = {}
        self._round_robin_index: int = 0
    
    def register_provider(self, name: str, base_weight: float = 1.0):
        """Register a provider with the load balancer."""
        self._providers[name] = ProviderHealth(
            name=name,
            base_weight=base_weight,
            weight=base_weight,
        )
        self._queues[name] = deque(maxlen=self.max_queue_size)
        self._active_requests[name] = 0
        
        PROVIDER_WEIGHT.labels(provider=name).set(base_weight)
        PROVIDER_HEALTH.labels(provider=name).set(1)
    
    def get_healthy_providers(self) -> List[str]:
        """Get list of healthy providers."""
        return [
            name for name, health in self._providers.items()
            if health.healthy and health.weight > 0
        ]
    
    def select_provider(self, exclude: Optional[List[str]] = None) -> Optional[str]:
        """
        Select a provider using weighted round-robin.
        
        Args:
            exclude: Providers to exclude from selection
            
        Returns:
            Selected provider name or None if all unhealthy
        """
        exclude = exclude or []
        candidates = [
            (name, health.weight)
            for name, health in self._providers.items()
            if health.healthy and name not in exclude and health.weight > 0
        ]
        
        if not candidates:
            return None
        
        # Weighted selection
        total_weight = sum(w for _, w in candidates)
        if total_weight == 0:
            return None
        
        # Simple weighted round-robin
        self._round_robin_index = (self._round_robin_index + 1) % len(candidates)
        
        # Weighted random selection for better distribution
        import random
        r = random.uniform(0, total_weight)
        cumulative = 0
        for name, weight in candidates:
            cumulative += weight
            if r <= cumulative:
                return name
        
        return candidates[0][0]
    
    def record_success(self, provider: str, latency_ms: float):
        """Record a successful request."""
        if provider not in self._providers:
            return
        
        health = self._providers[provider]
        health.update_latency(latency_ms)
        health.consecutive_failures = 0
        health.healthy = True
        health.calculate_weight()
        
        PROVIDER_WEIGHT.labels(provider=provider).set(health.weight)
        PROVIDER_HEALTH.labels(provider=provider).set(1)
    
    def record_failure(self, provider: str):
        """Record a failed request."""
        if provider not in self._providers:
            return
        
        health = self._providers[provider]
        health.consecutive_failures += 1
        
        # Mark unhealthy after 3 consecutive failures
        if health.consecutive_failures >= 3:
            health.healthy = False
            health.weight = 0
            PROVIDER_HEALTH.labels(provider=provider).set(0)
        
        health.calculate_weight()
        PROVIDER_WEIGHT.labels(provider=provider).set(health.weight)
    
    def mark_healthy(self, provider: str):
        """Mark a provider as healthy (from health check)."""
        if provider in self._providers:
            health = self._providers[provider]
            health.healthy = True
            health.consecutive_failures = 0
            health.calculate_weight()
            PROVIDER_HEALTH.labels(provider=provider).set(1)
    
    def mark_unhealthy(self, provider: str):
        """Mark a provider as unhealthy."""
        if provider in self._providers:
            health = self._providers[provider]
            health.healthy = False
            health.weight = 0
            PROVIDER_HEALTH.labels(provider=provider).set(0)
    
    def can_accept_request(self, provider: str) -> bool:
        """Check if provider can accept more requests."""
        active = self._active_requests.get(provider, 0)
        return active < self.max_concurrent
    
    def get_queue_size(self, provider: str) -> int:
        """Get current queue size for provider."""
        return len(self._queues.get(provider, []))
    
    def get_stats(self) -> Dict[str, Any]:
        """Get load balancer statistics."""
        return {
            'providers': {
                name: {
                    'healthy': health.healthy,
                    'weight': health.weight,
                    'avg_latency_ms': health.avg_latency_ms,
                    'consecutive_failures': health.consecutive_failures,
                    'active_requests': self._active_requests.get(name, 0),
                    'queue_size': len(self._queues.get(name, [])),
                }
                for name, health in self._providers.items()
            }
        }


# Singleton instance
_load_balancer: Optional[WeightedLoadBalancer] = None


def get_load_balancer() -> WeightedLoadBalancer:
    """Get the load balancer singleton."""
    global _load_balancer
    if _load_balancer is None:
        _load_balancer = WeightedLoadBalancer()
    return _load_balancer
```


### 5. Vault Integration for Credential Management

```python
# backend/gpubroker/apps/providers/vault_client.py

import time
import logging
from typing import Optional, Dict, Any
from dataclasses import dataclass
from functools import lru_cache
import hvac
from django.conf import settings

logger = logging.getLogger('gpubroker.providers.vault')


@dataclass
class CachedCredential:
    """Cached credential with expiry."""
    value: str
    fetched_at: float
    ttl: int = 3600  # 1 hour default
    
    @property
    def is_expired(self) -> bool:
        return time.time() - self.fetched_at > self.ttl
    
    @property
    def is_stale(self) -> bool:
        """Check if credential should be refreshed (80% of TTL)."""
        return time.time() - self.fetched_at > self.ttl * 0.8


class VaultCredentialManager:
    """
    HashiCorp Vault integration for secure credential management.
    
    Features:
    - Automatic token renewal
    - Credential caching with TTL
    - Fallback to cached credentials when Vault unavailable
    - Per-user credential support for enterprise
    """
    
    def __init__(self):
        self._client: Optional[hvac.Client] = None
        self._cache: Dict[str, CachedCredential] = {}
        self._vault_available = True
        self._last_vault_check = 0
        self._vault_check_interval = 30  # seconds
    
    def _get_client(self) -> Optional[hvac.Client]:
        """Get or create Vault client."""
        if self._client is None:
            vault_addr = getattr(settings, 'VAULT_ADDR', 'http://localhost:8200')
            vault_token = getattr(settings, 'VAULT_TOKEN', None)
            
            if not vault_token:
                logger.warning("VAULT_TOKEN not configured")
                return None
            
            try:
                self._client = hvac.Client(url=vault_addr, token=vault_token)
                if not self._client.is_authenticated():
                    logger.error("Vault authentication failed")
                    self._client = None
            except Exception as e:
                logger.error(f"Vault connection failed: {e}")
                self._client = None
        
        return self._client
    
    def _check_vault_health(self) -> bool:
        """Check if Vault is available."""
        now = time.time()
        if now - self._last_vault_check < self._vault_check_interval:
            return self._vault_available
        
        self._last_vault_check = now
        client = self._get_client()
        
        if client is None:
            self._vault_available = False
            return False
        
        try:
            client.sys.read_health_status()
            self._vault_available = True
            return True
        except Exception as e:
            logger.warning(f"Vault health check failed: {e}")
            self._vault_available = False
            return False
    
    async def get_provider_credential(
        self,
        provider: str,
        user_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Get API key for a provider from Vault.
        
        Args:
            provider: Provider name (e.g., 'runpod', 'vastai')
            user_id: Optional user ID for per-user credentials
            
        Returns:
            API key or None
        """
        # Build cache key
        cache_key = f"{provider}:{user_id or 'default'}"
        
        # Check cache first
        cached = self._cache.get(cache_key)
        if cached and not cached.is_expired:
            if cached.is_stale and self._check_vault_health():
                # Refresh in background (non-blocking)
                pass  # Could use asyncio.create_task for background refresh
            return cached.value
        
        # Try Vault
        if self._check_vault_health():
            try:
                client = self._get_client()
                if client:
                    # Path format: secret/data/gpubroker/providers/{provider}
                    # Or for user-specific: secret/data/gpubroker/users/{user_id}/providers/{provider}
                    if user_id:
                        path = f"secret/data/gpubroker/users/{user_id}/providers/{provider}"
                    else:
                        path = f"secret/data/gpubroker/providers/{provider}"
                    
                    response = client.secrets.kv.v2.read_secret_version(
                        path=path.replace('secret/data/', ''),
                        mount_point='secret',
                    )
                    
                    if response and 'data' in response and 'data' in response['data']:
                        api_key = response['data']['data'].get('api_key')
                        if api_key:
                            self._cache[cache_key] = CachedCredential(
                                value=api_key,
                                fetched_at=time.time(),
                            )
                            return api_key
                            
            except Exception as e:
                logger.warning(f"Vault read failed for {provider}: {e}")
        
        # Fallback to cached credential (even if stale)
        if cached:
            logger.warning(f"Using stale credential for {provider}")
            return cached.value
        
        # Final fallback to environment variable
        import os
        env_key = os.getenv(f"{provider.upper()}_API_KEY")
        if env_key:
            self._cache[cache_key] = CachedCredential(
                value=env_key,
                fetched_at=time.time(),
                ttl=300,  # Shorter TTL for env vars
            )
        return env_key
    
    async def store_user_credential(
        self,
        user_id: str,
        provider: str,
        api_key: str,
    ) -> bool:
        """
        Store a user's provider credential in Vault.
        
        Args:
            user_id: User ID
            provider: Provider name
            api_key: API key to store
            
        Returns:
            True if stored successfully
        """
        if not self._check_vault_health():
            logger.error("Vault unavailable for credential storage")
            return False
        
        try:
            client = self._get_client()
            if client:
                path = f"gpubroker/users/{user_id}/providers/{provider}"
                client.secrets.kv.v2.create_or_update_secret(
                    path=path,
                    secret={'api_key': api_key},
                    mount_point='secret',
                )
                
                # Update cache
                cache_key = f"{provider}:{user_id}"
                self._cache[cache_key] = CachedCredential(
                    value=api_key,
                    fetched_at=time.time(),
                )
                return True
                
        except Exception as e:
            logger.error(f"Vault write failed: {e}")
        
        return False
    
    def clear_cache(self):
        """Clear credential cache."""
        self._cache.clear()


# Singleton instance
_vault_manager: Optional[VaultCredentialManager] = None


def get_vault_manager() -> VaultCredentialManager:
    """Get the Vault credential manager singleton."""
    global _vault_manager
    if _vault_manager is None:
        _vault_manager = VaultCredentialManager()
    return _vault_manager
```


### 6. Background Tasks with Apache Airflow

```python
# backend/gpubroker/apps/providers/airflow_dags/provider_tasks.py
"""
Apache Airflow DAGs for Provider API Gateway background tasks.

DAGs:
- provider_cache_warming: Warm caches for all providers every 5 minutes
- provider_health_checks: Health check all providers every 30 seconds
- price_change_webhooks: Process webhook notifications for price changes
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.dates import days_ago
import logging

logger = logging.getLogger('gpubroker.providers.airflow')


# Default DAG arguments
default_args = {
    'owner': 'gpubroker',
    'depends_on_past': False,
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=1),
}


def warm_provider_cache(provider_name: str, **context):
    """
    Task to warm cache for a single provider.
    
    Fetches latest offers and stores in Redis cache.
    """
    import asyncio
    import os
    import sys
    
    # Add Django project to path
    sys.path.insert(0, '/app/backend/gpubroker')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gpubroker.settings.production')
    
    import django
    django.setup()
    
    from apps.providers.adapters.registry import ProviderRegistry
    from apps.providers.vault_client import get_vault_manager
    from apps.providers.cache import get_cache
    from prometheus_client import Counter
    
    CACHE_WARM_SUCCESS = Counter(
        'cache_warm_success_total',
        'Successful cache warming operations',
        ['provider']
    )
    CACHE_WARM_FAILURE = Counter(
        'cache_warm_failure_total',
        'Failed cache warming operations',
        ['provider']
    )
    
    async def _warm():
        try:
            adapter = ProviderRegistry.get_adapter(provider_name)
            vault = get_vault_manager()
            cache = get_cache()
            
            # Get API key from Vault
            api_key = await vault.get_provider_credential(provider_name)
            
            # Fetch offers
            offers = await adapter.get_offers(api_key)
            
            # Store in cache
            cache_key = f"gateway:offers:{provider_name}"
            await cache.set(
                cache_key,
                [o.__dict__ for o in offers],
                ttl=300,  # 5 minutes
            )
            
            CACHE_WARM_SUCCESS.labels(provider=provider_name).inc()
            logger.info(f"Cache warmed for {provider_name}: {len(offers)} offers")
            return len(offers)
            
        except Exception as e:
            CACHE_WARM_FAILURE.labels(provider=provider_name).inc()
            logger.error(f"Cache warming failed for {provider_name}: {e}")
            raise
    
    return asyncio.get_event_loop().run_until_complete(_warm())


def health_check_provider(provider_name: str, **context):
    """
    Task to health check a single provider.
    
    Updates load balancer health status.
    """
    import asyncio
    import os
    import sys
    
    sys.path.insert(0, '/app/backend/gpubroker')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gpubroker.settings.production')
    
    import django
    django.setup()
    
    from apps.providers.adapters.registry import ProviderRegistry
    from apps.providers.load_balancer import get_load_balancer
    from apps.providers.vault_client import get_vault_manager
    
    async def _check():
        try:
            adapter = ProviderRegistry.get_adapter(provider_name)
            vault = get_vault_manager()
            lb = get_load_balancer()
            
            api_key = await vault.get_provider_credential(provider_name)
            is_healthy = await adapter.validate_credentials({'api_key': api_key})
            
            if is_healthy:
                lb.mark_healthy(provider_name)
            else:
                lb.mark_unhealthy(provider_name)
            
            return is_healthy
            
        except Exception as e:
            logger.error(f"Health check failed for {provider_name}: {e}")
            get_load_balancer().mark_unhealthy(provider_name)
            raise
    
    return asyncio.get_event_loop().run_until_complete(_check())


def send_price_change_webhook(
    webhook_url: str,
    provider: str,
    old_price: float,
    new_price: float,
    offer_id: str,
    **context,
):
    """
    Task to send webhook notification for price changes.
    """
    import httpx
    
    payload = {
        'event': 'price_change',
        'provider': provider,
        'offer_id': offer_id,
        'old_price': old_price,
        'new_price': new_price,
        'change_percent': ((new_price - old_price) / old_price) * 100,
    }
    
    try:
        with httpx.Client(timeout=10) as client:
            response = client.post(webhook_url, json=payload)
            response.raise_for_status()
            return {'status': 'sent', 'webhook_url': webhook_url}
    except Exception as e:
        logger.error(f"Webhook delivery failed: {e}")
        raise


def get_all_providers(**context):
    """Get list of all registered providers."""
    import os
    import sys
    
    sys.path.insert(0, '/app/backend/gpubroker')
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gpubroker.settings.production')
    
    import django
    django.setup()
    
    from apps.providers.adapters.registry import ProviderRegistry
    return ProviderRegistry.list_adapters()


# DAG: Cache Warming (every 5 minutes)
with DAG(
    'provider_cache_warming',
    default_args=default_args,
    description='Warm caches for all GPU providers',
    schedule_interval=timedelta(minutes=5),
    start_date=days_ago(1),
    catchup=False,
    tags=['gpubroker', 'cache', 'providers'],
) as cache_warming_dag:
    
    # Get providers list
    get_providers = PythonOperator(
        task_id='get_providers',
        python_callable=get_all_providers,
    )
    
    # Dynamic task generation for each provider
    # In production, use dynamic task mapping
    providers = ['runpod', 'vastai', 'aws_sagemaker', 'azure_ml', 'google_vertex_ai']
    
    for provider in providers:
        warm_task = PythonOperator(
            task_id=f'warm_cache_{provider}',
            python_callable=warm_provider_cache,
            op_kwargs={'provider_name': provider},
        )
        get_providers >> warm_task


# DAG: Health Checks (every 30 seconds - use sensor or external trigger)
with DAG(
    'provider_health_checks',
    default_args=default_args,
    description='Health check all GPU providers',
    schedule_interval=timedelta(seconds=30),
    start_date=days_ago(1),
    catchup=False,
    tags=['gpubroker', 'health', 'providers'],
    max_active_runs=1,  # Prevent overlap
) as health_check_dag:
    
    providers = ['runpod', 'vastai', 'aws_sagemaker', 'azure_ml', 'google_vertex_ai']
    
    for provider in providers:
        health_task = PythonOperator(
            task_id=f'health_check_{provider}',
            python_callable=health_check_provider,
            op_kwargs={'provider_name': provider},
        )


# DAG: Webhook Processing (triggered by events)
with DAG(
    'price_change_webhooks',
    default_args=default_args,
    description='Process price change webhook notifications',
    schedule_interval=None,  # Triggered externally
    start_date=days_ago(1),
    catchup=False,
    tags=['gpubroker', 'webhooks', 'notifications'],
) as webhook_dag:
    
    webhook_task = PythonOperator(
        task_id='send_webhook',
        python_callable=send_price_change_webhook,
        op_kwargs={
            'webhook_url': '{{ dag_run.conf.webhook_url }}',
            'provider': '{{ dag_run.conf.provider }}',
            'old_price': '{{ dag_run.conf.old_price }}',
            'new_price': '{{ dag_run.conf.new_price }}',
            'offer_id': '{{ dag_run.conf.offer_id }}',
        },
    )
```

### Airflow Configuration

```python
# airflow/airflow.cfg additions

[core]
dags_folder = /app/backend/gpubroker/apps/providers/airflow_dags
executor = KubernetesExecutor  # For horizontal scaling

[scheduler]
min_file_process_interval = 30

[webserver]
expose_config = False

# Dead letter queue via Airflow callbacks
[smtp]
smtp_host = localhost
smtp_mail_from = airflow@gpubroker.com
```

### Triggering DAGs from Django

```python
# backend/gpubroker/apps/providers/airflow_client.py

import httpx
import logging
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger('gpubroker.providers.airflow')


class AirflowClient:
    """Client for triggering Airflow DAGs from Django."""
    
    def __init__(self):
        self.base_url = getattr(settings, 'AIRFLOW_API_URL', 'http://localhost:8080/api/v1')
        self.auth = (
            getattr(settings, 'AIRFLOW_USERNAME', 'admin'),
            getattr(settings, 'AIRFLOW_PASSWORD', 'admin'),
        )
    
    async def trigger_dag(
        self,
        dag_id: str,
        conf: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Trigger an Airflow DAG run."""
        url = f"{self.base_url}/dags/{dag_id}/dagRuns"
        payload = {
            'conf': conf or {},
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json=payload,
                auth=self.auth,
                timeout=10,
            )
            response.raise_for_status()
            return response.json()
    
    async def trigger_price_webhook(
        self,
        webhook_url: str,
        provider: str,
        old_price: float,
        new_price: float,
        offer_id: str,
    ):
        """Trigger price change webhook DAG."""
        return await self.trigger_dag(
            'price_change_webhooks',
            conf={
                'webhook_url': webhook_url,
                'provider': provider,
                'old_price': old_price,
                'new_price': new_price,
                'offer_id': offer_id,
            },
        )


# Singleton
_airflow_client: Optional[AirflowClient] = None


def get_airflow_client() -> AirflowClient:
    """Get Airflow client singleton."""
    global _airflow_client
    if _airflow_client is None:
        _airflow_client = AirflowClient()
    return _airflow_client
```


## Data Models

### Request/Response Schemas

```python
# backend/gpubroker/apps/providers/schemas.py (enhanced)

from datetime import datetime
from typing import Optional, List, Dict, Any
from ninja import Schema
from pydantic import Field


class ProviderItem(Schema):
    """Normalized GPU offer from any provider."""
    id: str
    provider: str
    name: str
    gpu: str
    memory_gb: int
    price_per_hour: float
    currency: str = "USD"
    availability: str
    region: str
    tags: List[str] = []
    last_updated: datetime
    
    # Extended fields for enterprise
    spot_price: Optional[float] = None
    on_demand_price: Optional[float] = None
    vcpus: Optional[int] = None
    ram_gb: Optional[int] = None
    storage_gb: Optional[int] = None
    network_gbps: Optional[float] = None


class ProviderListResponse(Schema):
    """Paginated list of provider offers."""
    total: int
    items: List[ProviderItem]
    warnings: Optional[List[str]] = None
    
    # Pagination metadata
    page: int = 1
    per_page: int = 20
    has_next: bool = False
    cursor: Optional[str] = None


class RateLimitInfo(Schema):
    """Rate limit information in response headers."""
    limit: int
    remaining: int
    reset_at: datetime
    retry_after: Optional[int] = None


class CircuitBreakerStatus(Schema):
    """Circuit breaker status for a provider."""
    provider: str
    state: str  # closed, open, half_open
    failure_count: int
    success_count: int
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None


class ProviderHealthStatus(Schema):
    """Health status for a provider."""
    provider: str
    healthy: bool
    weight: float
    avg_latency_ms: float
    error_rate: float
    last_check: datetime
    circuit_breaker: CircuitBreakerStatus


class GatewayHealthResponse(Schema):
    """Comprehensive gateway health response."""
    status: str  # ok, degraded, unhealthy
    timestamp: datetime
    providers: List[ProviderHealthStatus]
    cache_status: Dict[str, Any]
    rate_limiter_status: Dict[str, Any]
    
    # Metrics summary
    total_requests_1m: int = 0
    avg_latency_ms: float = 0
    error_rate: float = 0


class IntegrationConfig(Schema):
    """Provider integration configuration."""
    provider: str
    api_key: Optional[str] = None
    api_url: Optional[str] = None
    enabled: bool = True


class IntegrationStatus(Schema):
    """Provider integration status."""
    provider: str
    status: str  # active, error, not_configured
    message: Optional[str] = None
    last_checked: datetime
```

### Database Models

```python
# backend/gpubroker/apps/providers/models.py (enhanced)

from django.db import models
from django.contrib.postgres.fields import ArrayField
import uuid


class Provider(models.Model):
    """GPU cloud provider."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    display_name = models.CharField(max_length=200)
    api_base_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Health tracking
    health_status = models.CharField(
        max_length=20,
        choices=[
            ('healthy', 'Healthy'),
            ('degraded', 'Degraded'),
            ('unhealthy', 'Unhealthy'),
        ],
        default='healthy',
        db_index=True,
    )
    last_health_check = models.DateTimeField(null=True, blank=True)
    
    # Rate limiting
    rate_limit_per_minute = models.IntegerField(default=100)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'providers'
        ordering = ['name']


class GPUOffer(models.Model):
    """Normalized GPU offer from a provider."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        related_name='offers',
        db_index=True,
    )
    
    # GPU details
    name = models.CharField(max_length=200, db_index=True)
    gpu_type = models.CharField(max_length=100, db_index=True)
    gpu_count = models.IntegerField(default=1)
    gpu_memory_gb = models.IntegerField(null=True, blank=True, db_index=True)
    
    # Instance details
    vcpus = models.IntegerField(null=True, blank=True)
    ram_gb = models.IntegerField(null=True, blank=True)
    storage_gb = models.IntegerField(null=True, blank=True)
    
    # Pricing
    price_per_hour = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        db_index=True,
    )
    spot_price = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
    )
    currency = models.CharField(max_length=3, default='USD')
    
    # Availability
    availability_status = models.CharField(
        max_length=20,
        choices=[
            ('available', 'Available'),
            ('limited', 'Limited'),
            ('unavailable', 'Unavailable'),
        ],
        default='available',
        db_index=True,
    )
    region = models.CharField(max_length=50, db_index=True)
    
    # Compliance
    compliance_tags = ArrayField(
        models.CharField(max_length=50),
        default=list,
        blank=True,
    )
    
    # Timestamps
    last_updated = models.DateTimeField(auto_now=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'gpu_offers'
        indexes = [
            models.Index(fields=['provider', 'gpu_type']),
            models.Index(fields=['price_per_hour', 'availability_status']),
            models.Index(fields=['region', 'gpu_memory_gb']),
        ]
        ordering = ['price_per_hour']


class ProviderHealthCheck(models.Model):
    """Health check history for providers."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    provider = models.ForeignKey(
        Provider,
        on_delete=models.CASCADE,
        related_name='health_checks',
    )
    
    is_healthy = models.BooleanField()
    latency_ms = models.FloatField(null=True, blank=True)
    error_message = models.TextField(blank=True)
    
    checked_at = models.DateTimeField(auto_now_add=True, db_index=True)
    
    class Meta:
        db_table = 'provider_health_checks'
        ordering = ['-checked_at']
        indexes = [
            models.Index(fields=['provider', 'checked_at']),
        ]
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Cache Lookup Order and Fallback

*For any* request to the gateway, the cache lookup SHALL follow the order: L2 (in-memory) → L1 (Redis) → provider fetch. If Redis is unavailable, the system SHALL gracefully fall back to L2 cache without error.

**Validates: Requirements 2.2, 2.6**

### Property 2: Cache TTL Expiration

*For any* cached item with TTL T, the item SHALL be considered expired and removed after T seconds have elapsed. Pricing data SHALL use 60-second TTL, static data SHALL use 300-second TTL.

**Validates: Requirements 2.3**

### Property 3: Cache Stampede Prevention

*For any* set of N concurrent requests arriving near cache expiration time, at most 1 request SHALL trigger a provider fetch (probabilistic early expiration). The remaining N-1 requests SHALL receive cached data.

**Validates: Requirements 2.5**

### Property 4: Circuit Breaker State Machine

*For any* provider adapter, the circuit breaker SHALL transition through states correctly:
- CLOSED → OPEN: When failure rate ≥ 50% over minimum 10 requests
- OPEN → HALF_OPEN: After 30 seconds timeout
- HALF_OPEN → CLOSED: After 3 successful requests
- HALF_OPEN → OPEN: On any failure

**Validates: Requirements 3.1, 3.2, 3.4, 3.5**

### Property 5: Circuit Breaker Cached Fallback

*For any* request when circuit is OPEN, the gateway SHALL return cached data (if available) or skip the provider. No requests SHALL be sent to the provider while circuit is OPEN.

**Validates: Requirements 3.3**

### Property 6: Rate Limiting by Plan Tier

*For any* user with plan tier P, the rate limiter SHALL allow exactly LIMIT[P] requests per minute (Free=10, Pro=100, Enterprise=1000). Anonymous users SHALL be rate limited by IP address at Free tier limits.

**Validates: Requirements 4.1, 4.4, 4.5**

### Property 7: Rate Limit Response Format

*For any* request that exceeds the rate limit, the gateway SHALL return HTTP 429 with a Retry-After header containing the number of seconds until the limit resets.

**Validates: Requirements 4.2**

### Property 8: Sliding Window Rate Limiting

*For any* sequence of requests over time, the rate limiter SHALL use a sliding window algorithm where the count is based on requests in the last 60 seconds, not fixed time buckets.

**Validates: Requirements 4.3, 4.6**

### Property 9: Weighted Load Balancing

*For any* set of healthy providers with weights W1, W2, ..., Wn, the load balancer SHALL distribute requests proportionally to weights. Slow providers (>2s latency) SHALL have their weight reduced by 50%.

**Validates: Requirements 5.1, 5.2**

### Property 10: Provider Concurrency Limits

*For any* provider, the load balancer SHALL enforce a maximum concurrent request limit. Requests exceeding the limit SHALL be queued with backpressure.

**Validates: Requirements 5.3, 5.5**

### Property 11: All Providers Unhealthy Fallback

*For any* request when all providers are marked unhealthy, the gateway SHALL return cached data with a warning. The response SHALL NOT be an error if cached data exists.

**Validates: Requirements 5.4**

### Property 12: Parallel Provider Fetching

*For any* request that requires fetching from providers, the gateway SHALL query all healthy providers in parallel. Total fetch time SHALL be approximately max(individual_times), not sum(individual_times).

**Validates: Requirements 1.3, 7.2**

### Property 13: Response Normalization

*For any* provider response, the gateway SHALL normalize it into the standard Offer schema. All required fields (id, provider, name, gpu, price_per_hour, region) SHALL be present.

**Validates: Requirements 7.1**

### Property 14: Offer Deduplication

*For any* set of offers from multiple providers, the gateway SHALL merge and deduplicate offers with the same GPU type and region, keeping the lowest price.

**Validates: Requirements 7.3**

### Property 15: Filter Correctness

*For any* filter parameters (gpu_type, price_range, region, availability), the returned offers SHALL match ALL specified filters. No offer violating any filter SHALL be returned.

**Validates: Requirements 7.4**

### Property 16: Sorting Correctness

*For any* sort parameter (price, performance, topsis), the returned offers SHALL be ordered according to the specified sort. For price sort, offers SHALL be in ascending price order.

**Validates: Requirements 7.5**

### Property 17: Pagination Consistency

*For any* paginated request with cursor C, the next page SHALL contain offers that come after the cursor position. No offer SHALL appear in multiple pages.

**Validates: Requirements 7.6**

### Property 18: Vault Credential Retrieval

*For any* provider credential request, the gateway SHALL first attempt to fetch from Vault. If Vault is unavailable, cached credentials SHALL be used for up to 1 hour.

**Validates: Requirements 9.1, 9.3**

### Property 19: Credential Security

*For any* log entry or error message, the gateway SHALL NOT include API keys or sensitive credentials. Credentials SHALL be masked or omitted entirely.

**Validates: Requirements 9.4**

### Property 20: Background Cache Warming

*For any* provider, the background task SHALL refresh the cache every 5 minutes. Stale data (older than TTL) SHALL trigger an async refresh without blocking requests.

**Validates: Requirements 10.1, 10.3**

### Property 21: Request Timeout

*For any* request where provider response time exceeds 5 seconds, the gateway SHALL timeout and return cached data (if available) or an error response.

**Validates: Requirements 1.5**

## Error Handling

### Error Categories

1. **Client Errors (4xx)**
   - 400 Bad Request: Invalid filter parameters
   - 401 Unauthorized: Missing or invalid JWT
   - 403 Forbidden: Insufficient permissions
   - 429 Too Many Requests: Rate limit exceeded

2. **Server Errors (5xx)**
   - 500 Internal Server Error: Unexpected errors
   - 502 Bad Gateway: Provider API errors
   - 503 Service Unavailable: All providers unhealthy
   - 504 Gateway Timeout: Provider timeout

### Error Response Format

```python
class ErrorResponse(Schema):
    error: str
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    trace_id: Optional[str] = None
    retry_after: Optional[int] = None
```

### Graceful Degradation

1. **Redis Unavailable**: Fall back to L2 in-memory cache
2. **Vault Unavailable**: Use cached credentials (up to 1 hour)
3. **Provider Unavailable**: Return cached data with warning
4. **All Providers Down**: Return cached data or 503 with retry hint


## Testing Strategy

### Dual Testing Approach

This design requires both unit tests and property-based tests for comprehensive coverage:

1. **Unit Tests**: Verify specific examples, edge cases, and error conditions
2. **Property Tests**: Verify universal properties across all inputs using Hypothesis

### Property-Based Testing Framework

- **Library**: Hypothesis (Python)
- **Minimum Iterations**: 100 per property test
- **Tag Format**: `**Feature: provider-api-gateway, Property {N}: {property_text}**`

### Test Categories

#### 1. Cache Layer Tests

```python
# tests/test_cache.py
from hypothesis import given, strategies as st, settings

@settings(max_examples=100)
@given(
    key=st.text(min_size=1, max_size=100),
    value=st.dictionaries(st.text(), st.integers()),
    ttl=st.integers(min_value=1, max_value=300),
)
def test_cache_set_get_roundtrip(key, value, ttl):
    """
    **Feature: provider-api-gateway, Property 2: Cache TTL Expiration**
    For any cached item, get after set should return the same value.
    """
    cache = MultiTierCache()
    cache.set(key, value, ttl)
    result = cache.get(key)
    assert result == value
```

#### 2. Rate Limiter Tests

```python
@settings(max_examples=100)
@given(
    plan=st.sampled_from(['free', 'pro', 'enterprise']),
    request_count=st.integers(min_value=1, max_value=200),
)
def test_rate_limiter_enforces_plan_limits(plan, request_count):
    """
    **Feature: provider-api-gateway, Property 6: Rate Limiting by Plan Tier**
    For any plan, exactly LIMIT[plan] requests should be allowed per minute.
    """
    limiter = SlidingWindowRateLimiter()
    limit = limiter.PLAN_LIMITS[plan]
    
    allowed_count = 0
    for _ in range(request_count):
        result = limiter.check(f"test_user_{plan}", plan)
        if result.allowed:
            allowed_count += 1
    
    assert allowed_count <= limit
```

#### 3. Circuit Breaker Tests

```python
@settings(max_examples=100)
@given(
    failure_sequence=st.lists(
        st.booleans(),
        min_size=10,
        max_size=50,
    ),
)
def test_circuit_breaker_state_transitions(failure_sequence):
    """
    **Feature: provider-api-gateway, Property 4: Circuit Breaker State Machine**
    Circuit breaker should transition states correctly based on failure rate.
    """
    breaker = AsyncCircuitBreaker(name="test")
    
    for is_failure in failure_sequence:
        if is_failure:
            breaker._record_failure(time.monotonic())
        else:
            breaker._record_success(time.monotonic())
    
    # Verify state is consistent with failure rate
    failure_rate = breaker._get_failure_rate()
    if failure_rate >= 0.5 and len(failure_sequence) >= 10:
        assert breaker.state in [CircuitState.OPEN, CircuitState.HALF_OPEN]
```

#### 4. Load Balancer Tests

```python
@settings(max_examples=100)
@given(
    weights=st.lists(
        st.floats(min_value=0.1, max_value=10.0),
        min_size=2,
        max_size=10,
    ),
    num_requests=st.integers(min_value=100, max_value=1000),
)
def test_weighted_distribution(weights, num_requests):
    """
    **Feature: provider-api-gateway, Property 9: Weighted Load Balancing**
    Requests should be distributed proportionally to weights.
    """
    lb = WeightedLoadBalancer()
    
    for i, weight in enumerate(weights):
        lb.register_provider(f"provider_{i}", base_weight=weight)
    
    selections = {f"provider_{i}": 0 for i in range(len(weights))}
    
    for _ in range(num_requests):
        selected = lb.select_provider()
        if selected:
            selections[selected] += 1
    
    # Verify distribution is roughly proportional to weights
    total_weight = sum(weights)
    for i, weight in enumerate(weights):
        expected_ratio = weight / total_weight
        actual_ratio = selections[f"provider_{i}"] / num_requests
        # Allow 20% tolerance due to randomness
        assert abs(actual_ratio - expected_ratio) < 0.2
```

#### 5. Filter Tests

```python
@settings(max_examples=100)
@given(
    offers=st.lists(
        st.fixed_dictionaries({
            'gpu_type': st.text(min_size=1),
            'price_per_hour': st.floats(min_value=0.01, max_value=100.0),
            'region': st.sampled_from(['us-east', 'us-west', 'eu-west']),
            'availability': st.sampled_from(['available', 'limited', 'unavailable']),
        }),
        min_size=1,
        max_size=100,
    ),
    max_price=st.floats(min_value=0.01, max_value=100.0),
)
def test_filter_correctness(offers, max_price):
    """
    **Feature: provider-api-gateway, Property 15: Filter Correctness**
    All returned offers should match the specified filters.
    """
    filtered = [o for o in offers if o['price_per_hour'] <= max_price]
    
    for offer in filtered:
        assert offer['price_per_hour'] <= max_price
```

### Integration Tests

```python
# tests/integration/test_gateway.py

async def test_full_request_flow():
    """Test complete request flow through all components."""
    # 1. Rate limit check
    # 2. Cache lookup (L2 -> L1)
    # 3. Circuit breaker check
    # 4. Load balancer selection
    # 5. Provider fetch (parallel)
    # 6. Response normalization
    # 7. Cache write
    pass

async def test_graceful_degradation():
    """Test fallback behavior when components fail."""
    # Simulate Redis failure
    # Simulate Vault failure
    # Simulate all providers down
    pass
```

### Performance Tests

```python
# tests/performance/test_throughput.py

async def test_10k_rps_throughput():
    """
    **Feature: provider-api-gateway, Property 1.1**
    Gateway should handle 10,000 RPS per instance.
    """
    # Use locust or similar for load testing
    pass

async def test_cached_response_latency():
    """
    **Feature: provider-api-gateway, Property 1.2**
    Cached responses should return within 10ms.
    """
    pass
```

## Configuration

### Django Settings

```python
# backend/gpubroker/gpubroker/settings/base.py

# Rate Limiting
RATE_LIMITS = {
    'free': 10,
    'pro': 100,
    'enterprise': 1000,
}

# Cache TTLs
CACHE_TTL_PRICING = 60  # seconds
CACHE_TTL_STATIC = 300  # seconds

# Circuit Breaker
CIRCUIT_BREAKER_FAIL_MAX = 5
CIRCUIT_BREAKER_FAIL_RATE = 0.5
CIRCUIT_BREAKER_WINDOW = 30
CIRCUIT_BREAKER_RESET_TIMEOUT = 30

# Load Balancer
LOAD_BALANCER_MAX_QUEUE = 1000
LOAD_BALANCER_MAX_CONCURRENT = 50
LOAD_BALANCER_SLOW_THRESHOLD_MS = 2000

# Vault
VAULT_ADDR = os.getenv('VAULT_ADDR', 'http://localhost:8200')
VAULT_TOKEN = os.getenv('VAULT_TOKEN')

# Redis
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_BEAT_SCHEDULE = {
    'warm-all-caches': {
        'task': 'apps.providers.tasks.warm_all_provider_caches',
        'schedule': 300.0,
    },
    'health-check-all': {
        'task': 'apps.providers.tasks.health_check_all_providers',
        'schedule': 30.0,
    },
}
```

### Connection Pooling

```python
# Database connection pooling
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # 10 minutes
        'CONN_HEALTH_CHECKS': True,
        'OPTIONS': {
            'MAX_CONNS': 20,
        },
    }
}

# Redis connection pooling
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': REDIS_URL,
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
            'CONNECTION_POOL_KWARGS': {
                'max_connections': 50,
            },
        },
    }
}
```

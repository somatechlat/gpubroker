"""
Centralized message catalog for GPUBROKER Providers.

All user-facing strings must be retrieved via get_message(code, **kwargs).
"""

from typing import Dict

MESSAGES: Dict[str, str] = {
    # Cache warming
    "cache_warm.starting": "Starting background cache warm",
    "cache_warm.completed": "Background cache warm completed: {count} offers cached from {providers} providers",
    "cache_warm.failed": "Background cache warm failed: {error}",
    "cache_warm.provider_error": "Failed to cache offers for {provider}: {error}",
    # Health checks
    "health_check.created": "Created health check for {provider}",
    "health_check.updated": "Updated health check for {provider}",
    "health_check.failed": "Failed to update health check for {provider}: {error}",
    # Management command
    "command.starting": "Starting provider cache refresh (interval: {interval}s, once: {once})",
    "command.completed": "Cache refresh completed: {count} offers cached",
    "command.interrupted": "Interrupted by user",
    "command.failed": "Cache refresh failed: {error}",
    "command.help": "Run background cache warming for provider offers",
    "command.interval_help": "Refresh interval in seconds (default: 30)",
    "command.once_help": "Run cache warm once and exit",
    # Provider adapters
    "adapter.no_auth": "{provider}: No auth token provided",
    "adapter.fetched": "{provider}: Fetched {count} offers",
    "adapter.api_error": "{provider} API error: {status}",
    "adapter.fetch_failed": "Failed to fetch {provider} data: {error}",
    "adapter.parsing_failed": "Failed to parse {provider} offer: {error}",
    # Circuit breaker
    "circuit_breaker.open": "Circuit breaker open for {provider}",
    "circuit_breaker.closed": "Circuit breaker closed for {provider}",
    # Services
    "services.fetch_started": "Fetched offers from {count} providers in parallel",
    "services.task_failed": "Provider fetch task failed: {error}",
    "services.cache_missing": "No cache for {key}, fetching fresh data",
    "services.cache_stale": "Cache stale for {key}, triggering background refresh",
    "services.refresh_completed": "Background refresh completed for {key}",
    "services.refresh_failed": "Background refresh failed for {key}: {error}",
    "services.fetch_error": "Failed to fetch offers: {error}",
    # Client initialization
    "client.created": "Created shared HTTP/2 client for {name}",
    "client.closed": "Closed shared HTTP/2 client for {name}",
    "client.init_failed": "Failed to initialize provider client: {error}",
    # Generic
    "provider.unknown": "Unknown provider: {provider}",
    "validation.invalid_credentials": "Invalid credentials for {provider}",
}


def get_message(code: str, **kwargs) -> str:
    """
    Retrieve a message by code and format it with kwargs.
    Falls back to code itself if missing.

    Args:
        code: Message code from MESSAGES dict
        **kwargs: Variables to format into the message

    Returns:
        Formatted message string
    """
    template = MESSAGES.get(code, code)
    try:
        return template.format(**kwargs)
    except Exception:
        return template

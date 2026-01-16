"""
Background Cache Warming Service for Provider Offers.

Periodically refreshes provider offers cache to eliminate cold starts.
Runs as Django management command with 30-second intervals.

According to Django docs: https://docs.djangoproject.com/en/5.0/howto/custom-management-commands/
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional, Dict

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand
from django.utils import timezone as django_timezone

from .services import fetch_offers_from_adapters, cache_offers, get_cached_offers
from .models import ProviderHealthCheck
from .common.messages import get_message

logger = logging.getLogger("gpubroker.providers.background_refresh")


class BackgroundRefreshWorker:
    """
    Background worker that periodically refreshes provider cache.
    """

    def __init__(self, interval_seconds: int = 30):
        """
        Initialize background refresh worker.

        Args:
            interval_seconds: Refresh interval (default: 30s)
        """
        self.interval_seconds = interval_seconds
        self.running = False
        self.cache_key_prefix = "providers:warm"

    async def warm_cache(self) -> Dict[str, int]:
        """
        Warm cache by fetching from all providers in parallel.

        Returns:
            Dict with stats: total_fetched, total_cached, errors
        """
        stats = {"total_fetched": 0, "total_cached": 0, "errors": 0, "providers": {}}

        try:
            logger.info(get_message("cache_warm.starting"))

            # Fetch from all providers
            results = await fetch_offers_from_adapters()

            for provider_name, offers in results.items():
                try:
                    # Cache each provider's offers with extended TTL
                    cache_key = f"{self.cache_key_prefix}:{provider_name}"

                    cache_data = {
                        "provider": provider_name,
                        "offers": offers,
                        "cached_at": datetime.now(timezone.utc).isoformat(),
                        "count": len(offers),
                    }

                    # Extended TTL: 90 seconds (vs 60s for user-triggered)
                    cache.set(cache_key, cache_data, timeout=90)

                    stats["total_fetched"] += len(offers)
                    stats["total_cached"] += len(offers)
                    stats["providers"][provider_name] = len(offers)

                    # Update provider health check
                    await self._update_health_check(provider_name, success=True)

                except Exception as e:
                    logger.error(
                        get_message(
                            "cache_warm.provider_error",
                            provider=provider_name,
                            error=str(e),
                        )
                    )
                    stats["errors"] += 1
                    await self._update_health_check(
                        provider_name, success=False, error=str(e)
                    )

            logger.info(
                get_message(
                    "cache_warm.completed",
                    count=stats["total_cached"],
                    providers=len(results),
                )
            )

        except Exception as e:
            logger.error(get_message("cache_warm.failed", error=str(e)))
            stats["errors"] += 1

        return stats

    async def _update_health_check(
        self, provider_name: str, success: bool, error: Optional[str] = None
    ) -> None:
        """
        Update provider health check status.

        Args:
            provider_name: Provider identifier
            success: Whether the check was successful
            error: Optional error message
        """
        from asgiref.sync import sync_to_async

        try:
            health_check, created = await sync_to_async(
                ProviderHealthCheck.objects.update_or_create
            )(
                provider=provider_name,
                defaults={
                    "status": "healthy" if success else "unhealthy",
                    "last_check": django_timezone.now(),
                    "error_message": error,
                    "response_time_ms": 0,  # Would need to measure actual time
                },
            )

            if created:
                logger.info(get_message("health_check.created", provider=provider_name))
            else:
                logger.debug(
                    get_message("health_check.updated", provider=provider_name)
                )

        except Exception as e:
            logger.error(
                get_message("health_check.failed", provider=provider_name, error=str(e))
            )

    async def run(self) -> None:
        """
        Run background refresh loop.
        Continuously refreshes cache at configured interval.
        """
        self.running = True
        logger.info(
            get_message(
                "cache_warm.starting",
                interval=self.interval_seconds,
            )
        )

        while self.running:
            try:
                await self.warm_cache()
                await asyncio.sleep(self.interval_seconds)

            except asyncio.CancelledError:
                logger.info(get_message("command.interrupted"))
                break
            except Exception as e:
                logger.error(get_message("cache_warm.failed", error=str(e)))
                await asyncio.sleep(self.interval_seconds)

    def stop(self) -> None:
        """Stop background refresh worker."""
        self.running = False
        logger.info(get_message("cache_warm.starting"))


class Command(BaseCommand):
    """
    Django management command to run background cache warming.

    Usage:
        python manage.py refresh_provider_cache

    According to Django docs: https://docs.djangoproject.com/en/5.0/howto/custom-management-commands/
    """

    help = get_message("command.help")

    def add_arguments(self, parser):
        parser.add_argument(
            "--interval",
            type=int,
            default=30,
            help=get_message("command.interval_help"),
        )
        parser.add_argument(
            "--once", action="store_true", help=get_message("command.once_help")
        )

    def handle(self, *args, **options):
        """Handle the command execution."""
        interval = options.get("interval", 30)
        once = options.get("once", False)

        self.stdout.write(
            self.style.SUCCESS(
                get_message("command.starting", interval=interval, once=once)
            )
        )

        # Create worker
        worker = BackgroundRefreshWorker(interval_seconds=interval)

        try:
            if once:
                # Run once and exit
                loop = asyncio.get_event_loop()
                stats = loop.run_until_complete(worker.warm_cache())

                self.stdout.write(
                    self.style.SUCCESS(
                        get_message("command.completed", count=stats["total_cached"])
                    )
                )
            else:
                # Run continuously
                loop = asyncio.get_event_loop()
                loop.run_until_complete(worker.run())

        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING(get_message("command.interrupted")))
            worker.stop()
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(get_message("command.failed", error=str(e)))
            )
            raise

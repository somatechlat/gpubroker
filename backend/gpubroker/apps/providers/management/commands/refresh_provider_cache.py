"""
Django management command to refresh provider offers cache.

Usage:
    python manage.py refresh_provider_cache
    python manage.py refresh_provider_cache --interval 60

According to Django docs: https://docs.djangoproject.com/en/5.0/howto/custom-management-commands/
"""

import asyncio
import logging
from django.core.management.base import BaseCommand

from ...background_refresh import BackgroundRefreshWorker
from ...common.messages import get_message


class Command(BaseCommand):
    """
    Management command to run background cache warming for provider offers.
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

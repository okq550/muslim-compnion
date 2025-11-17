"""
Core application configuration.

This module configures the core Django application and handles startup tasks
including cache warming for the metadata endpoint.
"""

import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CoreConfig(AppConfig):
    """Configuration for the core application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.core"
    verbose_name = "Core"

    def ready(self):
        """
        Application startup hook.

        Performs cache warming for metadata endpoint on application startup.
        This ensures the first request to /api/meta/ is fast.
        """
        # Import signals to ensure they are registered
        # pylint: disable=import-outside-toplevel,unused-import
        import backend.core.signals  # noqa: F401

        # Warm metadata cache on startup
        self._warm_metadata_cache()

    def _warm_metadata_cache(self):
        """
        Warm the metadata endpoint cache on application startup.

        This pre-populates the Redis cache with metadata to ensure the first
        request to /api/meta/ is fast (< 100ms). Gracefully handles failures
        to avoid blocking application startup.
        """
        try:
            # Import here to avoid AppRegistryNotReady error
            # pylint: disable=import-outside-toplevel
            import os
            from datetime import datetime
            from datetime import UTC

            from django.conf import settings
            from django.core.cache import cache

            # Build metadata exactly as the endpoint does
            from backend.core.views.main import _get_project_version

            metadata = {
                "project": {
                    "name": "Muslim Companion API",
                    "version": _get_project_version(),
                    "api_version": "v1",
                    "environment": getattr(settings, "ENVIRONMENT", "unknown"),
                    "build_timestamp": os.environ.get("BUILD_TIMESTAMP", ""),
                    "documentation_url": "/api/docs/",
                },
            }

            # Cache with 24-hour TTL (same as endpoint)
            cache_key = "api:metadata:v1"
            cache_ttl = 86400  # 24 hours

            cache.set(cache_key, metadata, cache_ttl)

            startup_time = datetime.now(UTC).isoformat().replace("+00:00", "Z")
            logger.info(
                "Cache warming completed successfully",
                extra={
                    "cache_key": cache_key,
                    "ttl_seconds": cache_ttl,
                    "timestamp": startup_time,
                },
            )

        except Exception as e:  # pylint: disable=broad-except
            # Log but don't crash - cache warming is an optimization, not critical
            logger.warning(
                f"Cache warming failed (non-critical): {e}",
                extra={"error": str(e), "error_type": type(e).__name__},
            )

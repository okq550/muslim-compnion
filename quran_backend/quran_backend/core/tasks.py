"""Celery tasks for core infrastructure operations.

This module contains background tasks for cache warming, health checks,
and other infrastructure maintenance operations.
"""

import logging

from celery import shared_task
from django.core.management import call_command

logger = logging.getLogger(__name__)


@shared_task(
    name="quran_backend.core.warm_quran_cache",
    bind=True,
    max_retries=3,
    default_retry_delay=300,  # 5 minutes
)
def warm_quran_cache(self) -> dict[str, any]:
    """Celery task to warm the cache with frequently accessed content.

    This task runs on a schedule (daily at 1:00 AM UTC) to refresh
    cached static content and ensure optimal performance.

    Scheduled in config/settings/base.py CELERY_BEAT_SCHEDULE.

    Returns:
        Dictionary with task execution status:
        {
            "status": "success" | "failed",
            "message": str,
            "items_cached": int
        }

    Example schedule configuration (add to base.py):
        CELERY_BEAT_SCHEDULE = {
            'warm-cache-daily': {
                'task': 'quran_backend.core.warm_quran_cache',
                'schedule': crontab(hour=1, minute=0),  # 1:00 AM UTC daily
            },
        }
    """
    try:
        logger.info("Starting scheduled cache warming task")

        # Call the management command programmatically
        # This ensures we reuse the same logic and avoid duplication
        call_command("warm_cache", content_types=["all"], verbosity=1)

        logger.info("Cache warming task completed successfully")

        return {
            "status": "success",
            "message": "Cache warming completed",
        }

    except Exception as e:
        logger.error(f"Cache warming task failed: {e}", exc_info=True)

        # Retry the task if it fails (max 3 attempts)
        try:
            raise self.retry(exc=e)
        except self.MaxRetriesExceededError:
            logger.error(
                "Cache warming task failed after maximum retries. "
                "Manual intervention may be required.",
            )
            return {
                "status": "failed",
                "message": f"Cache warming failed: {e}",
            }


@shared_task(name="quran_backend.core.check_cache_health")
def check_cache_health_task() -> dict[str, any]:
    """Celery task to check cache health and report metrics.

    Can be scheduled to run periodically for monitoring purposes.

    Returns:
        Dictionary with cache health status
    """
    try:
        from quran_backend.core.health import check_cache_health

        health_status = check_cache_health()

        # Log warning if cache is degraded or unavailable
        if health_status["status"] == "degraded":
            logger.warning(
                f"Cache health degraded: {health_status['details']}, "
                f"latency: {health_status['latency_ms']}ms",
            )
        elif health_status["status"] == "unavailable":
            logger.error(f"Cache unavailable: {health_status['details']}")
        else:
            logger.info(
                f"Cache health check passed (latency: {health_status['latency_ms']}ms)",
            )

        return health_status

    except Exception as e:
        logger.error(f"Cache health check task failed: {e}", exc_info=True)
        return {
            "status": "error",
            "details": f"Health check failed: {e}",
        }


@shared_task(name="quran_backend.core.log_cache_metrics")
def log_cache_metrics_task() -> dict[str, any]:
    """Celery task to collect and log cache metrics to Sentry.

    Should be scheduled to run periodically (e.g., every hour)
    for continuous cache performance monitoring.

    Returns:
        Dictionary with collected metrics
    """
    try:
        from quran_backend.core.metrics import CacheMetrics

        # Collect all metrics
        metrics = CacheMetrics.get_all_metrics()

        # Log to Sentry
        CacheMetrics.log_metrics_to_sentry()

        logger.info(
            f"Cache metrics logged: "
            f"Hit ratio: {metrics['hit_ratio']['hit_ratio']:.2%}, "
            f"Memory: {metrics['memory']['usage_percent']:.2f}%",
        )

        return {
            "status": "success",
            "metrics": metrics,
        }

    except Exception as e:
        logger.error(f"Cache metrics logging task failed: {e}", exc_info=True)
        return {
            "status": "error",
            "details": f"Metrics logging failed: {e}",
        }

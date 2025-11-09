"""Health check utilities for application monitoring.

Provides health check functions for critical infrastructure components
including cache (Redis), database, and external services.

These checks can be exposed via a /health endpoint for monitoring tools,
load balancers, and orchestration platforms.
"""

import logging
from typing import Any

from django.core.cache import cache
from django.db import connection

logger = logging.getLogger(__name__)


def check_cache_health() -> dict[str, Any]:
    """Check Redis cache connectivity and basic operation.

    Performs a simple set/get operation to verify cache is working.
    Used for health check endpoints and monitoring.

    Returns:
        Dictionary with cache health status:
        {
            "status": "available" | "degraded" | "unavailable",
            "latency_ms": float | None,
            "details": str
        }

    Example:
        >>> health = check_cache_health()
        >>> if health["status"] == "available":
        ...     print("Cache is healthy")
    """
    test_key = "health_check:ping"
    test_value = "pong"

    try:
        import time

        # Measure cache operation latency
        start_time = time.time()

        # Test set operation
        cache.set(test_key, test_value, timeout=10)

        # Test get operation
        retrieved_value = cache.get(test_key)

        # Test delete operation
        cache.delete(test_key)

        end_time = time.time()
        latency_ms = (end_time - start_time) * 1000

        # Verify value was stored and retrieved correctly
        if retrieved_value == test_value:
            status = "available"
            details = "Cache operations successful"

            # Warn if latency is high (> 100ms)
            if latency_ms > 100:
                status = "degraded"
                details = f"Cache responding slowly (latency: {latency_ms:.2f}ms)"
                logger.warning(f"Cache health check: {details}")
        else:
            status = "degraded"
            details = "Cache value mismatch (data corruption?)"
            latency_ms = None
            logger.error(f"Cache health check failed: {details}")

        return {
            "status": status,
            "latency_ms": round(latency_ms, 2) if latency_ms else None,
            "details": details,
        }

    except Exception as e:
        logger.error(f"Cache health check failed: {e}", exc_info=True)
        return {
            "status": "unavailable",
            "latency_ms": None,
            "details": f"Cache connection failed: {type(e).__name__}",
        }


def check_database_health() -> dict[str, Any]:
    """Check database connectivity.

    Performs a simple database query to verify connection is working.

    Returns:
        Dictionary with database health status:
        {
            "status": "available" | "unavailable",
            "details": str
        }

    Example:
        >>> health = check_database_health()
        >>> if health["status"] == "available":
        ...     print("Database is healthy")
    """
    try:
        # Execute a simple query to check connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        return {
            "status": "available",
            "details": "Database connection successful",
        }

    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        return {
            "status": "unavailable",
            "details": f"Database connection failed: {type(e).__name__}",
        }


def get_overall_health() -> dict[str, Any]:
    """Get overall application health status.

    Checks all critical infrastructure components and returns
    aggregated health status.

    Returns:
        Dictionary with overall health and component statuses:
        {
            "status": "healthy" | "degraded" | "unhealthy",
            "components": {
                "cache": {...},
                "database": {...}
            }
        }

    Example:
        >>> health = get_overall_health()
        >>> if health["status"] == "healthy":
        ...     print("All systems operational")
    """
    cache_health = check_cache_health()
    database_health = check_database_health()

    # Determine overall status
    if (
        cache_health["status"] in ["available", "degraded"]
        and database_health["status"] == "available"
    ):
        # Cache degraded is OK (graceful degradation)
        overall_status = "healthy" if cache_health["status"] == "available" else "degraded"
    elif database_health["status"] == "unavailable":
        # Database down is critical
        overall_status = "unhealthy"
    elif cache_health["status"] == "unavailable":
        # Cache down is degraded but not critical
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"

    return {
        "status": overall_status,
        "components": {
            "cache": cache_health,
            "database": database_health,
        },
    }

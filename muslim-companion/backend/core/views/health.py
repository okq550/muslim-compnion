"""
Granular Health Check Endpoints for Kubernetes Orchestration.

Implements AC #1-6 from US-API-009:
- /health/check - Liveness probe (minimal check, no external dependencies)
- /health/ready - Readiness probe (full resource check)
- /health/db - Database-specific health check
- /health/cache - Redis cache-specific health check
- /health/disk - Disk space-specific health check

Follows Kubernetes liveness/readiness probe best practices for container orchestration.
"""

import logging
import shutil
import time
from datetime import UTC, datetime
from typing import Any

from celery import current_app
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import OpenApiExample, extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


# ============================================================================
# LIVENESS PROBE - /health/check
# ============================================================================


@extend_schema(
    operation_id="health_liveness_check",
    summary="Liveness Probe - Minimal Server Availability Check",
    description="""
    Kubernetes liveness probe endpoint for container orchestration.

    **Purpose:** Checks if the server process is alive and accepting requests.

    **Behavior:** Returns immediately with no external resource checks (database, Redis, etc.).

    **Use Cases:**
    - Kubernetes liveness probe configuration
    - Load balancer health checks
    - Container restart decisions

    **Performance:** < 10ms response time (no I/O operations)
    """,
    responses={
        200: OpenApiExample(
            "Server Alive",
            value={
                "status": "ok",
                "timestamp": "2025-11-16T10:30:00Z",
            },
        ),
    },
    tags=["Health"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
@never_cache
def liveness_check(request):
    """
    Liveness probe - minimal server availability check.

    GET /health/check

    Returns immediately to indicate server is alive and accepting requests.
    No external resource checks (database, Redis, Celery, disk) are performed.

    This endpoint is designed for Kubernetes liveness probes and load balancer
    health checks where fast response time is critical.

    Returns:
        JsonResponse with liveness status:
        - 200 OK always (unless server process is critically failing)

    Response format:
        {
            "status": "ok",
            "timestamp": "2025-11-16T10:30:00Z"
        }

    Performance:
        - Response time: < 10ms
        - No I/O operations
        - No external dependencies
    """
    response_data = {
        "status": "ok",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
    }

    return Response(response_data, status=status.HTTP_200_OK)


# ============================================================================
# READINESS PROBE - /health/ready
# ============================================================================


@extend_schema(
    operation_id="health_readiness_check",
    summary="Readiness Probe - Full Resource Health Check",
    description="""
    Kubernetes readiness probe endpoint for production traffic routing.

    **Purpose:** Checks if the server is ready to handle production traffic.

    **Behavior:** Checks ALL critical resources (database, cache, Celery, disk).

    **Use Cases:**
    - Kubernetes readiness probe configuration
    - Production traffic routing decisions
    - Detailed system health monitoring

    **Performance:** < 1000ms total response time (includes all resource checks)
    """,
    responses={
        200: OpenApiExample(
            "System Ready",
            value={
                "status": "ready",
                "timestamp": "2025-11-16T10:30:00Z",
                "version": "1.0.0",
                "environment": "production",
                "components": {
                    "database": {
                        "status": "up",
                        "response_time_ms": 15,
                        "connection_pool": "8/20 active",
                    },
                    "cache": {
                        "status": "up",
                        "response_time_ms": 2,
                        "memory_used_mb": 45,
                        "keys": 1250,
                    },
                    "celery": {
                        "status": "up",
                        "workers": 2,
                        "active_tasks": 3,
                        "queue_depth": 12,
                    },
                    "disk": {
                        "status": "ok",
                        "free_percent": 45,
                        "free_gb": 120,
                    },
                },
            },
        ),
        503: OpenApiExample(
            "System Not Ready",
            value={
                "status": "not_ready",
                "timestamp": "2025-11-16T10:30:00Z",
                "version": "1.0.0",
                "environment": "production",
                "components": {
                    "database": {
                        "status": "down",
                        "response_time_ms": 0,
                        "error": "Connection refused",
                    },
                    "cache": {
                        "status": "up",
                        "response_time_ms": 2,
                        "memory_used_mb": 45,
                        "keys": 1250,
                    },
                    "celery": {
                        "status": "down",
                        "workers": 0,
                    },
                    "disk": {
                        "status": "ok",
                        "free_percent": 45,
                        "free_gb": 120,
                    },
                },
            },
        ),
    },
    tags=["Health"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
@never_cache
def readiness_check(request):
    """
    Readiness probe - full resource health check.

    GET /health/ready

    Checks all critical infrastructure components:
    - PostgreSQL database connectivity and connection pool
    - Redis cache connectivity and memory usage
    - Celery worker status and queue depth
    - Disk space availability

    Returns:
        JsonResponse with readiness status:
        - 200 OK if all components healthy
        - 503 Service Unavailable if any critical component unhealthy

    Response format:
        {
            "status": "ready" | "not_ready",
            "timestamp": "2025-11-16T10:30:00Z",
            "version": "1.0.0",
            "environment": "production",
            "components": {
                "database": {...},
                "cache": {...},
                "celery": {...},
                "disk": {...}
            }
        }

    Performance:
        - Total response time: < 1000ms
        - Individual component timeouts: 800ms max
        - Slow checks (> 500ms) logged as warnings
    """
    overall_status = "ready"
    components = {}

    # Check PostgreSQL database (critical)
    db_check = _check_database_health()
    components["database"] = db_check
    if db_check["status"] != "up":
        overall_status = "not_ready"

    # Check Redis cache (critical)
    cache_check = _check_cache_health()
    components["cache"] = cache_check
    if cache_check["status"] != "up":
        overall_status = "not_ready"

    # Check Celery workers (critical)
    celery_check = _check_celery_health()
    components["celery"] = celery_check
    if celery_check["status"] != "up":
        overall_status = "not_ready"

    # Check disk space (warning only, not critical)
    disk_check = _check_disk_health()
    components["disk"] = disk_check
    # Note: Disk is informational; doesn't affect overall readiness

    # Get version and environment
    version = getattr(settings, "VERSION", "unknown")
    environment = getattr(settings, "ENVIRONMENT", "unknown")

    # Build response
    response_data = {
        "status": overall_status,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "version": version,
        "environment": environment,
        "components": components,
    }

    # Log unhealthy status
    if overall_status == "not_ready":
        logger.error(
            "Readiness check failed - system not ready for traffic",
            extra={
                "status": overall_status,
                "components": components,
            },
        )

    # Return appropriate HTTP status
    http_status = (
        status.HTTP_200_OK
        if overall_status == "ready"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return Response(response_data, status=http_status)


# ============================================================================
# RESOURCE-SPECIFIC HEALTH CHECKS
# ============================================================================


@extend_schema(
    operation_id="health_database_check",
    summary="Database-Specific Health Check",
    description="""
    Isolated PostgreSQL database connectivity and performance check.

    **Checks:**
    - Database connection availability
    - Query execution time
    - Connection pool status

    **Performance:** < 200ms response time
    """,
    responses={
        200: OpenApiExample(
            "Database Healthy",
            value={
                "status": "ok",
                "timestamp": "2025-11-16T10:30:00Z",
                "resource": "database",
                "details": {
                    "connection": "active",
                    "response_time_ms": 15,
                    "connection_pool": {
                        "active": 8,
                        "total": 20,
                        "idle": 12,
                    },
                    "last_query_ms": 12,
                },
            },
        ),
        503: OpenApiExample(
            "Database Unhealthy",
            value={
                "status": "error",
                "timestamp": "2025-11-16T10:30:00Z",
                "resource": "database",
                "details": {
                    "connection": "failed",
                    "error": "Connection refused",
                },
            },
        ),
    },
    tags=["Health"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
@never_cache
def database_health_check(request):
    """
    Database-specific health check.

    GET /health/db

    Checks PostgreSQL database connectivity, query execution, and connection pool status.

    Returns:
        JsonResponse with database health status:
        - 200 OK if database accessible and responsive
        - 503 Service Unavailable if database down or timeout

    Response format:
        {
            "status": "ok" | "error",
            "timestamp": "2025-11-16T10:30:00Z",
            "resource": "database",
            "details": {...}
        }

    Performance:
        - Response time: < 200ms
    """
    db_check = _check_database_health()

    response_data = {
        "status": "ok" if db_check["status"] == "up" else "error",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "resource": "database",
        "details": db_check,
    }

    http_status = (
        status.HTTP_200_OK
        if db_check["status"] == "up"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return Response(response_data, status=http_status)


@extend_schema(
    operation_id="health_cache_check",
    summary="Redis Cache-Specific Health Check",
    description="""
    Isolated Redis cache connectivity and performance check.

    **Checks:**
    - Redis connection availability
    - Memory usage and eviction policy
    - Key operations (SET/GET)

    **Performance:** < 50ms response time
    """,
    responses={
        200: OpenApiExample(
            "Cache Healthy",
            value={
                "status": "ok",
                "timestamp": "2025-11-16T10:30:00Z",
                "resource": "cache",
                "details": {
                    "connection": "active",
                    "response_time_ms": 2,
                    "memory_used_mb": 45,
                    "memory_max_mb": 500,
                    "keys": 1250,
                    "eviction_policy": "allkeys-lru",
                },
            },
        ),
        503: OpenApiExample(
            "Cache Unhealthy",
            value={
                "status": "error",
                "timestamp": "2025-11-16T10:30:00Z",
                "resource": "cache",
                "details": {
                    "connection": "failed",
                    "error": "Connection timeout",
                },
            },
        ),
    },
    tags=["Health"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
@never_cache
def cache_health_check(request):
    """
    Cache-specific health check.

    GET /health/cache

    Checks Redis cache connectivity, memory usage, and key operations.

    Returns:
        JsonResponse with cache health status:
        - 200 OK if Redis accessible and responsive
        - 503 Service Unavailable if Redis down or timeout

    Response format:
        {
            "status": "ok" | "error",
            "timestamp": "2025-11-16T10:30:00Z",
            "resource": "cache",
            "details": {...}
        }

    Performance:
        - Response time: < 50ms
    """
    cache_check = _check_cache_health()

    response_data = {
        "status": "ok" if cache_check["status"] == "up" else "error",
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "resource": "cache",
        "details": cache_check,
    }

    http_status = (
        status.HTTP_200_OK
        if cache_check["status"] == "up"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return Response(response_data, status=http_status)


@extend_schema(
    operation_id="health_disk_check",
    summary="Disk Space Health Check",
    description="""
    Isolated disk space availability check.

    **Checks:**
    - Available disk space percentage
    - Free disk space in GB
    - Warning and critical thresholds

    **Thresholds:**
    - > 20% free: OK
    - < 20% free: Warning (low disk space)
    - < 10% free: Critical (503 error)

    **Performance:** < 50ms response time
    """,
    responses={
        200: OpenApiExample(
            "Disk Space OK",
            value={
                "status": "ok",
                "timestamp": "2025-11-16T10:30:00Z",
                "resource": "disk",
                "details": {
                    "free_percent": 45,
                    "free_gb": 120,
                    "total_gb": 267,
                    "mount_point": "/",
                    "warning_threshold": 20,
                    "critical_threshold": 10,
                },
            },
        ),
        503: OpenApiExample(
            "Critical Low Disk Space",
            value={
                "status": "critical",
                "timestamp": "2025-11-16T10:30:00Z",
                "resource": "disk",
                "details": {
                    "free_percent": 8,
                    "free_gb": 21,
                    "total_gb": 267,
                    "mount_point": "/",
                    "warning_threshold": 20,
                    "critical_threshold": 10,
                },
            },
        ),
    },
    tags=["Health"],
)
@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
@never_cache
def disk_health_check(request):
    """
    Disk space health check.

    GET /health/disk

    Checks available disk space and returns status based on thresholds.

    Returns:
        JsonResponse with disk health status:
        - 200 OK if sufficient disk space (> 20%)
        - 503 Service Unavailable if critical low disk space (< 10%)

    Response format:
        {
            "status": "ok" | "low" | "critical",
            "timestamp": "2025-11-16T10:30:00Z",
            "resource": "disk",
            "details": {...}
        }

    Performance:
        - Response time: < 50ms
    """
    disk_check = _check_disk_health()

    response_data = {
        "status": disk_check["status"],
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "resource": "disk",
        "details": disk_check,
    }

    # Return 503 only for critical disk space (< 10%)
    http_status = (
        status.HTTP_200_OK
        if disk_check["status"] != "critical"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )

    return Response(response_data, status=http_status)


# ============================================================================
# INTERNAL COMPONENT CHECK FUNCTIONS
# ============================================================================


def _check_database_health() -> dict[str, Any]:
    """
    Check PostgreSQL database connectivity and latency.

    Returns:
        Dictionary with database health status:
        {
            "status": "up" | "down",
            "response_time_ms": float,
            "connection_pool": str,  # e.g., "8/20 active"
            "last_query_ms": float,
        }
    """
    try:
        start_time = time.perf_counter()

        # Execute simple query to check connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()

        response_time_ms = (time.perf_counter() - start_time) * 1000

        # Get connection pool stats
        pool_size = getattr(connection, "pool", None)
        if pool_size:
            active = len([c for c in pool_size if c.in_use])
            total = len(pool_size)
            pool_info = f"{active}/{total} active"
        else:
            pool_info = "N/A"

        # Log slow queries
        if response_time_ms > 500:
            logger.warning(
                f"Slow database health check: {response_time_ms:.2f}ms",
                extra={"response_time_ms": response_time_ms},
            )

        return {
            "status": "up",
            "response_time_ms": round(response_time_ms, 2),
            "connection_pool": pool_info,
            "last_query_ms": round(response_time_ms, 2),
        }

    except Exception as e:
        logger.exception("Database health check failed")
        return {
            "status": "down",
            "response_time_ms": 0,
            "error": str(e),
        }


def _check_cache_health() -> dict[str, Any]:
    """
    Check Redis cache connectivity and latency.

    Returns:
        Dictionary with cache health status:
        {
            "status": "up" | "down",
            "response_time_ms": float,
            "memory_used_mb": int,
            "memory_max_mb": int,
            "keys": int,
            "eviction_policy": str,
        }
    """
    try:
        start_time = time.perf_counter()

        cache_key = "health_check:cache_test"
        cache_value = "ok"

        # Test SET and GET operations
        cache.set(cache_key, cache_value, timeout=10)
        result = cache.get(cache_key)
        cache.delete(cache_key)

        response_time_ms = (time.perf_counter() - start_time) * 1000

        if result != cache_value:
            logger.error("Cache read/write mismatch in health check")
            return {
                "status": "down",
                "response_time_ms": 0,
                "error": "Cache value mismatch",
            }

        # Get Redis INFO (if django-redis is configured)
        try:
            redis_client = cache._cache.get_client()
            info = redis_client.info("memory")
            memory_used_mb = info.get("used_memory", 0) // (1024 * 1024)
            memory_max_mb = info.get("maxmemory", 0) // (1024 * 1024)

            # Get key count
            db_size = redis_client.dbsize()

            # Get eviction policy
            config = redis_client.config_get("maxmemory-policy")
            eviction_policy = config.get("maxmemory-policy", "unknown")

        except Exception:
            # Graceful degradation if Redis INFO not available
            memory_used_mb = 0
            memory_max_mb = 0
            db_size = 0
            eviction_policy = "unknown"

        # Log slow checks
        if response_time_ms > 500:
            logger.warning(
                f"Slow cache health check: {response_time_ms:.2f}ms",
                extra={"response_time_ms": response_time_ms},
            )

        return {
            "status": "up",
            "response_time_ms": round(response_time_ms, 2),
            "memory_used_mb": memory_used_mb,
            "memory_max_mb": memory_max_mb,
            "keys": db_size,
            "eviction_policy": eviction_policy,
        }

    except Exception as e:
        logger.exception("Cache health check failed")
        return {
            "status": "down",
            "response_time_ms": 0,
            "error": str(e),
        }


def _check_celery_health() -> dict[str, Any]:
    """
    Check Celery worker status.

    Returns:
        Dictionary with Celery health status:
        {
            "status": "up" | "down",
            "workers": int,
            "active_tasks": int,
            "queue_depth": int,
        }
    """
    try:
        # Inspect active workers
        stats = current_app.control.inspect().stats()
        worker_count = len(stats) if stats else 0

        if worker_count == 0:
            logger.warning("No active Celery workers found")
            return {
                "status": "down",
                "workers": 0,
            }

        # Get active tasks
        active_tasks = current_app.control.inspect().active()
        total_active = sum(len(tasks) for tasks in (active_tasks or {}).values())

        # Get queue depth (reserved tasks)
        reserved_tasks = current_app.control.inspect().reserved()
        total_reserved = sum(len(tasks) for tasks in (reserved_tasks or {}).values())

        return {
            "status": "up",
            "workers": worker_count,
            "active_tasks": total_active,
            "queue_depth": total_reserved,
        }

    except Exception as e:
        logger.exception("Celery health check failed")
        return {
            "status": "down",
            "workers": 0,
            "error": str(e),
        }


def _check_disk_health() -> dict[str, Any]:
    """
    Check disk space availability.

    Returns:
        Dictionary with disk health status:
        {
            "status": "ok" | "low" | "critical",
            "free_percent": float,
            "free_gb": int,
            "total_gb": int,
            "mount_point": str,
            "warning_threshold": int,
            "critical_threshold": int,
        }
    """
    try:
        # Check root filesystem
        stat = shutil.disk_usage("/")
        free_percent = (stat.free / stat.total) * 100
        free_gb = stat.free // (1024**3)
        total_gb = stat.total // (1024**3)

        critical_threshold = 10
        warning_threshold = 20

        if free_percent < critical_threshold:
            disk_status = "critical"
            logger.critical(
                f"Critical disk space: {free_percent:.1f}% free",
                extra={"free_percent": free_percent, "free_gb": free_gb},
            )
        elif free_percent < warning_threshold:
            disk_status = "low"
            logger.warning(
                f"Low disk space: {free_percent:.1f}% free",
                extra={"free_percent": free_percent, "free_gb": free_gb},
            )
        else:
            disk_status = "ok"

        return {
            "status": disk_status,
            "free_percent": round(free_percent, 1),
            "free_gb": free_gb,
            "total_gb": total_gb,
            "mount_point": "/",
            "warning_threshold": warning_threshold,
            "critical_threshold": critical_threshold,
        }

    except Exception as e:
        logger.exception("Disk space check failed")
        return {
            "status": "unknown",
            "free_percent": 0,
            "free_gb": 0,
            "error": str(e),
        }

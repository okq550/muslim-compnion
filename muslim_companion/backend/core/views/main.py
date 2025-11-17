"""
Health Check Endpoint for Monitoring.

Implements AC #5 from US-API-007:
- Continuous system health monitoring
- Check PostgreSQL, Redis, Celery, disk space
- Return JSON response with status and latencies
- Return 200 OK if healthy, 503 if unhealthy
- Complete checks in < 1 second
- Excluded from authentication and rate limiting

Implements AC #7-8 from US-API-009:
- Project metadata endpoint (/api/meta/)
- Version from pyproject.toml with caching
"""

import importlib.metadata
import logging
import os
import shutil
import time
from datetime import UTC
from datetime import datetime

from celery import current_app
from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@extend_schema(
    operation_id="health_check",
    summary="System Health Check",
    description="""
    Health check endpoint for monitoring system components.

    **Monitors:**
    - PostgreSQL database connectivity and query execution
    - Redis cache connectivity and read/write operations
    - Celery worker status (at least one worker alive)
    - Disk space availability (warn if < 20% free)

    **Performance:** All checks complete in < 1 second

    **Access:** Public endpoint (no authentication required, not rate limited)
    """,
    responses={
        200: OpenApiExample(
            "Healthy System",
            value={
                "status": "healthy",
                "timestamp": "2025-11-09T10:30:00Z",
                "checks": {
                    "database": {"status": "up", "latency_ms": 15},
                    "cache": {"status": "up", "latency_ms": 2},
                    "celery": {"status": "up", "workers": 2},
                    "disk": {"status": "ok", "free_percent": 45},
                },
            },
        ),
        503: OpenApiExample(
            "Unhealthy System",
            value={
                "status": "unhealthy",
                "timestamp": "2025-11-09T10:30:00Z",
                "checks": {
                    "database": {"status": "down", "latency_ms": 0},
                    "cache": {"status": "up", "latency_ms": 2},
                    "celery": {"status": "down", "workers": 0},
                    "disk": {"status": "ok", "free_percent": 45},
                },
            },
        ),
    },
    tags=["🌐 Public", "Health & Monitoring"],
    auth=[],
)
@csrf_exempt
@never_cache
@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint for monitoring system components.

    GET /api/v1/health/

    Monitors:
    - PostgreSQL database connectivity and query execution
    - Redis cache connectivity and read/write operations
    - Celery worker status (at least one worker alive)
    - Disk space availability (warn if < 20% free)

    Returns:
        JsonResponse with health status:
        - 200 OK if all checks pass
        - 503 Service Unavailable if any critical check fails

    Response format:
        {
            "status": "healthy" | "unhealthy",
            "timestamp": "2025-11-09T10:30:00Z",
            "checks": {
                "database": {"status": "up", "latency_ms": 15},
                "cache": {"status": "up", "latency_ms": 2},
                "celery": {"status": "up", "workers": 2},
                "disk": {"status": "ok", "free_percent": 45}
            }
        }
    """
    overall_status = "healthy"
    checks = {}

    # Check PostgreSQL database (critical)
    db_status, db_latency = _check_database()
    checks["database"] = {"status": db_status, "latency_ms": db_latency}
    if db_status != "up":
        overall_status = "unhealthy"

    # Check Redis cache (critical)
    cache_status, cache_latency = _check_cache()
    checks["cache"] = {"status": cache_status, "latency_ms": cache_latency}
    if cache_status != "up":
        overall_status = "unhealthy"

    # Check Celery workers (critical)
    celery_status, worker_count = _check_celery()
    checks["celery"] = {"status": celery_status, "workers": worker_count}
    if celery_status != "up":
        overall_status = "unhealthy"

    # Check disk space (warning only)
    disk_status, free_percent = _check_disk()
    checks["disk"] = {"status": disk_status, "free_percent": free_percent}

    # Build response
    response_data = {
        "status": overall_status,
        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "checks": checks,
    }

    # Return appropriate HTTP status
    http_status = 200 if overall_status == "healthy" else 503

    # Log unhealthy status
    if overall_status == "unhealthy":
        logger.error(
            "Health check failed",
            extra={
                "status": overall_status,
                "checks": checks,
            },
        )

    return JsonResponse(response_data, status=http_status)


def _check_database():
    """
    Check PostgreSQL database connectivity and latency.

    Returns:
        tuple: (status: str, latency_ms: float)
        - status: "up" or "down"
        - latency_ms: Query execution time in milliseconds
    """
    try:
        start_time = time.time()
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        latency_ms = (time.time() - start_time) * 1000
        return ("up", round(latency_ms, 2))
    except Exception:
        logger.exception("Database health check failed")
        return ("down", 0.0)


def _check_cache():
    """
    Check Redis cache connectivity and latency.

    Returns:
        tuple: (status: str, latency_ms: float)
        - status: "up" or "down"
        - latency_ms: Read/write operation time in milliseconds
    """
    try:
        start_time = time.time()
        cache_key = "health_check_test"
        cache_value = "ok"

        # Test write operation
        cache.set(cache_key, cache_value, 10)

        # Test read operation
        result = cache.get(cache_key)

        latency_ms = (time.time() - start_time) * 1000

        if result == cache_value:
            return ("up", round(latency_ms, 2))
        logger.warning("Cache read/write mismatch in health check")
        return ("down", 0.0)

    except Exception:
        logger.exception("Cache health check failed")
        return ("down", 0.0)


def _check_celery():
    """
    Check Celery worker status.

    Returns:
        tuple: (status: str, worker_count: int)
        - status: "up" if at least one worker alive, "down" otherwise
        - worker_count: Number of active Celery workers
    """
    try:
        # Inspect active workers
        stats = current_app.control.inspect().stats()
        worker_count = len(stats) if stats else 0

        if worker_count > 0:
            return ("up", worker_count)
        logger.warning("No active Celery workers found")
        return ("down", 0)

    except Exception:
        logger.exception("Celery health check failed")
        return ("down", 0)


def _check_disk():
    """
    Check disk space availability.

    Returns:
        tuple: (status: str, free_percent: float)
        - status: "ok" if > 20% free, "low" if < 20%, "critical" if < 10%
        - free_percent: Percentage of free disk space
    """
    try:
        stat = shutil.disk_usage("/")
        free_percent = (stat.free / stat.total) * 100

        critical_threshold = 10
        low_threshold = 20

        if free_percent < critical_threshold:
            logger.critical("Critical disk space: %.1f%% free", free_percent)
            return ("critical", round(free_percent, 1))
        if free_percent < low_threshold:
            logger.warning("Low disk space: %.1f%% free", free_percent)
            return ("low", round(free_percent, 1))
        return ("ok", round(free_percent, 1))

    except Exception:
        logger.exception("Disk space check failed")
        return ("unknown", 0.0)


# ============================================================================
# PROJECT METADATA ENDPOINT - /api/meta/
# ============================================================================


@extend_schema(
    operation_id="project_metadata",
    summary="Project Metadata and API Discovery",
    description="""
    Public endpoint for retrieving project metadata and API information.

    **Returns:**
    - Project name and version
    - API version
    - Environment (production/staging/development)
    - Build timestamp
    - Documentation URL

    **Caching:** Response is cached in Redis for 24 hours for performance.

    **Access:** Public endpoint (no authentication required)
    """,
    responses={
        200: OpenApiExample(
            "Project Metadata",
            value={
                "project": {
                    "name": "Muslim Companion API",
                    "version": "0.1.0",
                    "api_version": "v1",
                    "environment": "production",
                    "build_timestamp": "2025-11-16T08:00:00Z",
                    "documentation_url": "/api/docs/",
                },
            },
        ),
    },
    tags=["🌐 Public", "System Metadata"],
    auth=[],
)
@api_view(["GET"])
@permission_classes([AllowAny])
@csrf_exempt
@never_cache
def project_metadata(request):
    """
    Project metadata endpoint for API discovery.

    GET /api/meta/

    Returns project information including name, version, environment, and documentation URL.
    Response is cached in Redis for 24 hours to improve performance.

    Returns:
        Response with project metadata:
        - 200 OK always

    Response format:
        {
            "project": {
                "name": "Muslim Companion API",
                "version": "0.1.0",
                "api_version": "v1",
                "environment": "production",
                "build_timestamp": "2025-11-16T08:00:00Z",
                "documentation_url": "/api/docs/"
            }
        }

    Caching:
        - Cache key: api:metadata:v1
        - TTL: 24 hours (86400 seconds)
        - Graceful degradation if Redis unavailable
    """
    cache_key = "api:metadata:v1"
    cache_ttl = 86400  # 24 hours

    # Try to get from cache first
    try:
        cached_metadata = cache.get(cache_key)
        if cached_metadata:
            return Response(cached_metadata, status=status.HTTP_200_OK)
    except Exception as e:
        logger.warning(f"Cache read failed for metadata endpoint: {e}")

    # Generate metadata
    metadata = {
        "project": {
            "name": "Muslim Companion API",
            "version": _get_project_version(),
            "api_version": "v1",
            "environment": getattr(settings, "ENVIRONMENT_NAME", "unknown"),
            "build_timestamp": os.environ.get("BUILD_TIMESTAMP", ""),
            "documentation_url": "/api/docs/",
        },
    }

    # Try to cache the response
    try:
        cache.set(cache_key, metadata, cache_ttl)
    except Exception as e:
        logger.warning(f"Cache write failed for metadata endpoint: {e}")

    return Response(metadata, status=status.HTTP_200_OK)


def _get_project_version() -> str:
    """
    Get project version from pyproject.toml using importlib.metadata.

    Attempts to read version in this order:
    1. importlib.metadata.version('muslim_companion')
    2. Environment variable APP_VERSION
    3. Fallback to 'unknown'

    Returns:
        str: Project version string
    """
    try:
        # Try to get version from installed package (package name uses underscores)
        return importlib.metadata.version("muslim_companion")
    except importlib.metadata.PackageNotFoundError:
        pass

    # Fallback to environment variable
    version = os.environ.get("APP_VERSION")
    if version:
        return version

    # Last resort fallback
    return "unknown"

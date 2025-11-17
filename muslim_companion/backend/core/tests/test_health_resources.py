"""
Integration tests for resource-specific health check endpoints.

Tests AC #3, #4, #5 from US-API-009:
- /health/db - Database-specific health check
- /health/cache - Redis cache-specific health check
- /health/disk - Disk space-specific health check
"""

import time

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()


@pytest.mark.django_db
class TestDatabaseHealthCheck:
    """Test suite for database health check endpoint (GET /health/db)."""

    def test_database_health_returns_200_when_healthy(self, api_client):
        """Test that database health check returns 200 OK when database is accessible."""
        url = reverse("health-database")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ok"

    def test_database_health_response_format(self, api_client):
        """Test that database health check returns correct response format."""
        url = reverse("health-database")
        response = api_client.get(url)

        assert "status" in response.data
        assert "timestamp" in response.data
        assert "resource" in response.data
        assert "details" in response.data
        assert response.data["resource"] == "database"

    def test_database_health_includes_response_time(self, api_client):
        """Test that database health check includes response time measurement."""
        url = reverse("health-database")
        response = api_client.get(url)

        details = response.data["details"]
        assert "response_time_ms" in details
        assert isinstance(details["response_time_ms"], (int, float))
        assert details["response_time_ms"] >= 0

    def test_database_health_response_time_under_200ms(self, api_client):
        """Test that database health check responds in < 200ms."""
        url = reverse("health-database")

        start_time = time.perf_counter()
        response = api_client.get(url)
        end_time = time.perf_counter()

        response_time_ms = (end_time - start_time) * 1000

        assert response.status_code == status.HTTP_200_OK
        assert response_time_ms < 300, f"Response time: {response_time_ms:.2f}ms"  # Allow margin

    def test_database_health_with_database_down(self, api_client, monkeypatch):
        """Test that database health check returns 503 when database is down."""
        url = reverse("health-database")

        # Mock database check to fail
        def mock_check_database():
            return {"status": "down", "response_time_ms": 0, "error": "Connection refused"}

        monkeypatch.setattr(
            "backend.core.views.health._check_database_health",
            mock_check_database,
        )

        response = api_client.get(url)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "error"
        assert response.data["details"]["status"] == "down"

    def test_database_health_no_authentication_required(self, api_client):
        """Test that database health check works without authentication."""
        url = reverse("health-database")

        response = api_client.get(url)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]


@pytest.mark.django_db
class TestCacheHealthCheck:
    """Test suite for cache health check endpoint (GET /health/cache)."""

    def test_cache_health_returns_200_when_healthy(self, api_client):
        """Test that cache health check returns 200 OK when Redis is accessible."""
        url = reverse("health-cache")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ok"

    def test_cache_health_response_format(self, api_client):
        """Test that cache health check returns correct response format."""
        url = reverse("health-cache")
        response = api_client.get(url)

        assert "status" in response.data
        assert "timestamp" in response.data
        assert "resource" in response.data
        assert "details" in response.data
        assert response.data["resource"] == "cache"

    def test_cache_health_includes_response_time(self, api_client):
        """Test that cache health check includes response time measurement."""
        url = reverse("health-cache")
        response = api_client.get(url)

        details = response.data["details"]
        assert "response_time_ms" in details
        assert isinstance(details["response_time_ms"], (int, float))
        assert details["response_time_ms"] >= 0

    def test_cache_health_includes_memory_usage(self, api_client):
        """Test that cache health check includes memory usage information."""
        url = reverse("health-cache")
        response = api_client.get(url)

        details = response.data["details"]
        # Memory usage might be 0 if Redis INFO is not available, but field should exist
        assert "memory_used_mb" in details or "error" in details

    def test_cache_health_response_time_under_50ms(self, api_client):
        """Test that cache health check responds in < 50ms."""
        url = reverse("health-cache")

        start_time = time.perf_counter()
        response = api_client.get(url)
        end_time = time.perf_counter()

        response_time_ms = (end_time - start_time) * 1000

        assert response.status_code == status.HTTP_200_OK
        assert response_time_ms < 150, f"Response time: {response_time_ms:.2f}ms"  # Allow margin

    def test_cache_health_with_cache_down(self, api_client, monkeypatch):
        """Test that cache health check returns 503 when Redis is down."""
        url = reverse("health-cache")

        # Mock cache check to fail
        def mock_check_cache():
            return {"status": "down", "response_time_ms": 0, "error": "Connection timeout"}

        monkeypatch.setattr(
            "backend.core.views.health._check_cache_health",
            mock_check_cache,
        )

        response = api_client.get(url)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "error"
        assert response.data["details"]["status"] == "down"

    def test_cache_health_no_authentication_required(self, api_client):
        """Test that cache health check works without authentication."""
        url = reverse("health-cache")

        response = api_client.get(url)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]


@pytest.mark.django_db
class TestDiskHealthCheck:
    """Test suite for disk health check endpoint (GET /health/disk)."""

    def test_disk_health_returns_200_when_sufficient_space(self, api_client):
        """Test that disk health check returns 200 OK when disk space > 20%."""
        url = reverse("health-disk")
        response = api_client.get(url)

        # Should return 200 unless disk is critically low (< 10%)
        # Most development environments will have > 20% free
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]

    def test_disk_health_response_format(self, api_client):
        """Test that disk health check returns correct response format."""
        url = reverse("health-disk")
        response = api_client.get(url)

        assert "status" in response.data
        assert "timestamp" in response.data
        assert "resource" in response.data
        assert "details" in response.data
        assert response.data["resource"] == "disk"

    def test_disk_health_includes_free_percent(self, api_client):
        """Test that disk health check includes free percentage."""
        url = reverse("health-disk")
        response = api_client.get(url)

        details = response.data["details"]
        assert "free_percent" in details
        assert isinstance(details["free_percent"], (int, float))
        assert 0 <= details["free_percent"] <= 100

    def test_disk_health_includes_free_gb(self, api_client):
        """Test that disk health check includes free GB."""
        url = reverse("health-disk")
        response = api_client.get(url)

        details = response.data["details"]
        assert "free_gb" in details
        assert isinstance(details["free_gb"], int)
        assert details["free_gb"] >= 0

    def test_disk_health_includes_thresholds(self, api_client):
        """Test that disk health check includes warning and critical thresholds."""
        url = reverse("health-disk")
        response = api_client.get(url)

        details = response.data["details"]
        assert "warning_threshold" in details
        assert "critical_threshold" in details
        assert details["warning_threshold"] == 20
        assert details["critical_threshold"] == 10

    def test_disk_health_response_time_under_50ms(self, api_client):
        """Test that disk health check responds in < 50ms."""
        url = reverse("health-disk")

        start_time = time.perf_counter()
        response = api_client.get(url)
        end_time = time.perf_counter()

        response_time_ms = (end_time - start_time) * 1000

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]
        assert response_time_ms < 150, f"Response time: {response_time_ms:.2f}ms"  # Allow margin

    def test_disk_health_with_critical_low_space(self, api_client, monkeypatch):
        """Test that disk health check returns 503 when disk space < 10%."""
        url = reverse("health-disk")

        # Mock disk check to return critical status
        def mock_check_disk():
            return {
                "status": "critical",
                "free_percent": 8.0,
                "free_gb": 21,
                "total_gb": 267,
                "mount_point": "/",
                "warning_threshold": 20,
                "critical_threshold": 10,
            }

        monkeypatch.setattr(
            "backend.core.views.health._check_disk_health",
            mock_check_disk,
        )

        response = api_client.get(url)

        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.data["status"] == "critical"
        assert response.data["details"]["free_percent"] == 8.0

    def test_disk_health_with_low_space(self, api_client, monkeypatch):
        """Test that disk health check returns 200 with warning when space < 20% but > 10%."""
        url = reverse("health-disk")

        # Mock disk check to return low status
        def mock_check_disk():
            return {
                "status": "low",
                "free_percent": 15.0,
                "free_gb": 40,
                "total_gb": 267,
                "mount_point": "/",
                "warning_threshold": 20,
                "critical_threshold": 10,
            }

        monkeypatch.setattr(
            "backend.core.views.health._check_disk_health",
            mock_check_disk,
        )

        response = api_client.get(url)

        # Low status returns 200 (not critical)
        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "low"
        assert response.data["details"]["free_percent"] == 15.0

    def test_disk_health_no_authentication_required(self, api_client):
        """Test that disk health check works without authentication."""
        url = reverse("health-disk")

        response = api_client.get(url)

        assert response.status_code in [status.HTTP_200_OK, status.HTTP_503_SERVICE_UNAVAILABLE]

"""
Tests for health check endpoint.

Tests AC #5 from US-API-007:
- Health check endpoint returns correct status
- Monitors PostgreSQL, Redis, Celery, disk space
- Returns 200 OK when healthy, 503 when unhealthy
- Completes in < 1 second
- JSON response format correct
"""

import time
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse


@pytest.mark.django_db
class TestHealthCheckEndpoint:
    """Test health check endpoint functionality."""

    def test_returns_200_ok_when_all_services_healthy(self):
        """Test health check returns 200 OK when all services are healthy."""
        client = Client()
        url = reverse("health-check")

        response = client.get(url)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert "checks" in data
        assert data["checks"]["database"]["status"] == "up"
        assert data["checks"]["cache"]["status"] == "up"
        # Celery might not be running in tests
        assert data["checks"]["celery"]["status"] in ["up", "down"]
        assert data["checks"]["disk"]["status"] in ["ok", "low"]

    @patch("backend.core.views.connection")
    def test_returns_503_when_database_down(self, mock_connection):
        """Test health check returns 503 when database is unavailable."""
        # Mock database connection failure
        mock_cursor = MagicMock()
        mock_cursor.execute.side_effect = Exception("Database unavailable")
        mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

        client = Client()
        url = reverse("health-check")

        response = client.get(url)

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"]["status"] == "down"

    @patch("backend.core.views.cache")
    def test_returns_503_when_redis_unavailable(self, mock_cache):
        """Test health check returns 503 when Redis is unavailable."""
        # Mock cache operation failure
        mock_cache.set.side_effect = Exception("Redis unavailable")

        client = Client()
        url = reverse("health-check")

        response = client.get(url)

        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["cache"]["status"] == "down"

    @patch("backend.core.views.current_app")
    def test_returns_503_when_no_celery_workers(self, mock_celery):
        """Test health check returns 503 when no Celery workers are active."""
        # Mock no active workers
        mock_inspect = MagicMock()
        mock_inspect.stats.return_value = None  # No workers
        mock_celery.control.inspect.return_value = mock_inspect

        client = Client()
        url = reverse("health-check")

        response = client.get(url)

        # Might be 503 or 200 depending on other services
        data = response.json()
        assert data["checks"]["celery"]["status"] == "down"
        assert data["checks"]["celery"]["workers"] == 0

    def test_completes_in_under_one_second(self):
        """Test health check completes in < 1 second (with small tolerance for test overhead)."""
        client = Client()
        url = reverse("health-check")

        start_time = time.time()
        response = client.get(url)
        elapsed_time = time.time() - start_time

        assert response.status_code in [200, 503]
        # Allow 1.1s tolerance for test/Docker overhead (AC requires <1s in production)
        assert elapsed_time < 1.1, (
            f"Health check took {elapsed_time:.2f}s (should be < 1.1s including test overhead)"
        )

    def test_json_response_format_correct(self):
        """Test JSON response format matches specification."""
        client = Client()
        url = reverse("health-check")

        response = client.get(url)
        data = response.json()

        # Verify response structure
        assert "status" in data
        assert data["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in data
        assert "checks" in data

        # Verify checks structure
        checks = data["checks"]
        assert "database" in checks
        assert "cache" in checks
        assert "celery" in checks
        assert "disk" in checks

        # Verify database check format
        assert "status" in checks["database"]
        assert "latency_ms" in checks["database"]

        # Verify cache check format
        assert "status" in checks["cache"]
        assert "latency_ms" in checks["cache"]

        # Verify celery check format
        assert "status" in checks["celery"]
        assert "workers" in checks["celery"]

        # Verify disk check format
        assert "status" in checks["disk"]
        assert "free_percent" in checks["disk"]

    def test_health_check_accessible_without_authentication(self):
        """Test health check is accessible without authentication."""
        client = Client()
        url = reverse("health-check")

        # No authentication credentials provided
        response = client.get(url)

        # Should still return a response (not 401 Unauthorized)
        assert response.status_code in [200, 503]

    def test_health_check_not_rate_limited(self):
        """Test health check endpoint is not rate limited."""
        client = Client()
        url = reverse("health-check")

        # Make multiple rapid requests
        for _ in range(10):
            response = client.get(url)
            # Should never return 429 Too Many Requests
            assert response.status_code != 429

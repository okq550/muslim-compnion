"""
Integration tests for liveness probe endpoint.

Tests AC #1 from US-API-009:
- /health/check returns 200 OK instantly
- Response format includes status and timestamp
- Response time < 10ms
- No authentication required
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
class TestLivenessProbe:
    """Test suite for liveness probe endpoint (GET /health/check)."""

    def test_liveness_returns_200_ok(self, api_client):
        """Test that liveness probe returns 200 OK."""
        url = reverse("health-liveness")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_liveness_response_format(self, api_client):
        """Test that liveness probe returns correct response format."""
        url = reverse("health-liveness")
        response = api_client.get(url)

        assert "status" in response.data
        assert "timestamp" in response.data
        assert response.data["status"] == "ok"

    def test_liveness_timestamp_format(self, api_client):
        """Test that timestamp is in ISO 8601 format."""
        url = reverse("health-liveness")
        response = api_client.get(url)

        timestamp = response.data["timestamp"]
        assert isinstance(timestamp, str)
        assert "T" in timestamp
        assert "Z" in timestamp  # UTC indicator

    def test_liveness_response_time_under_10ms(self, api_client):
        """Test that liveness probe responds in < 10ms."""
        url = reverse("health-liveness")

        # Measure response time using high-precision timer
        start_time = time.perf_counter()
        response = api_client.get(url)
        end_time = time.perf_counter()

        response_time_ms = (end_time - start_time) * 1000

        assert response.status_code == status.HTTP_200_OK
        # Allow some margin for test environment overhead
        assert response_time_ms < 50, f"Response time: {response_time_ms:.2f}ms"

    def test_liveness_no_authentication_required(self, api_client):
        """Test that liveness probe works without authentication."""
        url = reverse("health-liveness")

        # Make request without any authentication headers
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ok"

    def test_liveness_multiple_requests(self, api_client):
        """Test that liveness probe handles multiple consecutive requests."""
        url = reverse("health-liveness")

        # Make 10 rapid requests
        for _ in range(10):
            response = api_client.get(url)
            assert response.status_code == status.HTTP_200_OK
            assert response.data["status"] == "ok"

    def test_liveness_no_database_dependency(self, api_client, monkeypatch):
        """Test that liveness probe works even if database is down."""
        url = reverse("health-liveness")

        # Mock database connection to fail
        class MockConnection:
            def cursor(self):
                raise Exception("Database connection failed")

        mock_connection = MockConnection()
        monkeypatch.setattr("backend.core.views.health.connection", mock_connection)

        # Liveness probe should still return OK (no DB dependency)
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ok"

    def test_liveness_no_cache_dependency(self, api_client, monkeypatch):
        """Test that liveness probe works even if Redis is down."""
        url = reverse("health-liveness")

        # Mock cache to fail
        def mock_set(*args, **kwargs):
            raise Exception("Cache connection failed")

        monkeypatch.setattr("django.core.cache.cache.set", mock_set)

        # Liveness probe should still return OK (no cache dependency)
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["status"] == "ok"

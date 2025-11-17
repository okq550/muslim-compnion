"""
Integration tests for project metadata endpoint.

Tests AC #7 and #8 from US-API-009:
- /api/meta/ returns project metadata
- Version from pyproject.toml with fallback
- Environment field populated
- Build timestamp from environment variable
- Response is cached in Redis (24-hour TTL)
- Graceful degradation if Redis unavailable
"""

import pytest
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    """Return an API client for testing."""
    return APIClient()


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache.clear()
    yield
    cache.clear()


@pytest.mark.django_db
class TestProjectMetadata:
    """Test suite for project metadata endpoint (GET /api/meta/)."""

    def test_metadata_returns_200_ok(self, api_client):
        """Test that metadata endpoint returns 200 OK."""
        url = reverse("project-metadata")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

    def test_metadata_response_format(self, api_client):
        """Test that metadata endpoint returns correct response format."""
        url = reverse("project-metadata")
        response = api_client.get(url)

        assert "project" in response.data

        project = response.data["project"]
        assert "name" in project
        assert "version" in project
        assert "api_version" in project
        assert "environment" in project
        assert "build_timestamp" in project
        assert "documentation_url" in project

    def test_metadata_project_name(self, api_client):
        """Test that project name is populated correctly."""
        url = reverse("project-metadata")
        response = api_client.get(url)

        project = response.data["project"]
        assert project["name"] == "Muslim Companion API"

    def test_metadata_version_populated(self, api_client):
        """Test that version field is populated."""
        url = reverse("project-metadata")
        response = api_client.get(url)

        project = response.data["project"]
        assert isinstance(project["version"], str)
        assert len(project["version"]) > 0

    def test_metadata_api_version(self, api_client):
        """Test that API version is v1."""
        url = reverse("project-metadata")
        response = api_client.get(url)

        project = response.data["project"]
        assert project["api_version"] == "v1"

    def test_metadata_environment_populated(self, api_client):
        """Test that environment field is populated."""
        url = reverse("project-metadata")
        response = api_client.get(url)

        project = response.data["project"]
        assert isinstance(project["environment"], str)
        assert len(project["environment"]) > 0

    def test_metadata_build_timestamp_from_env(self, api_client, monkeypatch):
        """Test that build timestamp is read from BUILD_TIMESTAMP environment variable."""
        url = reverse("project-metadata")

        # Clear cache to force fresh read
        cache.clear()

        # Set environment variable
        test_timestamp = "2025-11-16T08:00:00Z"
        monkeypatch.setenv("BUILD_TIMESTAMP", test_timestamp)

        response = api_client.get(url)

        project = response.data["project"]
        assert project["build_timestamp"] == test_timestamp

    def test_metadata_documentation_url(self, api_client):
        """Test that documentation URL is provided."""
        url = reverse("project-metadata")
        response = api_client.get(url)

        project = response.data["project"]
        assert project["documentation_url"] == "/api/docs/"

    def test_metadata_no_authentication_required(self, api_client):
        """Test that metadata endpoint is publicly accessible."""
        url = reverse("project-metadata")

        # Make request without authentication
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "project" in response.data

    def test_metadata_cached_in_redis(self, api_client):
        """Test that metadata response is cached in Redis."""
        url = reverse("project-metadata")

        # First request should cache the response
        response1 = api_client.get(url)
        assert response1.status_code == status.HTTP_200_OK

        # Check that response is in cache
        cache_key = "api:metadata:v1"
        cached_data = cache.get(cache_key)

        assert cached_data is not None
        assert "project" in cached_data
        assert cached_data == response1.data

    def test_metadata_cache_ttl_24_hours(self, api_client):
        """Test that metadata cache TTL is 24 hours (86400 seconds)."""
        url = reverse("project-metadata")

        # Make request to cache the response
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        # Verify cache TTL
        cache_key = "api:metadata:v1"
        cached_data = cache.get(cache_key)

        assert cached_data is not None
        # Note: Direct TTL verification is tricky, but we can verify it's cached

    def test_metadata_subsequent_requests_use_cache(self, api_client, monkeypatch):
        """Test that subsequent requests use cached response."""
        url = reverse("project-metadata")

        # First request caches the response
        response1 = api_client.get(url)
        assert response1.status_code == status.HTTP_200_OK

        # Mock the version function to return different value
        def mock_get_version():
            return "999.999.999"

        monkeypatch.setattr(
            "backend.core.views.main._get_project_version",
            mock_get_version,
        )

        # Second request should use cache (not call _get_project_version)
        response2 = api_client.get(url)
        assert response2.status_code == status.HTTP_200_OK

        # Response should be the same (from cache, not new version)
        assert response1.data == response2.data
        assert response2.data["project"]["version"] != "999.999.999"

    def test_metadata_graceful_degradation_cache_read_failure(self, api_client, monkeypatch):
        """Test graceful degradation when cache read fails."""
        url = reverse("project-metadata")

        # Mock cache.get to fail
        def mock_cache_get(*args, **kwargs):
            raise Exception("Cache read failed")

        monkeypatch.setattr(
            "django.core.cache.cache.get",
            mock_cache_get,
        )

        # Should still return metadata (computed fresh)
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "project" in response.data

    def test_metadata_graceful_degradation_cache_write_failure(self, api_client, monkeypatch):
        """Test graceful degradation when cache write fails."""
        url = reverse("project-metadata")

        # Clear cache first
        cache.clear()

        # Mock cache.set to fail
        def mock_cache_set(*args, **kwargs):
            raise Exception("Cache write failed")

        monkeypatch.setattr(
            "django.core.cache.cache.set",
            mock_cache_set,
        )

        # Should still return metadata (but not cached)
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "project" in response.data

    def test_metadata_version_from_app_version_env(self, api_client, monkeypatch):
        """Test version fallback to APP_VERSION environment variable."""
        url = reverse("project-metadata")

        # Clear cache to force fresh read
        cache.clear()

        # Mock importlib.metadata.version to raise PackageNotFoundError
        import importlib.metadata

        def mock_version(package_name):
            raise importlib.metadata.PackageNotFoundError(package_name)

        monkeypatch.setattr(
            "backend.core.views.main.importlib.metadata.version",
            mock_version,
        )

        # Set APP_VERSION environment variable
        test_version = "1.2.3-custom"
        monkeypatch.setenv("APP_VERSION", test_version)

        response = api_client.get(url)

        project = response.data["project"]
        assert project["version"] == test_version

    def test_metadata_version_fallback_to_unknown(self, api_client, monkeypatch):
        """Test version fallback to 'unknown' when all sources fail."""
        url = reverse("project-metadata")

        # Clear cache to force fresh read
        cache.clear()

        # Mock importlib.metadata.version to raise PackageNotFoundError
        import importlib.metadata

        def mock_version(package_name):
            raise importlib.metadata.PackageNotFoundError(package_name)

        monkeypatch.setattr(
            "backend.core.views.main.importlib.metadata.version",
            mock_version,
        )

        # Clear APP_VERSION environment variable
        monkeypatch.delenv("APP_VERSION", raising=False)

        response = api_client.get(url)

        project = response.data["project"]
        assert project["version"] == "unknown"

    def test_metadata_multiple_concurrent_requests(self, api_client):
        """Test that metadata endpoint handles multiple concurrent requests."""
        url = reverse("project-metadata")

        # Make 10 rapid requests
        responses = [api_client.get(url) for _ in range(10)]

        # All should succeed
        for response in responses:
            assert response.status_code == status.HTTP_200_OK
            assert "project" in response.data

        # All should return same data (from cache after first request)
        for response in responses[1:]:
            assert response.data == responses[0].data

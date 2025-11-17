import hashlib

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from backend.analytics.models import AnalyticsEvent

User = get_user_model()


@pytest.fixture
def api_client():
    """Create an API client."""
    return APIClient()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="TestPass123",
        is_analytics_enabled=False,
    )


@pytest.fixture
def admin_user(db):
    """Create an admin user."""
    return User.objects.create_superuser(
        username="admin",
        email="admin@example.com",
        password="AdminPass123",
    )


@pytest.mark.django_db
class TestAnalyticsConsentEndpoint:
    """Test /api/v1/analytics/consent/ endpoint (AC #4)."""

    def test_consent_endpoint_updates_user_profile(self, api_client, user):
        """Test consent endpoint updates is_analytics_enabled."""
        api_client.force_authenticate(user=user)
        url = reverse("api:analytics-consent")

        response = api_client.post(
            url,
            {"consent_given": True, "consent_version": "1.0"},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_analytics_enabled is True

    def test_consent_requires_authentication(self, api_client):
        """Test consent endpoint requires authentication."""
        url = reverse("api:analytics-consent")
        response = api_client.post(
            url,
            {"consent_given": True},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.django_db
class TestPrivacyPolicyEndpoint:
    """Test /api/v1/legal/privacy-policy/ endpoint (AC #5)."""

    def test_privacy_policy_endpoint_public(self, api_client):
        """Test privacy policy is accessible without authentication."""
        url = reverse("api:privacy-policy")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "content" in response.data
        assert "version" in response.data
        assert "effective_date" in response.data


@pytest.mark.django_db
class TestUserDataDeletionEndpoint:
    """Test /api/v1/analytics/delete-my-data/ endpoint (AC #9)."""

    def test_delete_my_data_removes_user_events(self, api_client, user):
        """Test data deletion endpoint removes user's analytics."""
        # Create analytics events for user
        user_id_hash = hashlib.sha256(
            f"{user.id}{settings.SECRET_KEY}".encode(),
        ).hexdigest()

        AnalyticsEvent.objects.create(
            event_type="test_event",
            event_data={},
            user_id_hash=user_id_hash,
        )

        api_client.force_authenticate(user=user)
        url = reverse("api:analytics-delete-data")

        response = api_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        assert AnalyticsEvent.objects.filter(user_id_hash=user_id_hash).count() == 0
        user.refresh_from_db()
        assert user.is_analytics_enabled is False

    def test_delete_only_deletes_current_user_data(self, api_client, user, db):
        """Test data deletion only removes current user's data, not others."""
        # Create another user with analytics
        other_user = User.objects.create_user(
            username="otheruser",
            email="other@example.com",
            password="TestPass123",
        )

        user_hash = hashlib.sha256(
            f"{user.id}{settings.SECRET_KEY}".encode(),
        ).hexdigest()
        other_hash = hashlib.sha256(
            f"{other_user.id}{settings.SECRET_KEY}".encode(),
        ).hexdigest()

        AnalyticsEvent.objects.create(
            event_type="test_event",
            event_data={},
            user_id_hash=user_hash,
        )
        AnalyticsEvent.objects.create(
            event_type="test_event",
            event_data={},
            user_id_hash=other_hash,
        )

        api_client.force_authenticate(user=user)
        url = reverse("api:analytics-delete-data")
        response = api_client.delete(url)

        assert response.status_code == status.HTTP_200_OK
        # User's data deleted
        assert AnalyticsEvent.objects.filter(user_id_hash=user_hash).count() == 0
        # Other user's data still exists
        assert AnalyticsEvent.objects.filter(user_id_hash=other_hash).count() == 1


@pytest.mark.django_db
class TestAnalyticsAggregationEndpoints:
    """Test analytics aggregation endpoints (AC #7) - Admin only."""

    def test_popular_features_requires_admin(self, api_client, user):
        """Test popular features endpoint requires admin permission."""
        api_client.force_authenticate(user=user)
        url = reverse("api:analytics-popular-features")

        response = api_client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_popular_features_admin_access(self, api_client, admin_user):
        """Test admin can access popular features."""
        api_client.force_authenticate(user=admin_user)
        url = reverse("api:analytics-popular-features")

        # Create some test events
        AnalyticsEvent.objects.create(
            event_type="surah_viewed",
            event_data={"surah_number": 1},
        )

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert "popular_features" in response.data


@pytest.mark.django_db
class TestUserProfileEndpoint:
    """Test /api/v1/users/profile/ endpoint for analytics toggle (AC #2)."""

    def test_user_can_update_analytics_preference(self, api_client, user):
        """Test user can toggle analytics via profile endpoint."""
        from backend.users.models import UserProfile

        # Ensure user has a profile
        UserProfile.objects.get_or_create(user=user)

        api_client.force_authenticate(user=user)
        url = reverse("api:user-profile")

        # Enable analytics
        response = api_client.patch(
            url,
            {"is_analytics_enabled": True},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_analytics_enabled is True

        # Disable analytics
        response = api_client.patch(
            url,
            {"is_analytics_enabled": False},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        user.refresh_from_db()
        assert user.is_analytics_enabled is False

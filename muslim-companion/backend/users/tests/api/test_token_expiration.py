"""
Tests for JWT token expiration handling.

Tests that expired tokens are properly rejected and refresh flow works correctly.
"""

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


@pytest.mark.django_db
class TestTokenExpiration:
    """Test JWT token expiration and refresh behavior."""

    @pytest.fixture(autouse=True)
    def _disable_throttling(self):
        """Disable throttling for these tests."""
        from unittest.mock import patch

        # Mock the throttle's allow_request method to always return True
        with patch(
            "backend.users.api.throttling.AuthEndpointThrottle.allow_request",
            return_value=True,
        ):
            yield

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def test_user(self):
        """Create a test user for token expiration tests."""
        return User.objects.create_user(
            username="tokentest",
            email="token@example.com",
            password="TestPass123",  # noqa: S106
        )

    def test_expired_access_token_returns_401(self, api_client, test_user):
        """Test that expired access token returns 401 Unauthorized."""
        # Create an access token and manually expire it
        access_token = AccessToken.for_user(test_user)
        # Set expiration to past (subtract from current time to make it expired)
        access_token.set_exp(from_time=timezone.now() - timedelta(hours=2))
        expired_token = str(access_token)

        # Try to access protected endpoint with expired token
        url = reverse("api:user-me")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {expired_token}")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_valid_access_token_works(self, api_client, test_user):
        """Test that valid access token allows access to protected endpoints."""
        refresh = RefreshToken.for_user(test_user)
        access_token = str(refresh.access_token)

        url = reverse("api:user-me")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access_token}")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["username"] == test_user.username

    def test_refresh_token_generates_new_access_token(self, api_client, test_user):
        """Test that refresh token can generate new access token."""
        refresh = RefreshToken.for_user(test_user)
        refresh_token = str(refresh)

        url = reverse("api:auth-token-refresh")
        response = api_client.post(url, {"refresh_token": refresh_token}, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data
        assert (
            "refresh_token" in response.data
        )  # Should get new refresh token (rotation)

        # Verify new access token works
        new_access_token = response.data["access_token"]
        me_url = reverse("api:user-me")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access_token}")
        response = api_client.get(me_url)
        assert response.status_code == status.HTTP_200_OK

    def test_expired_refresh_token_returns_401(self, api_client, test_user):
        """Test that expired refresh token returns 401."""
        # Create a refresh token with very short lifetime
        with patch(
            "rest_framework_simplejwt.tokens.RefreshToken.lifetime",
            new=timedelta(seconds=-1),
        ):
            refresh = RefreshToken.for_user(test_user)
            expired_refresh = str(refresh)

        url = reverse("api:auth-token-refresh")
        response = api_client.post(
            url,
            {"refresh_token": expired_refresh},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_invalid_token_format_returns_401(self, api_client):
        """Test that invalid token format returns 401."""
        url = reverse("api:user-me")
        api_client.credentials(HTTP_AUTHORIZATION="Bearer invalid-token-format")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_missing_token_returns_401(self, api_client):
        """Test that missing token returns 401."""
        url = reverse("api:user-me")
        # No credentials set
        response = api_client.get(url)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh_rotation_invalidates_old_refresh_token(
        self,
        api_client,
        test_user,
    ):
        """Test that token rotation makes old refresh token unusable."""
        # Get initial refresh token
        refresh = RefreshToken.for_user(test_user)
        old_refresh_token = str(refresh)

        # Refresh to get new tokens
        url = reverse("api:auth-token-refresh")
        response = api_client.post(
            url,
            {"refresh_token": old_refresh_token},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        new_refresh_token = response.data["refresh_token"]
        assert new_refresh_token != old_refresh_token

        # Try to use old refresh token again - should fail because it's blacklisted
        response = api_client.post(
            url,
            {"refresh_token": old_refresh_token},
            format="json",
        )
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_access_token_lifetime_is_30_minutes(self, test_user):
        """Test that access token lifetime is configured to 30 minutes."""
        access_token = AccessToken.for_user(test_user)

        # Check that lifetime is 30 minutes (as configured in settings)
        expected_lifetime = timedelta(minutes=30)
        assert access_token.lifetime == expected_lifetime

    def test_refresh_token_lifetime_is_14_days(self, test_user):
        """Test that refresh token lifetime is configured to 14 days."""
        refresh_token = RefreshToken.for_user(test_user)

        # Check that lifetime is 14 days (as configured in settings)
        expected_lifetime = timedelta(days=14)
        assert refresh_token.lifetime == expected_lifetime

    def test_token_contains_user_id(self, test_user):
        """Test that JWT token contains user ID claim."""
        access_token = AccessToken.for_user(test_user)

        # Token should contain user_id claim
        assert "user_id" in access_token
        assert str(access_token["user_id"]) == str(test_user.id)

    def test_token_contains_correct_type(self, test_user):
        """Test that access token has correct token_type claim."""
        access_token = AccessToken.for_user(test_user)

        assert "token_type" in access_token
        assert access_token["token_type"] == "access"

    def test_multiple_access_tokens_can_coexist(self, api_client, test_user):
        """Test that multiple valid access tokens for same user work simultaneously."""
        # Generate two different access tokens
        refresh1 = RefreshToken.for_user(test_user)
        access1 = str(refresh1.access_token)

        refresh2 = RefreshToken.for_user(test_user)
        access2 = str(refresh2.access_token)

        assert access1 != access2

        # Both should work
        url = reverse("api:user-me")

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access1}")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {access2}")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

    def test_token_refresh_with_invalid_refresh_token(self, api_client):
        """Test token refresh with completely invalid refresh token."""
        url = reverse("api:auth-token-refresh")
        response = api_client.post(
            url,
            {"refresh_token": "completely-invalid"},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_refresh_without_refresh_token(self, api_client):
        """Test token refresh without providing refresh token."""
        url = reverse("api:auth-token-refresh")
        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

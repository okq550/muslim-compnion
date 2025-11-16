"""
Tests for JWT token blacklisting functionality.

Tests that tokens are properly blacklisted on logout and cannot be reused.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from backend.users.models import User


@pytest.mark.django_db
class TestTokenBlacklisting:
    """Test JWT token blacklisting on logout."""

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
        """Create a test user for blacklist tests."""
        return User.objects.create_user(
            username="blacklisttest",
            email="blacklist@example.com",
            password="TestPass123",  # noqa: S106
        )

    def test_logout_blacklists_token(self, api_client, test_user):
        """Test that logout successfully blacklists the refresh token."""
        # Generate tokens for user
        refresh = RefreshToken.for_user(test_user)
        refresh_token_str = str(refresh)

        # Logout with refresh token
        url = reverse("api:auth-logout")
        response = api_client.post(
            url,
            {"refresh_token": refresh_token_str},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data  # Check message exists (language-agnostic)

        # Verify token was blacklisted
        outstanding_token = OutstandingToken.objects.get(token=refresh_token_str)
        assert BlacklistedToken.objects.filter(token=outstanding_token).exists()

    def test_blacklisted_token_cannot_be_used(self, api_client, test_user):
        """Test that blacklisted token returns 401 on token refresh."""
        # Generate and blacklist token
        refresh = RefreshToken.for_user(test_user)
        refresh_token_str = str(refresh)
        refresh.blacklist()

        # Try to refresh with blacklisted token
        url = reverse("api:auth-token-refresh")
        response = api_client.post(
            url,
            {"refresh_token": refresh_token_str},
            format="json",
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_with_invalid_token_returns_400(self, api_client):
        """Test logout with invalid token returns 400."""
        url = reverse("api:auth-logout")
        response = api_client.post(
            url,
            {"refresh_token": "invalid-token"},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert (
            "detail" in response.data
        )  # Check error detail exists (language-agnostic)

    def test_logout_with_already_blacklisted_token_returns_400(
        self,
        api_client,
        test_user,
    ):
        """Test logout with already blacklisted token returns 400."""
        # Generate and blacklist token
        refresh = RefreshToken.for_user(test_user)
        refresh_token_str = str(refresh)
        refresh.blacklist()

        # Try to logout again with same token
        url = reverse("api:auth-logout")
        response = api_client.post(
            url,
            {"refresh_token": refresh_token_str},
            format="json",
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_outstanding_token_created_on_login(self, api_client, test_user):
        """Test that OutstandingToken is created on login."""
        url = reverse("api:auth-login")
        data = {
            "email": "blacklist@example.com",
            "password": "TestPass123",
        }

        # Count outstanding tokens before
        count_before = OutstandingToken.objects.filter(user=test_user).count()

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        # Outstanding token should be created
        count_after = OutstandingToken.objects.filter(user=test_user).count()
        assert count_after == count_before + 1

    def test_token_rotation_blacklists_old_token(self, api_client, test_user):
        """Test that token rotation blacklists the old refresh token."""
        # Generate initial token
        refresh = RefreshToken.for_user(test_user)
        old_refresh_token = str(refresh)

        # Refresh the token
        url = reverse("api:auth-token-refresh")
        response = api_client.post(
            url,
            {"refresh_token": old_refresh_token},
            format="json",
        )

        assert response.status_code == status.HTTP_200_OK
        assert "refresh_token" in response.data
        new_refresh_token = response.data["refresh_token"]
        assert new_refresh_token != old_refresh_token

        # Verify old token is blacklisted
        outstanding_token = OutstandingToken.objects.get(token=old_refresh_token)
        assert BlacklistedToken.objects.filter(token=outstanding_token).exists()

    def test_token_rotation_new_token_works(self, api_client, test_user):
        """Test that new token from rotation can be used."""
        # Generate and rotate token
        refresh = RefreshToken.for_user(test_user)
        old_refresh_token = str(refresh)

        refresh_url = reverse("api:auth-token-refresh")
        response = api_client.post(
            refresh_url,
            {"refresh_token": old_refresh_token},
            format="json",
        )
        new_refresh_token = response.data["refresh_token"]
        new_access_token = response.data["access_token"]

        # New access token should work
        me_url = reverse("api:user-me")
        api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {new_access_token}")
        response = api_client.get(me_url)
        assert response.status_code == status.HTTP_200_OK

        # New refresh token should work for another rotation
        response = api_client.post(
            refresh_url,
            {"refresh_token": new_refresh_token},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_multiple_token_rotations(self, api_client, test_user):
        """Test that multiple token rotations work correctly."""
        # Start with initial token
        refresh = RefreshToken.for_user(test_user)
        current_refresh = str(refresh)

        url = reverse("api:auth-token-refresh")

        # Perform 5 rotations
        for i in range(5):
            response = api_client.post(
                url,
                {"refresh_token": current_refresh},
                format="json",
            )
            assert response.status_code == status.HTTP_200_OK

            new_refresh = response.data["refresh_token"]
            assert new_refresh != current_refresh

            # Old token should be blacklisted
            outstanding_token = OutstandingToken.objects.get(token=current_refresh)
            assert BlacklistedToken.objects.filter(token=outstanding_token).exists()

            # Update for next iteration
            current_refresh = new_refresh

        # Final token should still work
        response = api_client.post(
            url,
            {"refresh_token": current_refresh},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_token_rotation_prevents_replay_attacks(self, api_client, test_user):
        """Test that old tokens cannot be replayed after rotation."""
        # Generate initial token
        refresh = RefreshToken.for_user(test_user)
        token1 = str(refresh)

        url = reverse("api:auth-token-refresh")

        # First rotation
        response = api_client.post(url, {"refresh_token": token1}, format="json")
        token2 = response.data["refresh_token"]

        # Second rotation
        response = api_client.post(url, {"refresh_token": token2}, format="json")
        token3 = response.data["refresh_token"]

        # Try to use token1 (should fail - blacklisted)
        response = api_client.post(url, {"refresh_token": token1}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # Try to use token2 (should fail - blacklisted)
        response = api_client.post(url, {"refresh_token": token2}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        # token3 should still work
        response = api_client.post(url, {"refresh_token": token3}, format="json")
        assert response.status_code == status.HTTP_200_OK

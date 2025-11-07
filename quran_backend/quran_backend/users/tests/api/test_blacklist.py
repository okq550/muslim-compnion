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

from quran_backend.users.models import User


@pytest.mark.django_db
class TestTokenBlacklisting:
    """Test JWT token blacklisting on logout."""

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
        response = api_client.post(url, {"refresh": refresh_token_str}, format="json")

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
        response = api_client.post(url, {"refresh": refresh_token_str}, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_logout_with_invalid_token_returns_400(self, api_client):
        """Test logout with invalid token returns 400."""
        url = reverse("api:auth-logout")
        response = api_client.post(url, {"refresh": "invalid-token"}, format="json")

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
        response = api_client.post(url, {"refresh": refresh_token_str}, format="json")

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

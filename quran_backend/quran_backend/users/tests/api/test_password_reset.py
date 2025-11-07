"""
Tests for password reset functionality - end-to-end flow.

Tests the complete password reset flow from request to confirmation.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import status
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
class TestPasswordResetFlow:
    """Test complete password reset flow end-to-end."""

    @pytest.fixture(autouse=True)
    def _disable_throttling(self):
        """Disable throttling for these tests."""
        from unittest.mock import patch

        # Mock the throttle's allow_request method to always return True
        with patch(
            "quran_backend.users.api.throttling.AuthEndpointThrottle.allow_request",
            return_value=True,
        ):
            yield

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def test_user(self):
        """Create a test user for password reset tests."""
        return User.objects.create_user(
            username="resettest",
            email="reset@example.com",
            password="OldPass123",  # noqa: S106
        )

    def test_password_reset_request_with_valid_email(self, api_client, test_user):
        """Test password reset request with valid email returns 200."""
        url = reverse("api:auth-password-reset")
        data = {"email": "reset@example.com"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    def test_password_reset_request_with_invalid_email(self, api_client):
        """Test password reset request with invalid email still returns 200 for security."""
        url = reverse("api:auth-password-reset")
        data = {"email": "nonexistent@example.com"}

        response = api_client.post(url, data, format="json")

        # Should return 200 even if email doesn't exist (security best practice)
        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    def test_password_reset_request_case_insensitive_email(
        self,
        api_client,
        test_user,
    ):
        """Test password reset with different email case works."""
        url = reverse("api:auth-password-reset")
        data = {"email": "RESET@EXAMPLE.COM"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK

    def test_password_reset_confirm_with_valid_token(self, api_client, test_user):
        """Test password reset confirmation with valid token successfully resets password."""
        # Generate valid reset token
        token = default_token_generator.make_token(test_user)
        uid = urlsafe_base64_encode(force_bytes(test_user.pk))

        url = reverse("api:auth-password-reset-confirm")
        data = {
            "uid": uid,
            "token": token,
            "new_password": "NewSecurePass123",
            "new_password_confirm": "NewSecurePass123",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

        # Verify password was actually changed
        test_user.refresh_from_db()
        assert test_user.check_password("NewSecurePass123")
        assert not test_user.check_password("OldPass123")

    def test_password_reset_confirm_with_invalid_token(self, api_client, test_user):
        """Test password reset confirmation with invalid token returns 400."""
        uid = urlsafe_base64_encode(force_bytes(test_user.pk))

        url = reverse("api:auth-password-reset-confirm")
        data = {
            "uid": uid,
            "token": "invalid-token",
            "new_password": "NewSecurePass123",
            "new_password_confirm": "NewSecurePass123",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

        # Verify password was NOT changed
        test_user.refresh_from_db()
        assert test_user.check_password("OldPass123")

    def test_password_reset_confirm_with_invalid_uid(self, api_client, test_user):
        """Test password reset confirmation with invalid UID returns 400."""
        token = default_token_generator.make_token(test_user)

        url = reverse("api:auth-password-reset-confirm")
        data = {
            "uid": "invalid-uid",
            "token": token,
            "new_password": "NewSecurePass123",
            "new_password_confirm": "NewSecurePass123",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_confirm_with_mismatched_passwords(
        self,
        api_client,
        test_user,
    ):
        """Test password reset with mismatched passwords returns 400."""
        token = default_token_generator.make_token(test_user)
        uid = urlsafe_base64_encode(force_bytes(test_user.pk))

        url = reverse("api:auth-password-reset-confirm")
        data = {
            "uid": uid,
            "token": token,
            "new_password": "NewSecurePass123",
            "new_password_confirm": "DifferentPass123",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "new_password_confirm" in response.data

    def test_password_reset_confirm_with_weak_password(self, api_client, test_user):
        """Test password reset with weak password returns 400."""
        token = default_token_generator.make_token(test_user)
        uid = urlsafe_base64_encode(force_bytes(test_user.pk))

        url = reverse("api:auth-password-reset-confirm")
        data = {
            "uid": uid,
            "token": token,
            "new_password": "weak",  # Too short, no uppercase, no digit
            "new_password_confirm": "weak",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "new_password" in response.data

    def test_password_reset_token_single_use(self, api_client, test_user):
        """Test that password reset token can only be used once."""
        token = default_token_generator.make_token(test_user)
        uid = urlsafe_base64_encode(force_bytes(test_user.pk))

        url = reverse("api:auth-password-reset-confirm")
        data = {
            "uid": uid,
            "token": token,
            "new_password": "NewSecurePass123",
            "new_password_confirm": "NewSecurePass123",
        }

        # First use should succeed
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK

        # Second use with same token should fail
        data["new_password"] = "AnotherPass123"
        data["new_password_confirm"] = "AnotherPass123"
        response = api_client.post(url, data, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_complete_flow(self, api_client, test_user):
        """Test complete password reset flow: request -> confirm -> login."""
        # Step 1: Request password reset
        reset_url = reverse("api:auth-password-reset")
        response = api_client.post(
            reset_url,
            {"email": "reset@example.com"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        # Step 2: Confirm password reset (simulate receiving email)
        token = default_token_generator.make_token(test_user)
        uid = urlsafe_base64_encode(force_bytes(test_user.pk))

        confirm_url = reverse("api:auth-password-reset-confirm")
        response = api_client.post(
            confirm_url,
            {
                "uid": uid,
                "token": token,
                "new_password": "NewSecurePass123",
                "new_password_confirm": "NewSecurePass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        # Step 3: Login with new password
        login_url = reverse("api:auth-login")
        response = api_client.post(
            login_url,
            {"email": "reset@example.com", "password": "NewSecurePass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]

        # Step 4: Verify old password no longer works
        response = api_client.post(
            login_url,
            {"email": "reset@example.com", "password": "OldPass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_password_reset_enforces_password_strength(self, api_client, test_user):
        """Test that password reset enforces same strength requirements as registration."""
        token = default_token_generator.make_token(test_user)
        uid = urlsafe_base64_encode(force_bytes(test_user.pk))
        url = reverse("api:auth-password-reset-confirm")

        # Test: No uppercase
        response = api_client.post(
            url,
            {
                "uid": uid,
                "token": token,
                "new_password": "lowercase123",
                "new_password_confirm": "lowercase123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Refresh token after failed attempt
        token = default_token_generator.make_token(test_user)

        # Test: No lowercase
        response = api_client.post(
            url,
            {
                "uid": uid,
                "token": token,
                "new_password": "UPPERCASE123",
                "new_password_confirm": "UPPERCASE123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Refresh token after failed attempt
        token = default_token_generator.make_token(test_user)

        # Test: No digit
        response = api_client.post(
            url,
            {
                "uid": uid,
                "token": token,
                "new_password": "NoDigitsHere",
                "new_password_confirm": "NoDigitsHere",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST

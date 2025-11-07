"""
Tests for account lockout functionality.

Tests that accounts are properly locked after failed login attempts
and that lockout expires after the configured duration.
"""

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from quran_backend.users.services.account_lockout import AccountLockoutService

User = get_user_model()


@pytest.mark.django_db
class TestAccountLockout:
    """Test account lockout on failed login attempts."""

    @pytest.fixture(autouse=True)
    def _clear_cache(self):
        """Clear cache before each test."""
        cache.clear()
        yield
        cache.clear()

    @pytest.fixture(autouse=True)
    def _disable_throttling(self):
        """Disable throttling for these tests."""
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
        """Create a test user for lockout tests."""
        return User.objects.create_user(
            username="lockouttest",
            email="lockout@example.com",
            password="TestPass123",  # noqa: S106
        )

    def test_nine_failed_attempts_no_lockout(self, api_client, test_user):
        """Test that 9 failed attempts do not lock the account."""
        url = reverse("api:auth-login")

        # Make 9 failed login attempts
        for i in range(9):
            response = api_client.post(
                url,
                {"email": "lockout@example.com", "password": "wrongpassword"},
                format="json",
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST

        # 10th attempt with CORRECT password should succeed
        response = api_client.post(
            url,
            {"email": "lockout@example.com", "password": "TestPass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data
        assert "access" in response.data["tokens"]
        assert "refresh" in response.data["tokens"]

    def test_ten_failed_attempts_locks_account(self, api_client, test_user):
        """Test that 10 failed attempts lock the account."""
        url = reverse("api:auth-login")

        # Make 10 failed login attempts
        for i in range(10):
            response = api_client.post(
                url,
                {"email": "lockout@example.com", "password": "wrongpassword"},
                format="json",
            )
            if i < 9:
                assert response.status_code == status.HTTP_400_BAD_REQUEST
            else:
                # 10th attempt should lock the account
                assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Next attempt should return 423 Locked
        response = api_client.post(
            url,
            {"email": "lockout@example.com", "password": "wrongpassword"},
            format="json",
        )
        assert response.status_code == status.HTTP_423_LOCKED
        assert "retry_after" in response.data
        assert response.data["retry_after"] > 0

    def test_locked_account_cannot_login_with_correct_password(
        self,
        api_client,
        test_user,
    ):
        """Test that locked account cannot login even with correct password."""
        url = reverse("api:auth-login")

        # Lock the account by making 10 failed attempts
        for i in range(10):
            api_client.post(
                url,
                {"email": "lockout@example.com", "password": "wrongpassword"},
                format="json",
            )

        # Try to login with CORRECT password - should be locked
        response = api_client.post(
            url,
            {"email": "lockout@example.com", "password": "TestPass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_423_LOCKED
        assert "retry_after" in response.data

    def test_successful_login_resets_attempt_counter(self, api_client, test_user):
        """Test that successful login resets the attempt counter."""
        url = reverse("api:auth-login")

        # Make 5 failed attempts
        for i in range(5):
            response = api_client.post(
                url,
                {"email": "lockout@example.com", "password": "wrongpassword"},
                format="json",
            )
            assert response.status_code == status.HTTP_400_BAD_REQUEST

        # Verify attempts were recorded
        attempts = AccountLockoutService.get_attempt_count("lockout@example.com")
        assert attempts == 5

        # Successful login
        response = api_client.post(
            url,
            {"email": "lockout@example.com", "password": "TestPass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

        # Attempt counter should be reset
        attempts = AccountLockoutService.get_attempt_count("lockout@example.com")
        assert attempts == 0

    def test_different_users_tracked_independently(self, api_client):
        """Test that different users have independent lockout tracking."""
        # Create two users
        user1 = User.objects.create_user(
            username="user1",
            email="user1@example.com",
            password="TestPass123",  # noqa: S106
        )
        user2 = User.objects.create_user(
            username="user2",
            email="user2@example.com",
            password="TestPass123",  # noqa: S106
        )

        url = reverse("api:auth-login")

        # Make 10 failed attempts for user1 (should lock)
        for i in range(10):
            api_client.post(
                url,
                {"email": "user1@example.com", "password": "wrongpassword"},
                format="json",
            )

        # user1 should be locked
        response = api_client.post(
            url,
            {"email": "user1@example.com", "password": "TestPass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_423_LOCKED

        # user2 should NOT be locked
        response = api_client.post(
            url,
            {"email": "user2@example.com", "password": "TestPass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_200_OK

    def test_failed_attempts_from_different_ips_same_user(self, api_client, test_user):
        """Test that failed attempts from different IPs for same user are tracked."""
        url = reverse("api:auth-login")

        # Make 5 failed attempts from IP 1
        for i in range(5):
            api_client.post(
                url,
                {"email": "lockout@example.com", "password": "wrongpassword"},
                format="json",
                HTTP_X_FORWARDED_FOR="192.168.1.1",
            )

        # Make 5 more failed attempts from IP 2 (total 10)
        for i in range(5):
            api_client.post(
                url,
                {"email": "lockout@example.com", "password": "wrongpassword"},
                format="json",
                HTTP_X_FORWARDED_FOR="192.168.1.2",
            )

        # Account should now be locked regardless of IP
        response = api_client.post(
            url,
            {"email": "lockout@example.com", "password": "TestPass123"},
            format="json",
            HTTP_X_FORWARDED_FOR="192.168.1.3",
        )
        assert response.status_code == status.HTTP_423_LOCKED

    def test_lockout_service_record_failed_attempt(self):
        """Test AccountLockoutService.record_failed_attempt()."""
        email = "test@example.com"

        # Record 9 attempts - should not lock
        for i in range(9):
            locked = AccountLockoutService.record_failed_attempt(
                email,
                "192.168.1.1",
            )
            assert locked is False

        # 10th attempt should lock
        locked = AccountLockoutService.record_failed_attempt(email, "192.168.1.1")
        assert locked is True

        # Verify lockout status
        is_locked, seconds_remaining = AccountLockoutService.is_locked(email)
        assert is_locked is True
        assert seconds_remaining > 0

    def test_lockout_service_is_locked(self):
        """Test AccountLockoutService.is_locked()."""
        email = "test@example.com"

        # Account not locked initially
        is_locked, seconds_remaining = AccountLockoutService.is_locked(email)
        assert is_locked is False
        assert seconds_remaining == 0

        # Lock the account
        for i in range(10):
            AccountLockoutService.record_failed_attempt(email, "192.168.1.1")

        # Account should be locked
        is_locked, seconds_remaining = AccountLockoutService.is_locked(email)
        assert is_locked is True
        assert seconds_remaining > 0
        assert seconds_remaining <= 3600  # Max 1 hour

    def test_lockout_service_reset_attempts(self):
        """Test AccountLockoutService.reset_attempts()."""
        email = "test@example.com"

        # Record some failed attempts
        for i in range(5):
            AccountLockoutService.record_failed_attempt(email, "192.168.1.1")

        # Verify attempts recorded
        attempts = AccountLockoutService.get_attempt_count(email)
        assert attempts == 5

        # Reset attempts
        AccountLockoutService.reset_attempts(email)

        # Attempts should be 0
        attempts = AccountLockoutService.get_attempt_count(email)
        assert attempts == 0

        # Lockout should be cleared
        is_locked, _ = AccountLockoutService.is_locked(email)
        assert is_locked is False

    def test_lockout_service_get_attempt_count(self):
        """Test AccountLockoutService.get_attempt_count()."""
        email = "test@example.com"

        # Initial count should be 0
        attempts = AccountLockoutService.get_attempt_count(email)
        assert attempts == 0

        # Record 3 attempts
        for i in range(3):
            AccountLockoutService.record_failed_attempt(email, "192.168.1.1")

        # Count should be 3
        attempts = AccountLockoutService.get_attempt_count(email)
        assert attempts == 3

    def test_lockout_message_includes_retry_time(self, api_client, test_user):
        """Test that lockout response includes retry_after in minutes."""
        url = reverse("api:auth-login")

        # Lock the account
        for i in range(10):
            api_client.post(
                url,
                {"email": "lockout@example.com", "password": "wrongpassword"},
                format="json",
            )

        # Next attempt should return lockout message
        response = api_client.post(
            url,
            {"email": "lockout@example.com", "password": "wrongpassword"},
            format="json",
        )
        assert response.status_code == status.HTTP_423_LOCKED
        assert "detail" in response.data
        assert "retry_after" in response.data
        # Message should mention minutes
        assert "minutes" in str(response.data["detail"]).lower()

    def test_email_case_insensitive(self, api_client, test_user):
        """Test that email is case-insensitive for lockout tracking."""
        url = reverse("api:auth-login")

        # Make failed attempts with different email cases
        for i in range(5):
            api_client.post(
                url,
                {"email": "LOCKOUT@EXAMPLE.COM", "password": "wrongpassword"},
                format="json",
            )

        for i in range(5):
            api_client.post(
                url,
                {"email": "lockout@example.com", "password": "wrongpassword"},
                format="json",
            )

        # Account should be locked (10 attempts total)
        response = api_client.post(
            url,
            {"email": "LockOut@Example.Com", "password": "TestPass123"},
            format="json",
        )
        assert response.status_code == status.HTTP_423_LOCKED

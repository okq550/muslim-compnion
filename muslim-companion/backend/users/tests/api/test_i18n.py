"""
Tests for internationalization (i18n) of authentication endpoints.

Tests that error messages are properly translated based on Accept-Language header.
"""

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient


@pytest.mark.django_db
class TestAuthenticationI18n:
    """Test internationalization of authentication error messages."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    def test_registration_error_in_arabic(self, api_client):
        """Test registration error message in Arabic."""
        url = reverse("api:auth-register")
        data = {
            "email": "invalid-email",
            "password": "Test123",
            "password_confirm": "Test123",
        }
        response = api_client.post(url, data, HTTP_ACCEPT_LANGUAGE="ar", format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Check for Arabic text in response
        assert "email" in response.data

    def test_registration_error_in_english(self, api_client):
        """Test registration error message in English."""
        url = reverse("api:auth-register")
        data = {
            "email": "test@example.com",
            "password": "short",  # Too short
            "password_confirm": "short",
        }
        response = api_client.post(url, data, HTTP_ACCEPT_LANGUAGE="en", format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data
        # English message should contain "8 characters"
        assert "8" in str(response.data)

    def test_login_error_in_arabic(self, api_client, user):
        """Test login error message in Arabic."""
        url = reverse("api:auth-login")
        data = {
            "email": "wrong@example.com",
            "password": "WrongPass123",
        }
        response = api_client.post(url, data, HTTP_ACCEPT_LANGUAGE="ar", format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        # Response should contain error detail
        assert "detail" in response.data

    def test_login_error_in_english(self, api_client, user):
        """Test login error message in English."""
        url = reverse("api:auth-login")
        data = {
            "email": "wrong@example.com",
            "password": "WrongPass123",
        }
        response = api_client.post(url, data, HTTP_ACCEPT_LANGUAGE="en", format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data

    def test_default_language_is_arabic(self, api_client):
        """Test that default language is Arabic when no Accept-Language header."""
        url = reverse("api:auth-register")
        data = {
            "email": "test@example.com",
            "password": "short",
            "password_confirm": "short",
        }
        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data

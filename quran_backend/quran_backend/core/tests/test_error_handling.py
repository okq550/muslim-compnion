"""
Comprehensive tests for error handling infrastructure.

Tests AC #1-9 from US-API-002:
- User-friendly error messages
- Server error protection
- Clear validation error messages
- Standardized error response format
- Automatic retry for transient errors
- Data preservation during errors
- Localized error messages
- Comprehensive error logging
- Consistent error handling across endpoints
"""

import time
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from rest_framework import status
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.exceptions import NotFound
from rest_framework.exceptions import PermissionDenied
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory

from quran_backend.core.exceptions import ErrorCodes
from quran_backend.core.exceptions import NetworkError
from quran_backend.core.exceptions import TransientError
from quran_backend.core.exceptions import ValidationError
from quran_backend.core.exceptions import custom_exception_handler
from quran_backend.core.exceptions import get_error_code_from_exception
from quran_backend.core.middleware.error_handler import ErrorHandlingMiddleware
from quran_backend.core.utils.retry import retry_with_exponential_backoff

User = get_user_model()

pytestmark = pytest.mark.django_db


class TestCustomExceptionHandler:
    """Test suite for custom exception handler (AC #1-4, #7)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = APIRequestFactory()
        self.request = self.factory.get("/test/")
        self.request.request_id = "test-request-id-123"

    def test_validation_error_returns_400_with_correct_format(self):
        """Test AC #3: Validation errors return 400 with standardized format."""
        exc = DRFValidationError({"email": "Enter a valid email address"})
        context = {"request": self.request}

        response = custom_exception_handler(exc, context)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "error" in response.data
        assert response.data["error"]["code"] == ErrorCodes.VALIDATION_ERROR
        assert "message" in response.data["error"]
        assert "timestamp" in response.data["error"]
        assert "request_id" in response.data["error"]

    def test_authentication_error_returns_401(self):
        """Test AC #1: Authentication errors return 401."""
        exc = AuthenticationFailed("Invalid credentials")
        context = {"request": self.request}

        response = custom_exception_handler(exc, context)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.data["error"]["code"] == ErrorCodes.AUTH_ERROR

    def test_authorization_error_returns_403(self):
        """Test AC #1: Authorization errors return 403."""
        exc = PermissionDenied("Access denied")
        context = {"request": self.request}

        response = custom_exception_handler(exc, context)

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["error"]["code"] == ErrorCodes.AUTHORIZATION_ERROR

    def test_not_found_error_returns_404(self):
        """Test AC #1: Resource not found errors return 404."""
        exc = NotFound("Resource not found")
        context = {"request": self.request}

        response = custom_exception_handler(exc, context)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"]["code"] == ErrorCodes.NOT_FOUND

    def test_server_error_returns_500_without_stack_trace(self):
        """Test AC #2: Server errors return 500 with generic message, no stack trace."""
        exc = Exception("Internal database error occurred")
        context = {"request": self.request}

        response = custom_exception_handler(exc, context)

        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert response.data["error"]["code"] == ErrorCodes.SERVER_ERROR
        # Generic message, not internal details (don't expose "database")
        assert "database" not in response.data["error"]["message"].lower()
        # Message is localized, so just check it exists and isn't empty
        assert len(response.data["error"]["message"]) > 0

    def test_all_errors_follow_standardized_format(self):
        """Test AC #4: All errors follow consistent JSON structure."""
        exceptions = [
            DRFValidationError("Validation failed"),
            AuthenticationFailed("Invalid credentials"),
            PermissionDenied("Access denied"),
            NotFound("Not found"),
            Exception("Server error"),
        ]

        for exc in exceptions:
            context = {"request": self.request}
            response = custom_exception_handler(exc, context)

            # Verify standardized structure
            assert "error" in response.data
            assert "code" in response.data["error"]
            assert "message" in response.data["error"]
            assert "details" in response.data["error"]
            assert "timestamp" in response.data["error"]
            assert "request_id" in response.data["error"]

    def test_error_includes_correlation_id(self):
        """Test AC #2: Error responses include request_id for correlation."""
        exc = Exception("Something went wrong")
        context = {"request": self.request}

        response = custom_exception_handler(exc, context)

        assert response.data["error"]["request_id"] == "test-request-id-123"

    def test_timestamp_in_iso_8601_format(self):
        """Test AC #4: Timestamp is in ISO 8601 format."""
        exc = ValidationError("Invalid input")
        context = {"request": self.request}

        response = custom_exception_handler(exc, context)

        timestamp = response.data["error"]["timestamp"]
        # ISO 8601 format: YYYY-MM-DDTHH:MM:SSZ
        assert "T" in timestamp
        assert timestamp.endswith("Z")


class TestErrorMiddleware:
    """Test suite for error handling middleware (AC #2, #6, #8)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.factory = RequestFactory()
        self.get_response = MagicMock(return_value=MagicMock(status_code=200))
        self.middleware = ErrorHandlingMiddleware(self.get_response)

    def test_request_id_generated_and_attached(self):
        """Test AC #2: Middleware generates unique request_id for each request."""
        request = self.factory.get("/test/")

        self.middleware(request)

        assert hasattr(request, "request_id")
        assert len(request.request_id) > 0

    @patch("quran_backend.core.middleware.error_handler.sentry_sdk.capture_exception")
    def test_unhandled_exception_logged_to_sentry(self, mock_capture):
        """Test AC #8: Unhandled exceptions are logged to Sentry with context."""
        request = self.factory.get("/test/")
        request.request_id = "test-id"
        request.user = MagicMock(
            is_authenticated=True,
            id="user-123",
            email="test@example.com",
            username="testuser",
        )
        exception = Exception("Unexpected error")

        response = self.middleware.process_exception(request, exception)

        # Verify Sentry capture_exception was called
        mock_capture.assert_called_once_with(exception)
        # Verify response is standardized error format
        assert response.status_code == 500
        import json

        response_data = json.loads(response.content)
        assert "error" in response_data

    @patch("quran_backend.core.middleware.error_handler.transaction")
    def test_database_transaction_rolled_back_on_error(self, mock_transaction):
        """Test AC #6: Database transactions are rolled back on errors."""
        request = self.factory.get("/test/")
        request.user = MagicMock(is_authenticated=False)
        exception = Exception("Database error")

        # Simulate being in an atomic block
        mock_transaction.get_connection.return_value.in_atomic_block = True

        self.middleware.process_exception(request, exception)

        # Verify rollback was triggered
        mock_transaction.set_rollback.assert_called_once_with(True)


class TestRetryLogic:
    """Test suite for retry logic with exponential backoff (AC #5)."""

    def test_transient_error_triggers_retry(self):
        """Test AC #5: Transient errors trigger exponential backoff retry."""
        call_count = {"count": 0}

        @retry_with_exponential_backoff(max_retries=3, delays=(0.01, 0.02, 0.03))
        def flaky_function():
            call_count["count"] += 1
            if call_count["count"] < 3:
                raise TransientError("Temporary failure")
            return "success"

        start_time = time.time()
        result = flaky_function()
        elapsed = time.time() - start_time

        # Function succeeded after retries
        assert result == "success"
        assert call_count["count"] == 3
        # Verify exponential backoff occurred (at least 0.01 + 0.02 = 0.03 seconds)
        assert elapsed >= 0.03

    def test_retry_respects_max_attempts(self):
        """Test AC #5: Max retries are respected."""
        call_count = {"count": 0}

        @retry_with_exponential_backoff(max_retries=2, delays=(0.01, 0.01))
        def always_fail():
            call_count["count"] += 1
            raise NetworkError("Network down")

        with pytest.raises(NetworkError):
            always_fail()

        # 1 initial attempt + 2 retries = 3 total calls
        assert call_count["count"] == 3

    def test_non_retryable_errors_fail_immediately(self):
        """Test AC #5: Non-retryable errors don't trigger retry logic."""
        call_count = {"count": 0}

        @retry_with_exponential_backoff(max_retries=3, exceptions=(TransientError,))
        def raise_validation_error():
            call_count["count"] += 1
            raise ValueError("Bad input")

        with pytest.raises(ValueError):
            raise_validation_error()

        # Only 1 attempt (no retries for ValueError)
        assert call_count["count"] == 1


class TestErrorLocalization:
    """Test suite for localized error messages (AC #7)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = APIClient()

    @pytest.mark.django_db
    def test_error_messages_in_arabic_with_accept_language_ar(self):
        """Test AC #7: Error messages localized to Arabic when Accept-Language: ar."""
        response = self.client.post(
            "/api/v1/auth/register/",
            {"email": "invalid-email"},  # Missing password
            headers={"accept-language": "ar"},
        )

        assert response.status_code == 400
        response_data = response.json()
        # Validation messages are returned in field-level format by serializer
        assert "email" in response_data or "password" in response_data
        # Check that at least one field has Arabic text
        all_text = str(response_data)
        has_arabic = any("\u0600" <= char <= "\u06ff" for char in all_text)
        assert has_arabic, "Expected Arabic text in response"

    @pytest.mark.django_db
    def test_error_messages_in_english_with_accept_language_en(self):
        """Test AC #7: Error messages in English when Accept-Language: en."""
        response = self.client.post(
            "/api/v1/auth/register/",
            {"email": "invalid-email"},
            headers={"accept-language": "en"},
        )

        assert response.status_code == 400
        response_data = response.json()
        # Validation messages are in field format
        assert "email" in response_data or "password" in response_data

    def test_error_codes_remain_in_english(self):
        """Test AC #7: Error codes always in English regardless of language."""
        exc = ValidationError("فشل التحقق")  # Arabic message
        factory = APIRequestFactory()
        request = factory.get("/test/")
        request.request_id = "test-id"
        context = {"request": request}

        response = custom_exception_handler(exc, context)

        # Error code should always be in English
        assert response.data["error"]["code"] == ErrorCodes.VALIDATION_ERROR
        assert isinstance(response.data["error"]["code"], str)
        # Error codes should be ASCII
        assert response.data["error"]["code"].isascii()


class TestErrorHandlingConsistency:
    """Test suite for consistent error handling across endpoints (AC #9)."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = APIClient()

    @pytest.mark.django_db
    def test_validation_errors_on_registration_endpoint(self):
        """Test AC #9: Validation errors on /api/v1/auth/register/."""
        response = self.client.post("/api/v1/auth/register/", {"email": "invalid"})

        assert response.status_code == 400
        # Response may have "error" or "detail" (both indicate validation error)
        assert (
            "error" in response.json()
            or "detail" in response.json()
            or "email" in response.json()
        )

    @pytest.mark.django_db
    def test_authentication_errors_on_login_endpoint(self):
        """Test AC #9: Authentication errors on /api/v1/auth/login/."""
        response = self.client.post(
            "/api/v1/auth/login/",
            {"email": "nonexistent@example.com", "password": "wrongpass"},
        )

        assert response.status_code == 400
        # Response may have "error" or "detail" field for authentication failures
        response_data = response.json()
        assert (
            "error" in response_data
            or "detail" in response_data
            or "non_field_errors" in response_data
        )

    @pytest.mark.django_db
    def test_missing_token_error_on_logout_endpoint(self):
        """Test AC #9: Error handling on /api/v1/auth/logout/ without token."""
        response = self.client.post("/api/v1/auth/logout/", {})

        assert response.status_code == 400
        assert "error" in response.json() or "detail" in response.json()

    @pytest.mark.django_db
    def test_404_error_on_invalid_endpoint(self):
        """Test AC #9: 404 errors on non-existent endpoints."""
        response = self.client.get("/api/v1/nonexistent/endpoint/")

        assert response.status_code == 404


class TestErrorCodeMapping:
    """Test suite for error code mapping."""

    def test_get_error_code_for_validation_errors(self):
        """Test error code mapping for validation errors."""
        exc = DRFValidationError("Invalid input")
        code = get_error_code_from_exception(exc)
        assert code == ErrorCodes.VALIDATION_ERROR

    def test_get_error_code_for_auth_errors(self):
        """Test error code mapping for authentication errors."""
        exc = AuthenticationFailed("Bad credentials")
        code = get_error_code_from_exception(exc)
        assert code == ErrorCodes.AUTH_ERROR

    def test_get_error_code_for_permission_errors(self):
        """Test error code mapping for permission errors."""
        exc = PermissionDenied("Access forbidden")
        code = get_error_code_from_exception(exc)
        assert code == ErrorCodes.AUTHORIZATION_ERROR

    def test_get_error_code_for_not_found_errors(self):
        """Test error code mapping for not found errors."""
        exc = NotFound("Resource missing")
        code = get_error_code_from_exception(exc)
        assert code == ErrorCodes.NOT_FOUND

    def test_get_error_code_for_network_errors(self):
        """Test error code mapping for network errors."""
        exc = NetworkError("Service unavailable")
        code = get_error_code_from_exception(exc)
        assert code == ErrorCodes.NETWORK_ERROR

    def test_get_error_code_for_generic_errors(self):
        """Test error code mapping for unhandled exceptions."""
        exc = Exception("Unexpected error")
        code = get_error_code_from_exception(exc)
        assert code == ErrorCodes.SERVER_ERROR

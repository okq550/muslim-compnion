"""
Custom exceptions and exception handler for standardized API error responses.

Implements AC #1-4, #7 from US-API-002:
- User-friendly error messages
- Standardized error response format
- Localized error messages (Arabic/English)
- Error code constants
"""

import uuid
from datetime import UTC
from datetime import datetime

from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler


# Error Code Constants (AC #4)
class ErrorCodes:
    """Standardized error codes for all API errors."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    AUTH_ERROR = "AUTH_ERROR"
    AUTHORIZATION_ERROR = "AUTHORIZATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    NETWORK_ERROR = "NETWORK_ERROR"
    SERVER_ERROR = "SERVER_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    BACKUP_ERROR = "BACKUP_ERROR"
    ENCRYPTION_ERROR = "ENCRYPTION_ERROR"
    RESTORE_ERROR = "RESTORE_ERROR"
    INTEGRITY_ERROR = "INTEGRITY_ERROR"


# Custom Exception Classes (AC #3, #5)
class ValidationError(APIException):
    """Raised when data validation fails."""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = _("Validation failed. Please check your input.")
    default_code = ErrorCodes.VALIDATION_ERROR


class AuthenticationError(APIException):
    """Raised when authentication fails."""

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = _("Invalid credentials provided.")
    default_code = ErrorCodes.AUTH_ERROR


class AuthorizationError(APIException):
    """Raised when user lacks permission."""

    status_code = status.HTTP_403_FORBIDDEN
    default_detail = _("You do not have permission to access this resource.")
    default_code = ErrorCodes.AUTHORIZATION_ERROR


class ResourceNotFoundError(APIException):
    """Raised when requested resource doesn't exist."""

    status_code = status.HTTP_404_NOT_FOUND
    default_detail = _("The requested resource was not found.")
    default_code = ErrorCodes.NOT_FOUND


class NetworkError(APIException):
    """Raised when external service communication fails."""

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _("Service temporarily unavailable. Please try again later.")
    default_code = ErrorCodes.NETWORK_ERROR


class TransientError(APIException):
    """
    Raised for temporary errors that should be retried.
    Used by retry decorator to identify retryable errors.
    """

    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = _("Temporary error occurred. Retrying...")
    default_code = ErrorCodes.NETWORK_ERROR


class RateLimitError(APIException):
    """Raised when rate limit is exceeded."""

    status_code = status.HTTP_429_TOO_MANY_REQUESTS
    default_detail = _("Too many requests. Please try again later.")
    default_code = ErrorCodes.RATE_LIMIT_EXCEEDED


class BackupFailedError(APIException):
    """Raised when backup operation fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _("Backup operation failed. Please contact system administrator.")
    default_code = ErrorCodes.BACKUP_ERROR


class EncryptionFailedError(APIException):
    """Raised when encryption or decryption fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _(
        "Encryption operation failed. Please contact system administrator."
    )
    default_code = ErrorCodes.ENCRYPTION_ERROR


class RestoreFailedError(APIException):
    """Raised when database restoration fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _(
        "Database restoration failed. Please contact system administrator."
    )
    default_code = ErrorCodes.RESTORE_ERROR


class IntegrityCheckFailedError(APIException):
    """Raised when backup integrity verification fails."""

    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    default_detail = _("Backup integrity check failed. Backup may be corrupted.")
    default_code = ErrorCodes.INTEGRITY_ERROR


def get_error_code_from_exception(exc):
    """
    Map exception types to standardized error codes.

    Args:
        exc: Exception instance

    Returns:
        str: Error code constant
    """
    from django.core.exceptions import PermissionDenied
    from django.core.exceptions import ValidationError as DjangoValidationError
    from django.http import Http404
    from rest_framework.exceptions import AuthenticationFailed
    from rest_framework.exceptions import NotAuthenticated
    from rest_framework.exceptions import NotFound
    from rest_framework.exceptions import PermissionDenied as DRFPermissionDenied
    from rest_framework.exceptions import Throttled
    from rest_framework.exceptions import ValidationError as DRFValidationError

    # Map exception types to error codes
    if isinstance(exc, (DRFValidationError, DjangoValidationError, ValidationError)):
        return ErrorCodes.VALIDATION_ERROR
    if isinstance(exc, (NotAuthenticated, AuthenticationFailed, AuthenticationError)):
        return ErrorCodes.AUTH_ERROR
    if isinstance(exc, (PermissionDenied, DRFPermissionDenied, AuthorizationError)):
        return ErrorCodes.AUTHORIZATION_ERROR
    if isinstance(exc, (Http404, NotFound, ResourceNotFoundError)):
        return ErrorCodes.NOT_FOUND
    if isinstance(exc, (NetworkError, TransientError)):
        return ErrorCodes.NETWORK_ERROR
    if isinstance(exc, (Throttled, RateLimitError)):
        return ErrorCodes.RATE_LIMIT_EXCEEDED
    return ErrorCodes.SERVER_ERROR


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns standardized error responses.

    Implements AC #1-4, #7 from US-API-002:
    - Transforms all exceptions to standardized format
    - Adds request_id (correlation ID from middleware)
    - Adds timestamp in ISO 8601 format
    - Maps exception types to error codes
    - Wraps error messages for localization

    Also implements AC #3, #4 from US-API-005:
    - Handles rate limit (429) responses with Retry-After header
    - Provides user-friendly localized rate limit messages

    Returns errors in the format:
    {
        "error": {
            "code": "ERROR_CODE",
            "message": "User-friendly message",
            "details": {...},
            "timestamp": "2025-11-07T12:34:56Z",
            "request_id": "550e8400-e29b-41d4-a716-446655440000"
        }
    }
    """
    from rest_framework.exceptions import Throttled

    # Special handling for Throttled exceptions (US-API-005, AC #3, #4, #8)
    if isinstance(exc, Throttled):
        # Get request from context
        request = context.get("request")
        request_id = getattr(request, "request_id", str(uuid.uuid4()))

        # Calculate retry_after in seconds
        retry_after = int(exc.wait) if exc.wait else 60

        # Track rate limit violation and detect abuse (AC #8)
        from quran_backend.core.utils.abuse_detection import track_rate_limit_violation

        # Determine identifier (user ID or IP address)
        if request.user and request.user.is_authenticated:
            identifier = f"user_{request.user.id}"
        else:
            # Get IP address (handle X-Forwarded-For for load balancers)
            x_forwarded_for = request.headers.get("x-forwarded-for")
            if x_forwarded_for:
                identifier = x_forwarded_for.split(",")[0].strip()
            else:
                identifier = request.META.get("REMOTE_ADDR", "unknown")

        # Track violation
        endpoint = request.path
        track_rate_limit_violation(
            identifier,
            endpoint,
            context={
                "method": request.method,
                "request_id": request_id,
                "user_agent": request.headers.get("user-agent", ""),
            },
        )

        # Build rate limit error response
        response_data = {
            "error": {
                "code": ErrorCodes.RATE_LIMIT_EXCEEDED,
                "message": _(
                    "Too many requests. Please try again in {seconds} seconds."
                ).format(
                    seconds=retry_after,
                ),
                "details": {
                    "retry_after": retry_after,
                },
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "request_id": request_id,
            },
        }

        response = Response(response_data, status=status.HTTP_429_TOO_MANY_REQUESTS)
        # Add Retry-After header (AC #4)
        response["Retry-After"] = str(retry_after)
        return response

    # Call DRF's default exception handler first
    response = drf_exception_handler(exc, context)

    # If DRF didn't handle it, create a generic 500 response
    if response is None:
        response = Response(
            {"detail": _("Something went wrong. Please try again.")},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    # Get request from context
    request = context.get("request")

    # Get request_id from request (set by ErrorHandlingMiddleware)
    request_id = getattr(request, "request_id", str(uuid.uuid4()))

    # Get error code from exception type
    error_code = get_error_code_from_exception(exc)

    # Extract user-friendly message
    if hasattr(exc, "detail"):
        if isinstance(exc.detail, dict):
            # For field-level validation errors, extract first error
            first_field = next(iter(exc.detail.keys()), None)
            if first_field:
                first_error = exc.detail[first_field]
                if isinstance(first_error, list):
                    message = str(first_error[0])
                else:
                    message = str(first_error)
            else:
                message = _("Something went wrong. Please try again.")
        elif isinstance(exc.detail, list):
            message = str(exc.detail[0]) if exc.detail else str(exc)
        else:
            message = str(exc.detail)
    else:
        message = str(exc)

    # For server errors (500), use generic message (AC #2)
    if response.status_code >= 500:
        message = _("Something went wrong. Please try again.")
        details = {}  # Don't expose internal details
    else:
        # Include validation details for client errors
        details = response.data if isinstance(response.data, dict) else {}

    # Build standardized error response (AC #4)
    standardized_response = {
        "error": {
            "code": error_code,
            "message": message,
            "details": details,
            "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
            "request_id": request_id,
        },
    }

    response.data = standardized_response
    return response

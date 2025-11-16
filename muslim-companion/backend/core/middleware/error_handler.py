"""
Error Handling Middleware for request ID generation and exception logging.

Implements AC #2, #6, #8 from US-API-002:
- Generate unique request_id for each request
- Catch unhandled exceptions and log to Sentry
- Ensure database transactions are rolled back
- Enrich Sentry context with request and user info
"""

import logging
import uuid
from datetime import UTC
from datetime import datetime

import redis
import sentry_sdk
from django.conf import settings
from django.db import transaction
from django.http import JsonResponse
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class ErrorHandlingMiddleware:
    """
    Middleware for request tracking, exception handling, and error logging.

    Responsibilities:
    1. Generate unique request_id for correlation
    2. Attach request_id to request object
    3. Catch unhandled exceptions
    4. Log errors to Sentry with full context
    5. Ensure database transaction rollback on errors
    6. Return standardized error response
    """

    def __init__(self, get_response):
        """Initialize middleware with get_response callable."""
        self.get_response = get_response

    def __call__(self, request):
        """
        Process request and generate request_id.

        Args:
            request: Django HttpRequest

        Returns:
            HttpResponse
        """
        # Generate unique request ID for this request
        request.request_id = str(uuid.uuid4())

        # Attach request_id to Sentry scope
        sentry_sdk.set_tag("request_id", request.request_id)
        sentry_sdk.set_context(
            "request",
            {
                "url": request.build_absolute_uri(),
                "method": request.method,
                "query_params": dict(request.GET),
            },
        )

        # Add user context if authenticated
        if hasattr(request, "user") and request.user.is_authenticated:
            sentry_sdk.set_user(
                {
                    "id": request.user.id,
                    "email": request.user.email,
                    "username": request.user.username,
                },
            )

        # Process request
        response = self.get_response(request)

        return response

    def process_exception(self, request, exception):
        """
        Handle unhandled exceptions.

        This method is called when a view raises an exception that wasn't
        caught by the exception handler.

        Args:
            request: Django HttpRequest
            exception: Raised exception

        Returns:
            JsonResponse with standardized error format
        """
        # Get request_id (should be set in __call__, but fallback just in case)
        request_id = getattr(request, "request_id", str(uuid.uuid4()))

        # Special handling for Redis errors (graceful degradation - US-API-003 AC #5)
        if isinstance(exception, redis.exceptions.RedisError):
            logger.warning(
                f"Redis error (graceful degradation active): {type(exception).__name__}",
                exc_info=True,
                extra={
                    "request_id": request_id,
                    "cache_operation": "unknown",
                },
            )
            # Log to Sentry as warning, not error (cache failures are non-critical)
            sentry_sdk.set_tag("error_type", "cache_error")
            sentry_sdk.capture_message(
                f"Redis cache unavailable: {exception}",
                level="warning",
            )
            # Don't return error response - let request continue with database fallback
            # The IGNORE_EXCEPTIONS setting in cache config handles this
            return None

        # Log to Sentry with full context (AC #8)
        # Enrich context with request info
        sentry_sdk.set_tag("request_id", request_id)
        sentry_sdk.set_context(
            "request",
            {
                "url": request.build_absolute_uri(),
                "method": request.method,
                "headers": self._get_safe_headers(request),
                "query_params": dict(request.GET),
            },
        )

        # Add user context if authenticated
        if hasattr(request, "user") and request.user.is_authenticated:
            sentry_sdk.set_user(
                {
                    "id": request.user.id,
                    "email": request.user.email,
                    "username": request.user.username,
                },
            )

        # Add environment info
        sentry_sdk.set_tag(
            "environment",
            settings.ENVIRONMENT if hasattr(settings, "ENVIRONMENT") else "unknown",
        )

        # Capture exception to Sentry
        sentry_sdk.capture_exception(exception)

        # Ensure database transaction rollback (AC #6)
        if transaction.get_connection().in_atomic_block:
            transaction.set_rollback(True)

        # Log locally as well
        logger.error(
            f"Unhandled exception: {type(exception).__name__}",
            exc_info=True,
            extra={
                "request_id": request_id,
                "url": request.build_absolute_uri(),
                "method": request.method,
                "user_id": request.user.id
                if hasattr(request, "user") and request.user.is_authenticated
                else None,
            },
        )

        # Return standardized error response (AC #2)
        error_response = {
            "error": {
                "code": "SERVER_ERROR",
                "message": _("Something went wrong. Please try again."),
                "details": {},
                "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                "request_id": request_id,
            },
        }

        return JsonResponse(error_response, status=500)

    def _get_safe_headers(self, request):
        """
        Extract safe headers for logging (filter sensitive data).

        Args:
            request: Django HttpRequest

        Returns:
            dict: Safe headers with sensitive values filtered
        """
        # List of headers to exclude from logging
        sensitive_headers = {
            "HTTP_AUTHORIZATION",
            "HTTP_COOKIE",
            "HTTP_X_CSRF_TOKEN",
            "HTTP_X_API_KEY",
        }

        safe_headers = {}
        for key, value in request.META.items():
            if key.startswith("HTTP_") and key not in sensitive_headers:
                # Remove HTTP_ prefix for cleaner logging
                header_name = key[5:].replace("_", "-").title()
                safe_headers[header_name] = value

        return safe_headers

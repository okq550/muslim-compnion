"""
Error Response Serializers for API Documentation (US-API-008).

These serializers document the standard error response format used across the API.
They are used with @extend_schema decorators for OpenAPI documentation generation.
"""

from rest_framework import serializers


class ErrorDetailSerializer(serializers.Serializer):
    """Serializer for individual field-level error details."""

    field = serializers.CharField(
        help_text="Field name that caused the validation error",
    )
    message = serializers.CharField(
        help_text="Human-readable error message describing the issue",
    )


class ErrorResponseSerializer(serializers.Serializer):
    """
    Standard error response format for all API errors.

    All API endpoints return errors in this consistent format to simplify
    client-side error handling and provide clear troubleshooting information.

    **Error Codes:**
    - VALIDATION_ERROR: Invalid request data (HTTP 400)
    - AUTHENTICATION_ERROR: Missing or invalid authentication (HTTP 401)
    - AUTHORIZATION_ERROR: Insufficient permissions (HTTP 403)
    - NOT_FOUND: Resource not found (HTTP 404)
    - RATE_LIMIT_EXCEEDED: Too many requests (HTTP 429)
    - INTERNAL_ERROR: Server error (HTTP 500)

    **Troubleshooting:**
    Use the request_id to correlate errors with server logs for debugging.
    """

    error = serializers.CharField(
        help_text=(
            "Error code for programmatic error handling "
            "(e.g., VALIDATION_ERROR, AUTHENTICATION_ERROR)"
        ),
    )
    message = serializers.CharField(
        help_text="Human-readable error message describing what went wrong",
    )
    request_id = serializers.UUIDField(
        help_text=(
            "Unique correlation ID for tracking this request in logs "
            "(use for troubleshooting)"
        ),
    )
    details = ErrorDetailSerializer(
        many=True,
        required=False,
        help_text=(
            "Optional array of field-specific validation errors "
            "(only present for VALIDATION_ERROR)"
        ),
    )

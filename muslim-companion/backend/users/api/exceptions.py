"""Custom exception handler for standardized API error responses (AC #16)."""

from django.conf import settings
from rest_framework.views import exception_handler


def custom_exception_handler(exc, context):
    """
    Custom exception handler that returns standardized error responses.

    Returns errors in the format:
    {
        "error": {
            "code": "error_code",
            "message": "Error message in English/Arabic",
            "details": {...}
        }
    }

    In production, sanitizes exception messages to avoid leaking sensitive
    information about system internals.
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Sanitize message in production to avoid exposing internal details
        if settings.DEBUG:
            # In development, show full exception message for debugging
            message = str(exc)
        # In production, use generic message from response data
        # Extract first error message if available, otherwise use status text
        elif isinstance(response.data, dict):
            # Get first error message from details
            first_error = next(iter(response.data.values()), None)
            if isinstance(first_error, list) and first_error:
                message = str(first_error[0])
            elif isinstance(first_error, str):
                message = first_error
            else:
                message = response.status_text
        else:
            message = response.status_text

        # Standardize error response format (AC #16)
        custom_response_data = {
            "error": {
                "code": response.status_code,
                "message": message,
                "details": response.data,
            },
        }

        response.data = custom_response_data

    return response

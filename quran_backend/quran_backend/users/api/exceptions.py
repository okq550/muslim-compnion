"""Custom exception handler for standardized API error responses (AC #16)."""

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
    """
    # Call REST framework's default exception handler first
    response = exception_handler(exc, context)

    if response is not None:
        # Standardize error response format (AC #16)
        custom_response_data = {
            "error": {
                "code": response.status_code,
                "message": str(exc),
                "details": response.data,
            },
        }

        response.data = custom_response_data

    return response

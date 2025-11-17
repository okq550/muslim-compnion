"""Custom throttling classes for authentication endpoints (AC #10, #11, #12)."""

from rest_framework.throttling import AnonRateThrottle


class AuthEndpointThrottle(AnonRateThrottle):
    """
    Rate limiting for authentication endpoints.

    Limits anonymous users to 5 requests per minute to prevent brute force attacks.
    """

    rate = "5/min"

"""Custom throttling classes for API rate limiting (US-API-005)."""

from django.conf import settings
from rest_framework.throttling import AnonRateThrottle as DRFAnonRateThrottle
from rest_framework.throttling import UserRateThrottle as DRFUserRateThrottle


class AnonRateThrottle(DRFAnonRateThrottle):
    """
    Rate limiting for anonymous users (AC #2).

    Limits anonymous users to 20 requests per minute per IP address.
    Uses Redis cache for distributed rate tracking.

    Cache key format: throttle_anon_{ip_address}
    Rate: 20 requests per minute per IP
    """

    scope = "anon"

    def allow_request(self, request, view):
        """
        Check if request should be allowed based on rate limit.

        Also checks whitelist for bypassing rate limits.
        """
        # Check if IP is whitelisted (AC #7)
        ip_address = self.get_ident(request)
        if ip_address in settings.RATE_LIMIT_WHITELIST:
            return True

        return super().allow_request(request, view)


class UserRateThrottle(DRFUserRateThrottle):
    """
    Rate limiting for authenticated users (AC #2).

    Limits authenticated users to 100 requests per minute per user ID.
    Uses Redis cache for distributed rate tracking.

    Cache key format: throttle_user_{user_id}
    Rate: 100 requests per minute per user
    """

    scope = "user"

    def allow_request(self, request, view):
        """
        Check if request should be allowed based on rate limit.

        Also checks whitelist and admin bypass.
        """
        # Check if user is staff/superuser (AC #7)
        if request.user and request.user.is_authenticated:
            if request.user.is_staff or request.user.is_superuser:
                return True

            # Check if user ID is whitelisted
            if str(request.user.id) in settings.RATE_LIMIT_WHITELIST:
                return True

        return super().allow_request(request, view)

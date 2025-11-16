"""Middleware to add rate limit headers to responses (US-API-005, AC #5)."""

import time

from django.utils.deprecation import MiddlewareMixin


class RateLimitHeadersMiddleware(MiddlewareMixin):
    """
    Middleware that adds rate limit headers to all API responses (AC #5).

    Headers added:
    - X-RateLimit-Limit: Maximum requests allowed in window
    - X-RateLimit-Remaining: Requests remaining in current window
    - X-RateLimit-Reset: Unix timestamp when window resets
    """

    def process_response(self, request, response):
        """Add rate limit headers to response."""
        # Extract throttle info from request if available
        throttle_durations = getattr(request, "throttle_durations", None)
        throttle_history = getattr(request, "throttle_history", None)

        if throttle_durations and throttle_history:
            # Calculate rate limit info from throttle history
            # throttle_durations is a list of time windows in seconds (e.g., [60] for 1 minute)
            # throttle_history is a dict mapping cache keys to list of request timestamps

            # Get the first throttle duration (minute-based window)
            duration = throttle_durations[0] if throttle_durations else 60

            # Get the throttle history for this request
            for cache_key, history in throttle_history.items():
                if history:
                    # Calculate limit based on cache key scope
                    if "anon" in cache_key:
                        limit = 20  # Anonymous rate limit
                    elif "user" in cache_key:
                        limit = 100  # User rate limit
                    else:
                        limit = 20  # Default to anonymous limit

                    # Remaining = limit - current request count
                    remaining = max(0, limit - len(history))

                    # Reset time = current time + duration - age of oldest request
                    now = time.time()
                    if history:
                        oldest_request_time = min(history)
                        time_since_oldest = now - oldest_request_time
                        time_until_reset = max(0, duration - time_since_oldest)
                    else:
                        time_until_reset = duration

                    reset_timestamp = int(now + time_until_reset)

                    # Add headers to response
                    response["X-RateLimit-Limit"] = str(limit)
                    response["X-RateLimit-Remaining"] = str(remaining)
                    response["X-RateLimit-Reset"] = str(reset_timestamp)
                    break  # Only process first throttle scope

        return response

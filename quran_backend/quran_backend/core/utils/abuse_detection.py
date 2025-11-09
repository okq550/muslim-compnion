"""Abuse detection utilities for rate limiting (US-API-005, AC #8)."""

import logging

import sentry_sdk
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def track_rate_limit_violation(user_id_or_ip, endpoint, context=None):
    """
    Track rate limit violation and detect abuse patterns (AC #8).

    Logs violations to Sentry, increments violation counter in Redis,
    and triggers alerts for repeat offenders (10+ violations per hour).

    Args:
        user_id_or_ip: User ID (authenticated) or IP address (anonymous)
        endpoint: API endpoint that was rate limited
        context: Additional context dict (optional)

    Returns:
        dict: Violation tracking info including total count and whether threshold exceeded
    """
    if context is None:
        context = {}

    # Build Redis key for tracking violations (1-hour TTL)
    cache_key = f"rate_violations:{user_id_or_ip}:hour"

    # Increment violation counter
    violation_count = cache.get(cache_key, 0)
    violation_count += 1
    cache.set(cache_key, violation_count, timeout=3600)  # 1 hour TTL

    # Log to Sentry with full context
    with sentry_sdk.push_scope() as scope:
        scope.set_tag("violation_type", "rate_limit")
        scope.set_tag("endpoint", endpoint)
        scope.set_tag("user_id_or_ip", user_id_or_ip)
        scope.set_context(
            "rate_limit_violation",
            {
                "user_id_or_ip": user_id_or_ip,
                "endpoint": endpoint,
                "violation_count": violation_count,
                "threshold": settings.RATE_LIMIT_ABUSE_THRESHOLD,
                **context,
            },
        )

        # Check if threshold exceeded (10+ violations per hour)
        if violation_count >= settings.RATE_LIMIT_ABUSE_THRESHOLD:
            # Critical alert for repeat offenders
            logger.critical(
                f"Rate limit abuse detected: {user_id_or_ip} exceeded threshold "
                f"({violation_count} violations in 1 hour, threshold: {settings.RATE_LIMIT_ABUSE_THRESHOLD})"
            )
            sentry_sdk.capture_message(
                f"Rate limit abuse threshold exceeded: {user_id_or_ip}",
                level="error",
            )

            # Optionally implement temporary ban (AC #8)
            # For now, just track and alert - actual banning can be added later
            # ban_key = f"rate_ban:{user_id_or_ip}"
            # cache.set(ban_key, True, timeout=settings.RATE_LIMIT_BAN_DURATION)
        else:
            # Regular violation logging (info level)
            logger.info(
                f"Rate limit violation: {user_id_or_ip} on {endpoint} "
                f"(count: {violation_count}/{settings.RATE_LIMIT_ABUSE_THRESHOLD})"
            )
            sentry_sdk.capture_message(
                f"Rate limit violation: {user_id_or_ip}",
                level="info",
            )

    return {
        "violation_count": violation_count,
        "threshold_exceeded": violation_count >= settings.RATE_LIMIT_ABUSE_THRESHOLD,
        "threshold": settings.RATE_LIMIT_ABUSE_THRESHOLD,
    }


def is_temporarily_banned(user_id_or_ip):
    """
    Check if user/IP is temporarily banned due to abuse.

    Args:
        user_id_or_ip: User ID or IP address to check

    Returns:
        bool: True if temporarily banned, False otherwise
    """
    ban_key = f"rate_ban:{user_id_or_ip}"
    return cache.get(ban_key, False)

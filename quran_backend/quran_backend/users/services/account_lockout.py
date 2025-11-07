"""
Account lockout service for protecting against brute force attacks.

Tracks failed login attempts per email address and locks accounts after
10 failed attempts within 1 hour. Uses Redis for persistent storage.
"""

import logging
import time

from django.core.cache import cache

logger = logging.getLogger(__name__)

# Constants
MAX_ATTEMPTS = 10
LOCKOUT_DURATION = 3600  # 1 hour in seconds
ATTEMPT_WINDOW = 3600  # 1 hour in seconds


class AccountLockoutService:
    """
    Service for tracking failed login attempts and account lockouts.

    Uses Redis for persistent storage with automatic expiration.
    Thread-safe and supports distributed deployments.
    """

    @staticmethod
    def _get_attempt_key(email: str) -> str:
        """Generate Redis key for attempt counter."""
        return f"auth:attempts:{email.lower()}"

    @staticmethod
    def _get_lockout_key(email: str) -> str:
        """Generate Redis key for lockout status."""
        return f"auth:lockout:{email.lower()}"

    @classmethod
    def record_failed_attempt(
        cls,
        email: str,
        ip_address: str | None = None,
    ) -> bool:
        """
        Record a failed login attempt for the given email.

        Args:
            email: User's email address
            ip_address: IP address of the request (for logging)

        Returns:
            True if account was locked, False otherwise
        """
        try:
            attempt_key = cls._get_attempt_key(email)
            lockout_key = cls._get_lockout_key(email)

            # Get current attempt count
            attempts = cache.get(attempt_key, 0)
            attempts += 1

            # Store updated attempt count with TTL
            cache.set(attempt_key, attempts, timeout=ATTEMPT_WINDOW)

            # Log failed attempt
            logger.info(
                f"Failed login attempt for {email} from {ip_address or 'unknown IP'} "
                f"(attempt {attempts}/{MAX_ATTEMPTS})",
            )

            # Check if we should lock the account
            if attempts >= MAX_ATTEMPTS:
                # Set lockout timestamp (current time + lockout duration)
                lockout_until = time.time() + LOCKOUT_DURATION
                cache.set(lockout_key, lockout_until, timeout=LOCKOUT_DURATION)

                # Log lockout event
                logger.warning(
                    f"Account locked: {email} after {attempts} failed attempts "
                    f"from {ip_address or 'unknown IP'}",
                )
                return True

            return False

        except Exception as e:
            # Graceful degradation: log error but don't block login
            logger.error(
                f"Error recording failed attempt for {email}: {e}",
                exc_info=True,
            )
            return False

    @classmethod
    def is_locked(cls, email: str) -> tuple[bool, int]:
        """
        Check if an account is currently locked.

        Args:
            email: User's email address

        Returns:
            Tuple of (is_locked, seconds_remaining)
            - is_locked: True if account is locked
            - seconds_remaining: Seconds until lockout expires (0 if not locked)
        """
        try:
            lockout_key = cls._get_lockout_key(email)

            # Check if lockout timestamp exists
            lockout_timestamp = cache.get(lockout_key)

            if lockout_timestamp:
                # Calculate seconds remaining
                now = time.time()
                seconds_remaining = max(0, int(lockout_timestamp - now))

                if seconds_remaining > 0:
                    return (True, seconds_remaining)
                # Lockout has expired, clean up
                cache.delete(lockout_key)

            return (False, 0)

        except Exception as e:
            # Graceful degradation: log error and allow login
            logger.error(f"Error checking lockout for {email}: {e}", exc_info=True)
            return (False, 0)

    @classmethod
    def reset_attempts(cls, email: str) -> None:
        """
        Reset failed attempt counter and clear lockout for the given email.

        Called after successful login or manual unlock by admin.

        Args:
            email: User's email address
        """
        try:
            attempt_key = cls._get_attempt_key(email)
            lockout_key = cls._get_lockout_key(email)

            # Delete both keys
            cache.delete(attempt_key)
            cache.delete(lockout_key)

            logger.info(f"Lockout cleared for {email}")

        except Exception as e:
            # Graceful degradation: log error
            logger.error(f"Error resetting attempts for {email}: {e}", exc_info=True)

    @classmethod
    def get_attempt_count(cls, email: str) -> int:
        """
        Get the current failed attempt count for the given email.

        Args:
            email: User's email address

        Returns:
            Number of failed attempts (0 if none)
        """
        try:
            attempt_key = cls._get_attempt_key(email)
            return cache.get(attempt_key, 0)

        except Exception as e:
            # Graceful degradation: log error and return 0
            logger.error(
                f"Error getting attempt count for {email}: {e}",
                exc_info=True,
            )
            return 0

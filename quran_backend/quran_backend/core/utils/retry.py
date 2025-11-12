"""
Retry logic with exponential backoff for transient errors.

Implements AC #5 from US-API-002:
- Automatic retry for transient errors
- Exponential backoff (1s, 2s, 4s)
- Max 3 retry attempts
- User informed of retry progress
- Only idempotent operations
"""

import functools
import logging
import time
from collections.abc import Callable

import redis
import requests
from django.db import OperationalError
from django_redis.exceptions import ConnectionInterrupted

from quran_backend.core.exceptions import NetworkError
from quran_backend.core.exceptions import TransientError

logger = logging.getLogger(__name__)


def retry_with_exponential_backoff(
    max_retries: int = 3,
    delays: tuple[float, ...] = (1.0, 2.0, 4.0),
    exceptions: tuple[type[Exception], ...] = (TransientError, NetworkError),
):
    """
    Decorator to retry function calls with exponential backoff.

    Implements AC #5: Automatic retry for transient errors with delays of 1s, 2s, 4s.
    Logs each retry attempt and informs user of progress.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        delays: Tuple of delay durations in seconds for each retry (default: (1, 2, 4))
        exceptions: Tuple of exception types to retry on (default: (TransientError, NetworkError))

    Usage:
        @retry_with_exponential_backoff()
        def fetch_from_external_api():
            response = requests.get("https://api.example.com/data")
            if response.status_code >= 500:
                raise TransientError("API temporarily unavailable")
            return response.json()

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            attempts = 0

            # First attempt (not a retry)
            try:
                return func(*args, **kwargs)
            except exceptions as exc:
                last_exception = exc
                attempts = 1
                logger.info(
                    "Function %s failed on first attempt: %s. Will retry up to %d times.",
                    func.__name__,
                    exc,
                    max_retries,
                )

            # Retry attempts
            for retry_num in range(1, max_retries + 1):
                # Get delay for this retry (use last delay if we exceed the tuple)
                delay = delays[min(retry_num - 1, len(delays) - 1)]

                # Log retry attempt
                logger.info(
                    "Retrying %s... (attempt %d/%d) after %s s delay",
                    func.__name__,
                    retry_num,
                    max_retries,
                    delay,
                )

                # Wait before retrying
                time.sleep(delay)

                # Attempt the function call
                try:
                    result = func(*args, **kwargs)
                    # Success! Log and return
                    logger.info(
                        "Function %s succeeded on attempt %d (after %d retries)",
                        func.__name__,
                        retry_num + 1,
                        retry_num,
                    )
                    return result
                except exceptions as exc:
                    last_exception = exc
                    attempts = retry_num + 1
                    logger.warning(
                        "Retry %d/%d failed for %s: %s",
                        retry_num,
                        max_retries,
                        func.__name__,
                        exc,
                    )
                    # Continue to next retry attempt

            # All retries exhausted
            logger.error(
                "Function %s failed after %d total attempts (1 initial + %d retries). Raising last exception.",
                func.__name__,
                attempts,
                max_retries,
            )
            raise last_exception

        return wrapper

    return decorator


# Convenience decorator for database operations
def retry_on_db_error(max_retries: int = 3):
    """
    Retry decorator specifically for database connection errors.

    Args:
        max_retries: Maximum retry attempts (default: 3)

    Usage:
        @retry_on_db_error()
        def save_user_data(user_id, data):
            user = User.objects.get(id=user_id)
            user.data = data
            user.save()
    """

    return retry_with_exponential_backoff(
        max_retries=max_retries,
        delays=(1.0, 2.0, 4.0),
        exceptions=(OperationalError, TransientError),
    )


# Convenience decorator for external API calls
def retry_on_network_error(max_retries: int = 3):
    """
    Retry decorator specifically for network/external API errors.

    Args:
        max_retries: Maximum retry attempts (default: 3)

    Usage:
        @retry_on_network_error()
        def fetch_quran_audio(surah_number, reciter_id):
            response = requests.get(f"https://api.example.com/audio/{surah_number}")
            if not response.ok:
                raise NetworkError(f"Failed to fetch audio: {response.status_code}")
            return response.content
    """

    return retry_with_exponential_backoff(
        max_retries=max_retries,
        delays=(1.0, 2.0, 4.0),
        exceptions=(
            NetworkError,
            TransientError,
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
        ),
    )


# Convenience decorator for Redis cache operations
def retry_on_cache_error(max_retries: int = 2):
    """
    Retry decorator for Redis cache operations (graceful degradation).

    Uses fewer retries since cache failures should degrade gracefully.
    Handles transient Redis connection errors but allows permanent failures
    to fail fast with database fallback.

    Args:
        max_retries: Maximum retry attempts (default: 2)

    Usage:
        @retry_on_cache_error()
        def get_cached_translation(verse_id, language):
            cache_key = f"translation:{verse_id}:{language}"
            return cache.get(cache_key)

    Note: This is complementary to the IGNORE_EXCEPTIONS setting in cache config.
          Use this decorator for critical cache operations that should be retried.
    """

    return retry_with_exponential_backoff(
        max_retries=max_retries,
        delays=(0.5, 1.0),  # Shorter delays for cache
        exceptions=(
            ConnectionInterrupted,
            redis.exceptions.ConnectionError,
            redis.exceptions.TimeoutError,
            TransientError,
        ),
    )

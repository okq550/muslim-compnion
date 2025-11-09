"""Cache Manager Service for Redis-based caching operations.

This module provides a centralized cache management layer built on top of
django-redis. It handles cache key generation, TTL management, graceful
degradation, and monitoring for the Quran Backend API.

Key Features:
- Automatic key prefixing with quran_backend namespace
- Graceful fallback when Redis is unavailable
- Cache hit/miss logging for monitoring
- Batch operations for efficiency
- Pattern-based deletion for cache invalidation
"""

import logging
from typing import Any

import redis
from django.core.cache import cache

logger = logging.getLogger(__name__)


class CacheManager:
    """Centralized cache management service using Redis backend.

    Provides high-level cache operations with automatic error handling,
    monitoring, and key generation utilities. All operations handle
    Redis failures gracefully and log cache hit/miss events.

    Usage:
        cache_mgr = CacheManager()
        cache_mgr.set("quran:surah:1", data, ttl=604800)
        data = cache_mgr.get("quran:surah:1")
    """

    # Default TTL values (in seconds)
    TTL_STATIC_CONTENT = (
        604800  # 7 days for static content (Quran, reciters, translations)
    )
    TTL_DYNAMIC_CONTENT = 3600  # 1 hour for dynamic content (user bookmarks)
    TTL_SHORT = 300  # 5 minutes for very dynamic content

    def __init__(self) -> None:
        """Initialize the cache manager."""
        self._cache = cache

    def get(self, key: str) -> Any | None:
        """Retrieve value from cache by key.

        Args:
            key: Cache key to retrieve (will be auto-prefixed)

        Returns:
            Cached value if found, None if not found or cache unavailable

        Example:
            >>> cache_mgr = CacheManager()
            >>> data = cache_mgr.get("quran:surah:1")
        """
        try:
            value = self._cache.get(key)
            if value is not None:
                logger.debug(f"Cache HIT: {key}")
            else:
                logger.debug(f"Cache MISS: {key}")
            return value
        except redis.exceptions.RedisError as e:
            logger.warning(f"Cache GET error for key '{key}': {e}")
            return None

    def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Store value in cache with optional TTL override.

        Args:
            key: Cache key to store (will be auto-prefixed)
            value: Value to cache (must be JSON serializable)
            ttl: Time-to-live in seconds (None uses default from settings)

        Returns:
            True if successfully cached, False on error

        Example:
            >>> cache_mgr = CacheManager()
            >>> cache_mgr.set("quran:surah:1", data, ttl=604800)
        """
        try:
            self._cache.set(key, value, timeout=ttl)
            logger.debug(f"Cache SET: {key} (TTL: {ttl or 'default'})")
            return True
        except (redis.exceptions.RedisError, TypeError) as e:
            logger.warning(f"Cache SET error for key '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """Remove single key from cache.

        Args:
            key: Cache key to delete (will be auto-prefixed)

        Returns:
            True if key was deleted, False otherwise

        Example:
            >>> cache_mgr = CacheManager()
            >>> cache_mgr.delete("quran:surah:1")
        """
        try:
            result = self._cache.delete(key)
            logger.debug(f"Cache DELETE: {key} (deleted: {result})")
            return result > 0
        except redis.exceptions.RedisError as e:
            logger.warning(f"Cache DELETE error for key '{key}': {e}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """Remove all keys matching pattern.

        This is useful for bulk cache invalidation, such as clearing
        all Quran text caches or all reciter caches at once.

        Args:
            pattern: Pattern to match (e.g., "quran:*" or "reciters:*")

        Returns:
            Number of keys deleted (0 on error or no matches)

        Example:
            >>> cache_mgr = CacheManager()
            >>> deleted_count = cache_mgr.delete_pattern("quran:surah:*")
        """
        try:
            # Get the django-redis client
            redis_client = self._cache.client.get_client()

            # Add the KEY_PREFIX to the pattern
            from django.conf import settings

            key_prefix = settings.CACHES["default"].get("KEY_PREFIX", "")
            if key_prefix:
                full_pattern = f"{key_prefix}:*:{pattern}"
            else:
                full_pattern = f"*:{pattern}"

            # Get all keys matching the pattern
            keys = redis_client.keys(full_pattern)

            if not keys:
                logger.debug(
                    f"Cache DELETE_PATTERN: No keys found for pattern '{pattern}'"
                )
                return 0

            # Delete all matched keys
            deleted = redis_client.delete(*keys)
            logger.info(
                f"Cache DELETE_PATTERN: Deleted {deleted} keys matching '{pattern}'"
            )
            return deleted

        except redis.exceptions.RedisError as e:
            logger.warning(f"Cache DELETE_PATTERN error for pattern '{pattern}': {e}")
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key to check (will be auto-prefixed)

        Returns:
            True if key exists, False otherwise

        Example:
            >>> cache_mgr = CacheManager()
            >>> if cache_mgr.exists("quran:surah:1"):
            ...     print("Key exists")
        """
        try:
            result = self._cache.has_key(key)
            logger.debug(f"Cache EXISTS: {key} = {result}")
            return result
        except redis.exceptions.RedisError as e:
            logger.warning(f"Cache EXISTS error for key '{key}': {e}")
            return False

    def get_many(self, keys: list[str]) -> dict[str, Any]:
        """Batch retrieval of multiple cache keys.

        More efficient than multiple individual get() calls.

        Args:
            keys: List of cache keys to retrieve

        Returns:
            Dictionary mapping keys to values (missing keys excluded)

        Example:
            >>> cache_mgr = CacheManager()
            >>> data = cache_mgr.get_many(["quran:surah:1", "quran:surah:2"])
        """
        try:
            result = self._cache.get_many(keys)
            hit_count = len(result)
            miss_count = len(keys) - hit_count
            logger.debug(f"Cache GET_MANY: {hit_count} hits, {miss_count} misses")
            return result
        except redis.exceptions.RedisError as e:
            logger.warning(f"Cache GET_MANY error: {e}")
            return {}

    def set_many(self, data: dict[str, Any], ttl: int | None = None) -> bool:
        """Batch storage of multiple cache entries.

        More efficient than multiple individual set() calls.

        Args:
            data: Dictionary mapping keys to values
            ttl: Time-to-live in seconds (None uses default)

        Returns:
            True if successfully cached, False on error

        Example:
            >>> cache_mgr = CacheManager()
            >>> cache_mgr.set_many({"quran:surah:1": data1, "quran:surah:2": data2})
        """
        try:
            self._cache.set_many(data, timeout=ttl)
            logger.debug(f"Cache SET_MANY: {len(data)} keys (TTL: {ttl or 'default'})")
            return True
        except (redis.exceptions.RedisError, TypeError) as e:
            logger.warning(f"Cache SET_MANY error: {e}")
            return False

    def clear_all(self) -> bool:
        """Clear entire cache (admin only - use with caution).

        This removes ALL cached data. Should only be used for
        development/testing or administrative cache clearing.

        Returns:
            True if cache cleared, False on error

        Example:
            >>> cache_mgr = CacheManager()
            >>> cache_mgr.clear_all()  # Use with caution!
        """
        try:
            self._cache.clear()
            logger.warning("Cache CLEAR_ALL: Entire cache cleared")
            return True
        except redis.exceptions.RedisError as e:
            logger.error(f"Cache CLEAR_ALL error: {e}")
            return False

    # Cache Key Generation Utilities
    # ================================

    @staticmethod
    def generate_quran_key(surah_number: int) -> str:
        """Generate cache key for Quran surah text.

        Args:
            surah_number: Surah number (1-114)

        Returns:
            Cache key in format: quran:surah:{number}

        Example:
            >>> key = CacheManager.generate_quran_key(1)
            >>> # Returns: "quran:surah:1"
        """
        return f"quran:surah:{surah_number}"

    @staticmethod
    def generate_reciter_list_key() -> str:
        """Generate cache key for reciter list.

        Returns:
            Cache key: "reciters:list"

        Example:
            >>> key = CacheManager.generate_reciter_list_key()
            >>> # Returns: "reciters:list"
        """
        return "reciters:list"

    @staticmethod
    def generate_translation_list_key() -> str:
        """Generate cache key for translation list.

        Returns:
            Cache key: "translations:list"

        Example:
            >>> key = CacheManager.generate_translation_list_key()
            >>> # Returns: "translations:list"
        """
        return "translations:list"

    @staticmethod
    def generate_user_bookmark_key(user_id: str) -> str:
        """Generate cache key for user bookmarks.

        Args:
            user_id: User identifier (UUID or username)

        Returns:
            Cache key in format: user:{user_id}:bookmarks

        Example:
            >>> key = CacheManager.generate_user_bookmark_key("abc123")
            >>> # Returns: "user:abc123:bookmarks"
        """
        return f"user:{user_id}:bookmarks"

    @staticmethod
    def generate_reciter_detail_key(reciter_id: int) -> str:
        """Generate cache key for reciter details.

        Args:
            reciter_id: Reciter ID

        Returns:
            Cache key in format: reciter:{id}

        Example:
            >>> key = CacheManager.generate_reciter_detail_key(42)
            >>> # Returns: "reciter:42"
        """
        return f"reciter:{reciter_id}"

    @staticmethod
    def generate_translation_detail_key(translation_id: int) -> str:
        """Generate cache key for translation details.

        Args:
            translation_id: Translation ID

        Returns:
            Cache key in format: translation:{id}

        Example:
            >>> key = CacheManager.generate_translation_detail_key(10)
            >>> # Returns: "translation:10"
        """
        return f"translation:{translation_id}"

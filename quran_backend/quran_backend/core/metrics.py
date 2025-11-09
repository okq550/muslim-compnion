"""Cache metrics and monitoring utilities.

Provides functions to track cache performance metrics including:
- Cache hit/miss ratio
- Cache memory usage
- Cache operation latency
- Cache eviction rate

These metrics are logged to Sentry and can be used for monitoring
and alerting in production.
"""

import logging
from typing import Any

import redis
import sentry_sdk
from django.core.cache import cache

logger = logging.getLogger(__name__)


class CacheMetrics:
    """Cache performance metrics tracker.

    Collects and reports cache metrics for monitoring and optimization.
    Metrics are logged to Sentry as custom measurements.
    """

    # Redis counter keys for hit/miss tracking
    HITS_KEY = "cache_metrics:hits"
    MISSES_KEY = "cache_metrics:misses"

    @classmethod
    def record_hit(cls) -> None:
        """Record a cache hit for metrics tracking.

        Increments the cache hits counter. Call this from CacheManager.get()
        when cache returns a value.
        """
        try:
            redis_client = cache.client.get_client()
            redis_client.incr(cls.HITS_KEY)
        except (redis.exceptions.RedisError, AttributeError):
            # Gracefully handle if Redis is unavailable
            logger.debug("Failed to record cache hit (Redis unavailable)")

    @classmethod
    def record_miss(cls) -> None:
        """Record a cache miss for metrics tracking.

        Increments the cache misses counter. Call this from CacheManager.get()
        when cache returns None.
        """
        try:
            redis_client = cache.client.get_client()
            redis_client.incr(cls.MISSES_KEY)
        except (redis.exceptions.RedisError, AttributeError):
            # Gracefully handle if Redis is unavailable
            logger.debug("Failed to record cache miss (Redis unavailable)")

    @classmethod
    def get_hit_ratio(cls) -> dict[str, Any]:
        """Calculate cache hit ratio from tracked metrics.

        Returns:
            Dictionary with hit ratio statistics:
            {
                "hits": int,
                "misses": int,
                "total": int,
                "hit_ratio": float (0.0 to 1.0)
            }

        Example:
            >>> metrics = CacheMetrics.get_hit_ratio()
            >>> print(f"Hit ratio: {metrics['hit_ratio']:.2%}")
            Hit ratio: 85.50%
        """
        try:
            redis_client = cache.client.get_client()

            hits = int(redis_client.get(cls.HITS_KEY) or 0)
            misses = int(redis_client.get(cls.MISSES_KEY) or 0)
            total = hits + misses

            hit_ratio = hits / total if total > 0 else 0.0

            metrics = {
                "hits": hits,
                "misses": misses,
                "total": total,
                "hit_ratio": hit_ratio,
            }

            # Log to Sentry if hit ratio is below target (80%)
            if total > 100 and hit_ratio < 0.8:  # Require at least 100 requests
                sentry_sdk.set_measurement("cache_hit_ratio", hit_ratio)
                logger.warning(
                    f"Cache hit ratio below target: {hit_ratio:.2%} "
                    f"(hits: {hits}, misses: {misses})"
                )
            elif total > 100:
                # Log successful metrics periodically
                logger.info(
                    f"Cache hit ratio: {hit_ratio:.2%} " f"(hits: {hits}, misses: {misses})"
                )

            return metrics

        except (redis.exceptions.RedisError, AttributeError) as e:
            logger.error(f"Failed to calculate hit ratio: {e}")
            return {
                "hits": 0,
                "misses": 0,
                "total": 0,
                "hit_ratio": 0.0,
            }

    @classmethod
    def reset_hit_ratio(cls) -> bool:
        """Reset hit/miss counters.

        Useful for starting fresh metrics tracking after deployments
        or for periodic resets.

        Returns:
            True if counters were reset, False on error
        """
        try:
            redis_client = cache.client.get_client()
            redis_client.delete(cls.HITS_KEY, cls.MISSES_KEY)
            logger.info("Cache hit/miss counters reset")
            return True

        except (redis.exceptions.RedisError, AttributeError) as e:
            logger.error(f"Failed to reset hit ratio counters: {e}")
            return False

    @classmethod
    def get_memory_usage(cls) -> dict[str, Any]:
        """Get Redis memory usage statistics.

        Returns:
            Dictionary with memory metrics:
            {
                "used_memory_mb": float,
                "maxmemory_mb": float,
                "usage_percent": float,
                "evicted_keys": int
            }

        Example:
            >>> memory = CacheMetrics.get_memory_usage()
            >>> if memory["usage_percent"] > 90:
            ...     print("Cache memory critically high!")
        """
        try:
            redis_client = cache.client.get_client()
            info = redis_client.info("memory")
            stats = redis_client.info("stats")

            used_memory = info.get("used_memory", 0)
            maxmemory = info.get("maxmemory", 0)

            # Convert to MB
            used_memory_mb = used_memory / (1024 * 1024)
            maxmemory_mb = maxmemory / (1024 * 1024) if maxmemory > 0 else 500.0  # Default

            usage_percent = (used_memory / maxmemory * 100) if maxmemory > 0 else 0.0
            evicted_keys = stats.get("evicted_keys", 0)

            metrics = {
                "used_memory_mb": round(used_memory_mb, 2),
                "maxmemory_mb": round(maxmemory_mb, 2),
                "usage_percent": round(usage_percent, 2),
                "evicted_keys": evicted_keys,
            }

            # Alert if memory usage is high (> 90% of limit)
            if usage_percent > 90:
                sentry_sdk.set_measurement("cache_memory_usage_percent", usage_percent)
                logger.error(
                    f"Cache memory critically high: {usage_percent:.2f}% "
                    f"({used_memory_mb:.2f} MB / {maxmemory_mb:.2f} MB)"
                )
            elif usage_percent > 80:
                sentry_sdk.set_measurement("cache_memory_usage_percent", usage_percent)
                logger.warning(
                    f"Cache memory usage high: {usage_percent:.2f}% "
                    f"({used_memory_mb:.2f} MB / {maxmemory_mb:.2f} MB)"
                )

            # Alert if eviction is happening frequently
            if evicted_keys > 1000:
                logger.warning(
                    f"High cache eviction rate: {evicted_keys} keys evicted. "
                    f"Consider increasing cache size."
                )

            return metrics

        except (redis.exceptions.RedisError, AttributeError) as e:
            logger.error(f"Failed to get memory usage: {e}")
            return {
                "used_memory_mb": 0.0,
                "maxmemory_mb": 0.0,
                "usage_percent": 0.0,
                "evicted_keys": 0,
            }

    @classmethod
    def get_all_metrics(cls) -> dict[str, Any]:
        """Get comprehensive cache metrics.

        Combines hit ratio and memory usage into a single report.

        Returns:
            Dictionary with all cache metrics:
            {
                "hit_ratio": {...},
                "memory": {...}
            }

        Example:
            >>> metrics = CacheMetrics.get_all_metrics()
            >>> print(f"Hit ratio: {metrics['hit_ratio']['hit_ratio']:.2%}")
            >>> print(f"Memory usage: {metrics['memory']['usage_percent']:.2f}%")
        """
        return {
            "hit_ratio": cls.get_hit_ratio(),
            "memory": cls.get_memory_usage(),
        }

    @classmethod
    def log_metrics_to_sentry(cls) -> None:
        """Log all cache metrics to Sentry for monitoring.

        This can be called periodically (e.g., via Celery Beat)
        to track cache performance over time.
        """
        metrics = cls.get_all_metrics()

        # Log to Sentry as custom measurements
        sentry_sdk.set_measurement(
            "cache_hit_ratio",
            metrics["hit_ratio"]["hit_ratio"],
        )
        sentry_sdk.set_measurement(
            "cache_memory_usage_mb",
            metrics["memory"]["used_memory_mb"],
        )
        sentry_sdk.set_measurement(
            "cache_memory_usage_percent",
            metrics["memory"]["usage_percent"],
        )
        sentry_sdk.set_measurement(
            "cache_evicted_keys",
            metrics["memory"]["evicted_keys"],
        )

        # Log summary
        logger.info(
            f"Cache metrics: Hit ratio: {metrics['hit_ratio']['hit_ratio']:.2%}, "
            f"Memory: {metrics['memory']['used_memory_mb']:.2f} MB "
            f"({metrics['memory']['usage_percent']:.2f}%)"
        )

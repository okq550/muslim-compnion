"""Cache decorators for Django REST Framework views.

This module provides decorators to automatically cache API responses,
reducing database load and improving response times for frequently
accessed endpoints.

Key Features:
- @cache_response decorator for DRF views
- Automatic cache key generation from request parameters
- Configurable TTL per endpoint
- Cache hit/miss tracking
- Graceful fallback when Redis unavailable
"""

import functools
import logging
from collections.abc import Callable
from typing import Any

from rest_framework.request import Request
from rest_framework.response import Response

from quran_backend.core.services import CacheManager

logger = logging.getLogger(__name__)


def cache_response(
    cache_key_func: Callable[[Request, Any, Any], str],
    ttl: int = CacheManager.TTL_STATIC_CONTENT,
) -> Callable:
    """Decorator to cache DRF API responses.

    Caches successful (200 OK) responses using the provided cache_key_func
    to generate unique cache keys. Subsequent requests with the same cache
    key return the cached response without hitting the database.

    Args:
        cache_key_func: Function that generates cache key from request
                       Signature: (request, *args, **kwargs) -> str
        ttl: Time-to-live in seconds (default: 7 days for static content)

    Returns:
        Decorated view function with caching behavior

    Example:
        >>> def make_cache_key(request, *args, **kwargs):
        ...     surah_number = kwargs.get('surah_number')
        ...     return f"quran:surah:{surah_number}"
        ...
        >>> @cache_response(cache_key_func=make_cache_key, ttl=604800)
        ... def get_surah(request, surah_number):
        ...     # This will be cached for 7 days
        ...     return Response({"surah": surah_number})

    Usage in ViewSets:
        >>> class QuranViewSet(viewsets.ReadOnlyModelViewSet):
        ...     @cache_response(cache_key_func=lambda r, *a, **kw: f"quran:{kw['pk']}")
        ...     def retrieve(self, request, *args, **kwargs):
        ...         return super().retrieve(request, *args, **kwargs)
    """

    def decorator(view_func: Callable) -> Callable:
        @functools.wraps(view_func)
        def wrapper(request_or_self, *args, **kwargs) -> Response:
            # Handle both function-based views and class-based views
            if isinstance(request_or_self, Request):
                # Function-based view: first arg is request
                request = request_or_self
            else:
                # Class-based view: first arg is self, second is request
                request = args[0] if args else kwargs.get("request")

            # Generate cache key
            try:
                if isinstance(request_or_self, Request):
                    cache_key = cache_key_func(request, *args, **kwargs)
                else:
                    # For class-based views, pass request from args
                    cache_key = cache_key_func(request, *args[1:], **kwargs)
            except Exception as e:
                logger.warning(f"Cache key generation failed: {e}. Bypassing cache.")
                return view_func(request_or_self, *args, **kwargs)

            # Try to get cached response
            cache_mgr = CacheManager()
            cached_data = cache_mgr.get(cache_key)

            if cached_data is not None:
                # Cache HIT - return cached response
                logger.debug(
                    f"Cache HIT: Returning cached response for key '{cache_key}'"
                )
                return Response(cached_data)

            # Cache MISS - execute view and cache result
            logger.debug(f"Cache MISS: Executing view for key '{cache_key}'")
            response = view_func(request_or_self, *args, **kwargs)

            # Only cache successful responses
            if isinstance(response, Response) and response.status_code == 200:
                cache_mgr.set(cache_key, response.data, ttl=ttl)
                logger.debug(f"Cached response for key '{cache_key}' (TTL: {ttl}s)")
            else:
                logger.debug(
                    f"Response not cached (status: {getattr(response, 'status_code', 'unknown')})",
                )

            return response

        return wrapper

    return decorator


# Cache Warming Utilities
# =========================


def warm_cache(
    keys_and_values: dict[str, Any],
    ttl: int = CacheManager.TTL_STATIC_CONTENT,
) -> int:
    """Warm cache by pre-populating with common queries.

    This function is useful for:
    - Deployment cache warming
    - Scheduled cache refresh
    - Manual cache pre-population

    Args:
        keys_and_values: Dictionary mapping cache keys to values
        ttl: Time-to-live in seconds (default: 7 days)

    Returns:
        Number of keys successfully cached

    Example:
        >>> # Warm cache with popular surahs
        >>> warm_cache({
        ...     "quran:surah:1": get_surah_data(1),
        ...     "quran:surah:2": get_surah_data(2),
        ... })
    """
    cache_mgr = CacheManager()

    # Use batch operation for efficiency
    if cache_mgr.set_many(keys_and_values, ttl=ttl):
        logger.info(f"Cache warmed: {len(keys_and_values)} keys cached (TTL: {ttl}s)")
        return len(keys_and_values)

    # Fallback to individual sets if batch fails
    success_count = 0
    for key, value in keys_and_values.items():
        if cache_mgr.set(key, value, ttl=ttl):
            success_count += 1

    logger.info(f"Cache warmed: {success_count}/{len(keys_and_values)} keys cached")
    return success_count


def warm_cache_from_queryset(
    queryset,
    key_func: Callable[[Any], str],
    value_func: Callable[[Any], Any],
    ttl: int = CacheManager.TTL_STATIC_CONTENT,
) -> int:
    """Warm cache from a Django queryset.

    Iterates through queryset and caches each object using provided
    key and value functions.

    Args:
        queryset: Django queryset to iterate
        key_func: Function to generate cache key from object
        value_func: Function to generate cached value from object
                   (usually a serializer)
        ttl: Time-to-live in seconds

    Returns:
        Number of objects successfully cached

    Example:
        >>> from quran_backend.quran.models import QuranText
        >>> from quran_backend.quran.serializers import QuranSerializer
        >>>
        >>> queryset = QuranText.objects.filter(surah_number__lte=10)
        >>> warm_cache_from_queryset(
        ...     queryset,
        ...     key_func=lambda obj: f"quran:surah:{obj.surah_number}",
        ...     value_func=lambda obj: QuranSerializer(obj).data,
        ...     ttl=604800
        ... )
    """
    cache_data = {}

    for obj in queryset:
        try:
            cache_key = key_func(obj)
            cache_value = value_func(obj)
            cache_data[cache_key] = cache_value
        except Exception as e:
            logger.warning(f"Failed to prepare cache for object {obj}: {e}")
            continue

    return warm_cache(cache_data, ttl=ttl)


# Mixin for Model ViewSets
# ==========================


class CachedModelMixin:
    """Mixin for Django REST Framework ViewSets to add automatic caching.

    This mixin overrides the retrieve() and list() methods to add
    caching behavior. Designed to work with ReadOnlyModelViewSet.

    Attributes:
        cache_key_prefix: Prefix for cache keys (e.g., "quran:surah")
        cache_ttl: Time-to-live in seconds (default: 7 days)

    Example:
        >>> class QuranViewSet(CachedModelMixin, viewsets.ReadOnlyModelViewSet):
        ...     cache_key_prefix = "quran:surah"
        ...     cache_ttl = 604800  # 7 days
        ...     queryset = QuranText.objects.all()
        ...     serializer_class = QuranSerializer
        ...
        ...     def get_cache_key(self, request, *args, **kwargs):
        ...         # Custom cache key generation
        ...         pk = kwargs.get('pk')
        ...         return f"{self.cache_key_prefix}:{pk}"

    Note: Subclasses should override get_cache_key() for custom key generation.
    """

    cache_key_prefix: str = "api"
    cache_ttl: int = CacheManager.TTL_STATIC_CONTENT

    def get_cache_key(self, request: Request, *args, **kwargs) -> str:
        """Generate cache key for the current request.

        Override this method to customize cache key generation.

        Args:
            request: DRF Request object
            *args: Positional arguments from view
            **kwargs: Keyword arguments from view (includes 'pk' for detail views)

        Returns:
            Cache key string
        """
        # Default: use pk if available (detail view), otherwise use query params
        pk = kwargs.get("pk")
        if pk:
            return f"{self.cache_key_prefix}:{pk}"

        # For list views, include query params in key
        query_string = request.query_params.urlencode()
        if query_string:
            return f"{self.cache_key_prefix}:list?{query_string}"

        return f"{self.cache_key_prefix}:list"

    def retrieve(self, request: Request, *args, **kwargs) -> Response:
        """Retrieve a single object with caching.

        Checks cache first, falls back to database on cache miss.
        """
        cache_key = self.get_cache_key(request, *args, **kwargs)
        cache_mgr = CacheManager()

        # Try cache first
        cached_data = cache_mgr.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data)

        # Cache miss - fetch from database
        logger.debug(f"Cache MISS: {cache_key}")
        response = super().retrieve(request, *args, **kwargs)  # type: ignore[misc]

        # Cache successful response
        if response.status_code == 200:
            cache_mgr.set(cache_key, response.data, ttl=self.cache_ttl)

        return response

    def list(self, request: Request, *args, **kwargs) -> Response:
        """List objects with caching.

        Note: List caching should be used carefully as it can become
        stale when new objects are created. Consider shorter TTL for
        list endpoints or disable caching entirely.
        """
        cache_key = self.get_cache_key(request, *args, **kwargs)
        cache_mgr = CacheManager()

        # Try cache first
        cached_data = cache_mgr.get(cache_key)
        if cached_data is not None:
            logger.debug(f"Cache HIT: {cache_key}")
            return Response(cached_data)

        # Cache miss - fetch from database
        logger.debug(f"Cache MISS: {cache_key}")
        response = super().list(request, *args, **kwargs)  # type: ignore[misc]

        # Cache successful response with shorter TTL for lists
        if response.status_code == 200:
            # Use shorter TTL for list endpoints (1 hour)
            list_ttl = min(self.cache_ttl, CacheManager.TTL_DYNAMIC_CONTENT)
            cache_mgr.set(cache_key, response.data, ttl=list_ttl)

        return response

"""Cache invalidation signals for automatic cache clearing.

This module provides Django signal handlers that automatically invalidate
cached data when models are updated or deleted. This ensures cache consistency
without requiring manual cache clearing.

Signal handlers are connected to models in their respective apps.ready() methods
or can be connected manually where models are defined.

Usage in app's apps.py:
    def ready(self):
        from quran_backend.core.signals import connect_quran_cache_signals
        connect_quran_cache_signals()
"""

import logging

from django.db.models.signals import post_delete
from django.db.models.signals import post_save

from quran_backend.core.services import CacheManager

logger = logging.getLogger(__name__)


# Generic Signal Handlers
# ========================


def invalidate_cache_by_key(cache_key: str, sender_name: str) -> None:
    """Helper function to invalidate a specific cache key.

    Args:
        cache_key: The cache key to invalidate
        sender_name: Name of the model that triggered the invalidation (for logging)
    """
    cache_mgr = CacheManager()
    if cache_mgr.delete(cache_key):
        logger.info(f"Cache invalidated: {cache_key} (triggered by {sender_name})")
    else:
        logger.warning(
            f"Failed to invalidate cache: {cache_key} (triggered by {sender_name})"
        )


def invalidate_cache_by_pattern(pattern: str, sender_name: str) -> None:
    """Helper function to invalidate cache keys matching a pattern.

    Args:
        pattern: Pattern to match cache keys (e.g., "quran:*")
        sender_name: Name of the model that triggered the invalidation (for logging)
    """
    cache_mgr = CacheManager()
    deleted_count = cache_mgr.delete_pattern(pattern)
    if deleted_count > 0:
        logger.info(
            f"Cache pattern invalidated: {pattern} ({deleted_count} keys deleted, "
            f"triggered by {sender_name})",
        )
    else:
        logger.debug(
            f"No cache keys found for pattern: {pattern} (triggered by {sender_name})"
        )


# Quran Text Cache Invalidation
# ===============================


def invalidate_quran_cache(sender, instance, **kwargs) -> None:
    """Invalidate Quran text cache when Quran content is modified.

    This handler should be connected to QuranText model signals:
    - post_save: Invalidate cache when text is created/updated
    - post_delete: Invalidate cache when text is deleted

    Args:
        sender: The model class that sent the signal
        instance: The actual instance being saved/deleted
        **kwargs: Additional signal arguments
    """
    # Invalidate specific surah cache if surah_number is available
    if hasattr(instance, "surah_number"):
        cache_key = CacheManager.generate_quran_key(instance.surah_number)
        invalidate_cache_by_key(cache_key, sender.__name__)
    else:
        # If we can't determine specific surah, invalidate all Quran caches
        invalidate_cache_by_pattern("quran:*", sender.__name__)


# Reciter Cache Invalidation
# ============================


def invalidate_reciter_cache(sender, instance, **kwargs) -> None:
    """Invalidate reciter cache when reciter data is modified.

    This handler should be connected to Reciter model signals.

    Args:
        sender: The model class that sent the signal
        instance: The actual instance being saved/deleted
        **kwargs: Additional signal arguments
    """
    # Invalidate reciter list cache
    cache_key = CacheManager.generate_reciter_list_key()
    invalidate_cache_by_key(cache_key, sender.__name__)

    # Invalidate specific reciter detail cache if available
    if hasattr(instance, "id") and instance.id:
        reciter_key = CacheManager.generate_reciter_detail_key(instance.id)
        invalidate_cache_by_key(reciter_key, sender.__name__)


# Translation Cache Invalidation
# ================================


def invalidate_translation_cache(sender, instance, **kwargs) -> None:
    """Invalidate translation cache when translation data is modified.

    This handler should be connected to Translation model signals.

    Args:
        sender: The model class that sent the signal
        instance: The actual instance being saved/deleted
        **kwargs: Additional signal arguments
    """
    # Invalidate translation list cache
    cache_key = CacheManager.generate_translation_list_key()
    invalidate_cache_by_key(cache_key, sender.__name__)

    # Invalidate specific translation detail cache if available
    if hasattr(instance, "id") and instance.id:
        translation_key = CacheManager.generate_translation_detail_key(instance.id)
        invalidate_cache_by_key(translation_key, sender.__name__)


# User Bookmark Cache Invalidation
# ==================================


def invalidate_user_bookmark_cache(sender, instance, **kwargs) -> None:
    """Invalidate user bookmark cache when bookmarks are modified.

    This handler should be connected to Bookmark model signals.

    Args:
        sender: The model class that sent the signal
        instance: The actual instance being saved/deleted
        **kwargs: Additional signal arguments
    """
    # Invalidate user-specific bookmark cache
    if hasattr(instance, "user_id"):
        cache_key = CacheManager.generate_user_bookmark_key(str(instance.user_id))
        invalidate_cache_by_key(cache_key, sender.__name__)
    elif hasattr(instance, "user"):
        # Support both user_id and user foreign key
        cache_key = CacheManager.generate_user_bookmark_key(str(instance.user.id))
        invalidate_cache_by_key(cache_key, sender.__name__)


# Signal Connection Helpers
# ===========================
# These functions should be called from app.ready() methods


def connect_quran_cache_signals() -> None:
    """Connect cache invalidation signals for Quran models.

    Call this from the Quran app's AppConfig.ready() method.

    Example:
        # In quran/apps.py
        from quran_backend.core.signals import connect_quran_cache_signals

        class QuranConfig(AppConfig):
            def ready(self):
                connect_quran_cache_signals()
    """
    try:
        # Import here to avoid circular imports
        from quran_backend.quran.models import (
            QuranText,  # type: ignore[import-not-found]
        )

        post_save.connect(invalidate_quran_cache, sender=QuranText)
        post_delete.connect(invalidate_quran_cache, sender=QuranText)
        logger.info("Quran cache invalidation signals connected")
    except ImportError:
        logger.debug(
            "QuranText model not found - cache signals will be connected when model is created",
        )


def connect_reciter_cache_signals() -> None:
    """Connect cache invalidation signals for Reciter models.

    Call this from the Recitation app's AppConfig.ready() method.
    """
    try:
        # Import here to avoid circular imports
        from quran_backend.recitation.models import (
            Reciter,  # type: ignore[import-not-found]
        )

        post_save.connect(invalidate_reciter_cache, sender=Reciter)
        post_delete.connect(invalidate_reciter_cache, sender=Reciter)
        logger.info("Reciter cache invalidation signals connected")
    except ImportError:
        logger.debug(
            "Reciter model not found - cache signals will be connected when model is created",
        )


def connect_translation_cache_signals() -> None:
    """Connect cache invalidation signals for Translation models.

    Call this from the Translation app's AppConfig.ready() method.
    """
    try:
        # Import here to avoid circular imports
        from quran_backend.translation.models import (
            Translation,  # type: ignore[import-not-found]
        )

        post_save.connect(invalidate_translation_cache, sender=Translation)
        post_delete.connect(invalidate_translation_cache, sender=Translation)
        logger.info("Translation cache invalidation signals connected")
    except ImportError:
        logger.debug(
            "Translation model not found - cache signals will be connected when model is created",
        )


def connect_bookmark_cache_signals() -> None:
    """Connect cache invalidation signals for Bookmark models.

    Call this from the Bookmark app's AppConfig.ready() method.
    """
    try:
        # Import here to avoid circular imports
        from quran_backend.bookmark.models import (
            Bookmark,  # type: ignore[import-not-found]
        )

        post_save.connect(invalidate_user_bookmark_cache, sender=Bookmark)
        post_delete.connect(invalidate_user_bookmark_cache, sender=Bookmark)
        logger.info("Bookmark cache invalidation signals connected")
    except ImportError:
        logger.debug(
            "Bookmark model not found - cache signals will be connected when model is created",
        )


def connect_all_cache_signals() -> None:
    """Connect all cache invalidation signals.

    This is a convenience function to connect all signals at once.
    Can be called from the core app's AppConfig.ready() method.

    Note: This will only connect signals for models that exist.
    Non-existent models will be silently skipped with a debug log.
    """
    connect_quran_cache_signals()
    connect_reciter_cache_signals()
    connect_translation_cache_signals()
    connect_bookmark_cache_signals()
    logger.info("All available cache invalidation signals connected")

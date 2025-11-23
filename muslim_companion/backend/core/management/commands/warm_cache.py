"""Django management command to warm the cache.

This command pre-populates the cache with frequently accessed static content
to improve response times and reduce database load. Useful for:
- Post-deployment cache warming
- Manual cache refresh during development
- Testing cache behavior

Usage:
    python manage.py warm_cache
    python manage.py warm_cache --content-types quran reciters
    python manage.py warm_cache --clear-first
"""

import logging

from django.core.management.base import BaseCommand

from backend.core.services import CacheManager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Warm cache with frequently accessed static content."""

    help = "Pre-populate cache with static content (Quran, reciters, translations)"

    def add_arguments(self, parser):
        """Add command-line arguments.

        Args:
            parser: ArgumentParser instance
        """
        parser.add_argument(
            "--content-types",
            nargs="+",
            choices=["quran", "reciters", "translations", "all"],
            default=["all"],
            help="Content types to warm (default: all)",
        )

        parser.add_argument(
            "--clear-first",
            action="store_true",
            help="Clear cache before warming",
        )

        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Limit number of items to cache per type (for testing)",
        )

    def handle(self, *args, **options):
        """Execute cache warming.

        Args:
            *args: Positional arguments
            **options: Command options from add_arguments
        """
        content_types = options["content_types"]
        clear_first = options["clear_first"]
        limit = options["limit"]

        # Normalize "all" to specific types
        if "all" in content_types:
            content_types = ["quran", "reciters", "translations"]

        self.stdout.write(self.style.SUCCESS("🔥 Starting cache warming..."))

        # Clear cache if requested
        if clear_first:
            self.stdout.write("Clearing existing cache...")
            cache_mgr = CacheManager()
            if cache_mgr.clear_all():
                self.stdout.write(self.style.SUCCESS("✓ Cache cleared"))
            else:
                self.stdout.write(
                    self.style.WARNING("⚠ Cache clear failed (continuing anyway)"),
                )

        # Warm cache for each content type
        total_cached = 0

        if "quran" in content_types:
            cached = self._warm_quran_cache(limit)
            total_cached += cached
            self.stdout.write(
                self.style.SUCCESS(f"✓ Cached {cached} Quran surahs")
                if cached > 0
                else self.style.WARNING("⚠ No Quran data cached"),
            )

        if "reciters" in content_types:
            cached = self._warm_reciter_cache(limit)
            total_cached += cached
            self.stdout.write(
                self.style.SUCCESS("✓ Cached reciter list")
                if cached > 0
                else self.style.WARNING(
                    "⚠ Reciter cache not populated (models may not exist yet)",
                ),
            )

        if "translations" in content_types:
            cached = self._warm_translation_cache(limit)
            total_cached += cached
            self.stdout.write(
                self.style.SUCCESS("✓ Cached translation list")
                if cached > 0
                else self.style.WARNING(
                    "⚠ Translation cache not populated (models may not exist yet)",
                ),
            )

        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f"\n🎉 Cache warming complete! {total_cached} items cached",
            ),
        )

    def _warm_quran_cache(self, limit: int | None = None) -> int:
        """Warm cache with Quran text data.

        Args:
            limit: Maximum number of surahs to cache (None for all)

        Returns:
            Number of surahs cached
        """
        try:
            # Import here to avoid errors if models don't exist yet
            from backend.quran.models import QuranText  # type: ignore[import-not-found]
            from backend.quran.serializers import (  # type: ignore[import-not-found]
                QuranSerializer,
            )

            cache_mgr = CacheManager()

            # Get popular surahs (or all if no limit)
            # Popular surahs: Al-Fatihah (1), Al-Baqarah (2), Yasin (36), Ar-Rahman (55), etc.
            popular_surahs = [1, 2, 36, 55, 67, 112, 113, 114]

            if limit:
                queryset = QuranText.objects.filter(
                    surah_number__in=popular_surahs[:limit],
                )
            else:
                queryset = QuranText.objects.all()

            cached_count = 0
            for surah in queryset:
                cache_key = CacheManager.generate_quran_key(surah.surah_number)
                serializer = QuranSerializer(surah)
                if cache_mgr.set(
                    cache_key,
                    serializer.data,
                    ttl=CacheManager.TTL_STATIC_CONTENT,
                ):
                    cached_count += 1

            return cached_count

        except ImportError:
            logger.debug("QuranText model not found - skipping Quran cache warming")
            return 0
        except Exception as e:
            logger.error(f"Error warming Quran cache: {e}", exc_info=True)
            return 0

    def _warm_reciter_cache(self, limit: int | None = None) -> int:
        """Warm cache with reciter list data.

        Args:
            limit: Maximum number of reciters to cache (None for all)

        Returns:
            Number of items cached (1 for list, or 0 on error)
        """
        try:
            # Import here to avoid errors if models don't exist yet
            from backend.recitation.models import (
                Reciter,  # type: ignore[import-not-found]
            )
            from backend.recitation.serializers import (  # type: ignore[import-not-found]
                ReciterSerializer,
            )

            cache_mgr = CacheManager()

            # Cache reciter list
            queryset = Reciter.objects.all()
            if limit:
                queryset = queryset[:limit]

            serializer = ReciterSerializer(queryset, many=True)
            cache_key = CacheManager.generate_reciter_list_key()

            if cache_mgr.set(
                cache_key,
                serializer.data,
                ttl=CacheManager.TTL_STATIC_CONTENT,
            ):
                return 1

            return 0

        except ImportError:
            logger.debug("Reciter model not found - skipping reciter cache warming")
            return 0
        except Exception as e:
            logger.error(f"Error warming reciter cache: {e}", exc_info=True)
            return 0

    def _warm_translation_cache(self, limit: int | None = None) -> int:
        """Warm cache with translation list data.

        Args:
            limit: Maximum number of translations to cache (None for all)

        Returns:
            Number of items cached (1 for list, or 0 on error)
        """
        try:
            # Import here to avoid errors if models don't exist yet
            from backend.translation.models import (  # type: ignore[import-not-found]
                Translation,
            )
            from backend.translation.serializers import (  # type: ignore[import-not-found]
                TranslationSerializer,
            )

            cache_mgr = CacheManager()

            # Cache translation list
            queryset = Translation.objects.all()
            if limit:
                queryset = queryset[:limit]

            serializer = TranslationSerializer(queryset, many=True)
            cache_key = CacheManager.generate_translation_list_key()

            if cache_mgr.set(
                cache_key,
                serializer.data,
                ttl=CacheManager.TTL_STATIC_CONTENT,
            ):
                return 1

            return 0

        except ImportError:
            logger.debug(
                "Translation model not found - skipping translation cache warming",
            )
            return 0
        except Exception as e:
            logger.error(f"Error warming translation cache: {e}", exc_info=True)
            return 0

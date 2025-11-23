"""Quran API views.

Implements API endpoints for Quran content:
- GET /api/v1/quran/surahs/ - List all Surahs (AC #6)
- GET /api/v1/quran/surahs/{id}/ - Surah detail (AC #7)
- GET /api/v1/quran/surahs/{id}/verses/ - Verses by Surah (AC #8)
- GET /api/v1/quran/verses/{id}/ - Single verse detail (AC #9)

All endpoints implement:
- Standard response format (AC #10)
- Redis caching with 7-day TTL (AC #11)
- Performance targets < 200ms p95 (AC #12)
"""

import logging

from drf_spectacular.utils import OpenApiParameter
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from backend.core.services.cache_manager import CacheManager

from .models import Surah
from .models import Verse
from .serializers import SurahDetailSerializer
from .serializers import SurahListSerializer
from .serializers import SurahVersesSerializer
from .serializers import VerseSerializer
from .serializers import VerseWithSurahSerializer

logger = logging.getLogger(__name__)

# Cache key patterns
CACHE_KEY_SURAH_LIST = "quran:surahs:list:{page}:{page_size}:{ordering}:{rev_type}"
CACHE_KEY_SURAH_DETAIL = "quran:surah:{id}"
CACHE_KEY_SURAH_VERSES = "quran:surah:{id}:verses:{start}:{end}"
CACHE_KEY_VERSE_DETAIL = "quran:verse:{id}"


class StandardPagination(PageNumberPagination):
    """Standard pagination for Quran endpoints."""

    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 114  # Max Surahs

    def get_paginated_response(self, data):
        """Return response in standard pagination format (AC #10)."""
        return Response(
            {
                "data": data,
                "pagination": {
                    "page": self.page.number,
                    "page_size": self.get_page_size(self.request),
                    "total_pages": self.page.paginator.num_pages,
                    "total_count": self.page.paginator.count,
                },
            },
        )


@extend_schema(
    tags=["User", "Quran Content"],
    summary="List all Surahs",
    description=(
        "Returns a paginated list of all 114 Surahs. "
        "Supports filtering by revelation_type and ordering by revelation_order."
    ),
    parameters=[
        OpenApiParameter(
            name="revelation_type",
            description="Filter by revelation type (Meccan or Medinan)",
            required=False,
            type=str,
        ),
        OpenApiParameter(
            name="ordering",
            description="Order by field (e.g., revelation_order, -id)",
            required=False,
            type=str,
        ),
    ],
)
class SurahListView(generics.ListAPIView):
    """
    List all Surahs with pagination, filtering, and sorting.

    AC #6: GET /api/v1/surahs/ Returns Complete Surah List
    - Returns paginated list of all 114 Surahs
    - Supports ?ordering=revelation_order for chronological reading
    - Supports ?revelation_type=Meccan filtering
    - Response time < 200ms (p95)
    - Uses Redis caching (7-day TTL for static content)
    """

    queryset = Surah.objects.all().order_by("id")
    serializer_class = SurahListSerializer
    permission_classes = [AllowAny]
    pagination_class = StandardPagination
    ordering_fields = ["id", "revelation_order", "total_verses"]
    ordering = ["id"]

    def __init__(self, **kwargs):
        """Initialize view with cache manager."""
        super().__init__(**kwargs)
        self.cache_manager = CacheManager()

    def list(self, request, *args, **kwargs):
        """List Surahs with caching."""
        # Build cache key from request params
        page = request.query_params.get("page", "1")
        page_size = request.query_params.get("page_size", "20")
        ordering = request.query_params.get("ordering", "id")
        revelation_type = request.query_params.get("revelation_type", "all")

        cache_key = CACHE_KEY_SURAH_LIST.format(
            page=page,
            page_size=page_size,
            ordering=ordering,
            rev_type=revelation_type,
        )

        # Check cache
        cached_response = self.cache_manager.get(cache_key)
        if cached_response is not None:
            logger.debug("Cache hit for Surah list: %s", cache_key)
            return Response(cached_response)

        # Get data from database
        queryset = self.get_queryset()

        # Apply revelation_type filter
        if revelation_type != "all":
            queryset = queryset.filter(revelation_type__iexact=revelation_type)

        # Apply ordering
        if ordering:
            if ordering.startswith("-"):
                queryset = queryset.order_by(ordering)
            else:
                queryset = queryset.order_by(ordering)

        page_obj = self.paginate_queryset(queryset)
        if page_obj is not None:
            serializer = self.get_serializer(page_obj, many=True)
            response = self.get_paginated_response(serializer.data)

            # Cache the response data
            self.cache_manager.set(
                cache_key,
                response.data,
                ttl=CacheManager.TTL_STATIC_CONTENT,
            )

            return response

        serializer = self.get_serializer(queryset, many=True)
        response_data = {"data": serializer.data}

        # Cache unpaginated response
        self.cache_manager.set(
            cache_key,
            response_data,
            ttl=CacheManager.TTL_STATIC_CONTENT,
        )

        return Response(response_data)


@extend_schema(
    tags=["User", "Quran Content"],
    summary="Get Surah detail",
    description=(
        "Returns complete metadata for a single Surah including revelation_note, "
        "mushaf_page_start, and juz_start."
    ),
)
class SurahDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single Surah by ID.

    AC #7: GET /api/v1/surahs/{id}/ Returns Single Surah Detail
    - Returns complete Surah metadata including revelation_note
    - Valid IDs: 1-114
    - Returns 404 for invalid Surah ID with clear error message
    """

    queryset = Surah.objects.all()
    serializer_class = SurahDetailSerializer
    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        """Initialize view with cache manager."""
        super().__init__(**kwargs)
        self.cache_manager = CacheManager()

    def retrieve(self, request, *args, **kwargs):
        """Retrieve Surah with caching."""
        pk = kwargs.get("pk")
        cache_key = CACHE_KEY_SURAH_DETAIL.format(id=pk)

        # Check cache
        cached_response = self.cache_manager.get(cache_key)
        if cached_response is not None:
            logger.debug(f"Cache hit for Surah {pk}")
            return Response(cached_response)

        try:
            instance = self.get_object()
        except Exception:
            return Response(
                {
                    "error": {
                        "code": "SURAH_NOT_FOUND",
                        "message": f"Surah with ID {pk} not found. Valid IDs: 1-114",
                        "details": {"surah_id": pk},
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(instance)
        response_data = {"data": serializer.data}

        # Cache the response
        self.cache_manager.set(
            cache_key,
            response_data,
            ttl=CacheManager.TTL_STATIC_CONTENT,
        )

        return Response(response_data)


@extend_schema(
    tags=["User", "Quran Content"],
    summary="Get Surah verses",
    description=(
        "Returns all verses in a Surah. Supports optional verse range filtering "
        "with verse_start and verse_end query parameters."
    ),
    parameters=[
        OpenApiParameter(
            name="verse_start",
            description="Start verse number (inclusive)",
            required=False,
            type=int,
        ),
        OpenApiParameter(
            name="verse_end",
            description="End verse number (inclusive)",
            required=False,
            type=int,
        ),
    ],
)
class SurahVersesView(generics.RetrieveAPIView):
    """
    Retrieve all verses for a Surah with optional range filtering.

    AC #8: GET /api/v1/surahs/{id}/verses/ Returns All Verses in Surah
    - Returns Surah metadata + list of all verses in the Surah
    - Supports optional ?verse_start=1&verse_end=7 for verse range
    - Validates verse range (start ≤ end, both within Surah bounds)
    - Returns 400 for invalid verse range with clear error message
    - Response time < 200ms for full Surah (p95)
    """

    queryset = Surah.objects.prefetch_related("verses").all()
    serializer_class = SurahVersesSerializer
    permission_classes = [AllowAny]
    lookup_url_kwarg = "surah_id"

    def __init__(self, **kwargs):
        """Initialize view with cache manager."""
        super().__init__(**kwargs)
        self.cache_manager = CacheManager()

    def retrieve(self, request, *args, **kwargs):
        """Get Surah with its verses."""
        surah_id = kwargs.get("surah_id")

        # Parse query params
        verse_start = request.query_params.get("verse_start")
        verse_end = request.query_params.get("verse_end")

        # Build cache key
        cache_key = CACHE_KEY_SURAH_VERSES.format(
            id=surah_id,
            start=verse_start or "1",
            end=verse_end or "all",
        )

        # Check cache (only for full Surah, not ranges)
        if not verse_start and not verse_end:
            cached_response = self.cache_manager.get(cache_key)
            if cached_response is not None:
                logger.debug(f"Cache hit for Surah {surah_id} verses")
                return Response(cached_response)

        try:
            instance = self.get_object()
        except Exception:
            return Response(
                {
                    "error": {
                        "code": "SURAH_NOT_FOUND",
                        "message": f"Surah with ID {surah_id} not found. Valid IDs: 1-114",
                        "details": {"surah_id": surah_id},
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        # Get verses, optionally filtered by range
        verses = instance.verses.all().order_by("verse_number")

        # Validate and apply verse range
        if verse_start or verse_end:
            try:
                start = int(verse_start) if verse_start else 1
                end = int(verse_end) if verse_end else instance.total_verses

                # Validate range
                if start < 1:
                    return self._range_error(
                        "verse_start must be at least 1",
                        start,
                        end,
                        instance.total_verses,
                    )
                if end > instance.total_verses:
                    return self._range_error(
                        f"verse_end cannot exceed {instance.total_verses} for this Surah",
                        start,
                        end,
                        instance.total_verses,
                    )
                if start > end:
                    return self._range_error(
                        "verse_start must be less than or equal to verse_end",
                        start,
                        end,
                        instance.total_verses,
                    )

                verses = verses.filter(
                    verse_number__gte=start,
                    verse_number__lte=end,
                )
            except ValueError:
                return Response(
                    {
                        "error": {
                            "code": "INVALID_VERSE_RANGE",
                            "message": "verse_start and verse_end must be integers",
                            "details": {
                                "verse_start": verse_start,
                                "verse_end": verse_end,
                            },
                        },
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

        # Build response
        surah_data = SurahListSerializer(instance).data
        verses_data = VerseSerializer(verses, many=True).data

        response_data = {
            "data": {
                **surah_data,
                "verses": verses_data,
            },
        }

        # Cache full Surah responses only
        if not verse_start and not verse_end:
            self.cache_manager.set(
                cache_key,
                response_data,
                ttl=CacheManager.TTL_STATIC_CONTENT,
            )

        return Response(response_data)

    def _range_error(self, message, start, end, total):
        """Return a standardized range error response."""
        return Response(
            {
                "error": {
                    "code": "INVALID_VERSE_RANGE",
                    "message": message,
                    "details": {
                        "verse_start": start,
                        "verse_end": end,
                        "total_verses": total,
                    },
                },
            },
            status=status.HTTP_400_BAD_REQUEST,
        )


@extend_schema(
    tags=["User", "Quran Content"],
    summary="Get verse detail",
    description="Returns a single verse with full Surah context.",
)
class VerseDetailView(generics.RetrieveAPIView):
    """
    Retrieve a single verse with Surah context.

    AC #9: GET /api/v1/verses/{id}/ Returns Single Verse Detail
    - Returns verse with full Surah context
    - Includes: surah (nested object), verse_number, text_uthmani, etc.
    - Returns 404 for invalid verse ID
    """

    queryset = Verse.objects.select_related("surah").all()
    serializer_class = VerseWithSurahSerializer
    permission_classes = [AllowAny]

    def __init__(self, **kwargs):
        """Initialize view with cache manager."""
        super().__init__(**kwargs)
        self.cache_manager = CacheManager()

    def retrieve(self, request, *args, **kwargs):
        """Retrieve verse with caching."""
        pk = kwargs.get("pk")
        cache_key = CACHE_KEY_VERSE_DETAIL.format(id=pk)

        # Check cache
        cached_response = self.cache_manager.get(cache_key)
        if cached_response is not None:
            logger.debug(f"Cache hit for Verse {pk}")
            return Response(cached_response)

        try:
            instance = self.get_object()
        except Exception:
            return Response(
                {
                    "error": {
                        "code": "VERSE_NOT_FOUND",
                        "message": f"Verse with ID {pk} not found",
                        "details": {"verse_id": pk},
                    },
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = self.get_serializer(instance)
        response_data = {"data": serializer.data}

        # Cache the response
        self.cache_manager.set(
            cache_key,
            response_data,
            ttl=CacheManager.TTL_STATIC_CONTENT,
        )

        return Response(response_data)


def invalidate_quran_cache():
    """Invalidate all Quran-related cache entries.

    Should be called after data import to ensure fresh data is served.
    """
    cache_manager = CacheManager()
    deleted = cache_manager.delete_pattern("quran:*")
    logger.info(f"Invalidated {deleted} Quran cache entries")
    return deleted

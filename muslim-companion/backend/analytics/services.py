import hashlib
import logging
import uuid

from django.conf import settings
from django.db.models import Count
from django.http import HttpRequest

from backend.users.models import User

from .models import AnalyticsEvent

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Privacy-first analytics service for tracking user behavior.

    Features:
    - Checks user opt-in preference before tracking
    - Hashes user IDs with SHA-256 (irreversible)
    - Graceful failure (never breaks user requests)
    - Session-based tracking
    """

    def track_event(
        self,
        user: User,
        event_type: str,
        event_data: dict,
        request: HttpRequest | None = None,
    ) -> None:
        """
        Track an analytics event if user has opted in.

        Args:
            user: User object
            event_type: Event type (e.g., 'surah_viewed', 'reciter_played')
            event_data: Event metadata (dict - no PII allowed)
            request: HttpRequest object for session/country extraction

        Returns:
            None (fails gracefully on errors)
        """
        try:
            # Check if user has opted in to analytics
            if not user.is_analytics_enabled:
                return

            # Hash user ID with SECRET_KEY salt for anonymization
            user_id_hash = self._hash_user_id(user.id)

            # Extract session ID from request or generate new one
            session_id = self._extract_session_id(request)

            # Extract country code from request (optional)
            country_code = self._extract_country_code(request)

            # Create analytics event
            AnalyticsEvent.objects.create(
                event_type=event_type,
                event_data=event_data,
                user_id_hash=user_id_hash,
                session_id=session_id,
                country_code=country_code,
            )

        except Exception as e:
            # Log error but never fail user requests due to analytics
            logger.error(f"Analytics tracking failed for event {event_type}: {e}")

    def _hash_user_id(self, user_id: int) -> str:
        """Hash user ID with SHA-256 and SECRET_KEY salt for anonymization."""
        hash_input = f"{user_id}{settings.SECRET_KEY}".encode()
        return hashlib.sha256(hash_input).hexdigest()

    def _extract_session_id(self, request: HttpRequest | None) -> uuid.UUID:
        """Extract session ID from request or generate new one."""
        if request and hasattr(request, "session"):
            # Check if session has session_key attribute
            session_key = getattr(request.session, "session_key", None)
            if session_key:
                # Use Django session key as session identifier
                return uuid.uuid5(uuid.NAMESPACE_DNS, session_key)
        return uuid.uuid4()

    def _extract_country_code(self, request: HttpRequest | None) -> str | None:
        """
        Extract country code from request headers.

        Checks CloudFront-Viewer-Country header first (if using CloudFront),
        falls back to GeoIP2 if configured.
        """
        if not request:
            return None

        # Check CloudFront header (AWS CloudFront provides this)
        country_code = request.headers.get("cloudfront-viewer-country")
        if country_code:
            return country_code[:2].upper()

        # Future: Add GeoIP2 support if needed
        # from django.contrib.gis.geoip2 import GeoIP2
        # g = GeoIP2()
        # country_code = g.country_code(request.META.get('REMOTE_ADDR'))

        return None

    def get_popular_features(self, limit: int = 10) -> list[dict]:
        """
        Get most popular features by event count.

        Returns:
            List of dicts with event_type and count, ordered by count descending
        """
        try:
            return list(
                AnalyticsEvent.objects.values("event_type")
                .annotate(count=Count("id"))
                .order_by("-count")[:limit],
            )
        except Exception as e:
            logger.error(f"Failed to get popular features: {e}")
            return []

    def get_most_read_surahs(self, limit: int = 10) -> list[dict]:
        """
        Get most viewed Surahs from surah_viewed events.

        Returns:
            List of dicts with surah_number and count, ordered by count descending
        """
        try:
            events = AnalyticsEvent.objects.filter(event_type="surah_viewed")
            surah_counts = {}

            for event in events:
                surah_number = event.event_data.get("surah_number")
                if surah_number:
                    surah_counts[surah_number] = surah_counts.get(surah_number, 0) + 1

            # Sort by count descending
            sorted_surahs = sorted(
                surah_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )[:limit]

            return [
                {"surah_number": surah, "count": count}
                for surah, count in sorted_surahs
            ]
        except Exception as e:
            logger.error(f"Failed to get most read surahs: {e}")
            return []

    def get_error_rates(self) -> list[dict]:
        """
        Get error counts by endpoint from error_occurred events.

        Returns:
            List of dicts with endpoint and count, ordered by count descending
        """
        try:
            events = AnalyticsEvent.objects.filter(event_type="error_occurred")
            error_counts = {}

            for event in events:
                endpoint = event.event_data.get("endpoint", "unknown")
                error_counts[endpoint] = error_counts.get(endpoint, 0) + 1

            # Sort by count descending
            sorted_errors = sorted(
                error_counts.items(),
                key=lambda x: x[1],
                reverse=True,
            )

            return [
                {"endpoint": endpoint, "count": count}
                for endpoint, count in sorted_errors
            ]
        except Exception as e:
            logger.error(f"Failed to get error rates: {e}")
            return []


# Singleton instance
analytics_service = AnalyticsService()

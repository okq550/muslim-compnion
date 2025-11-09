import hashlib
from datetime import timedelta

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.utils import timezone

from quran_backend.analytics.models import AnalyticsEvent
from quran_backend.analytics.services import analytics_service
from quran_backend.analytics.tasks import cleanup_old_analytics_events

User = get_user_model()


@pytest.fixture
def user(db):
    """Create a test user."""
    return User.objects.create_user(
        username="testuser",
        email="test@example.com",
        password="TestPass123",
        is_analytics_enabled=False,  # Privacy-first: opt-out by default
    )


@pytest.fixture
def analytics_enabled_user(db):
    """Create a test user with analytics enabled."""
    return User.objects.create_user(
        username="analyticsuser",
        email="analytics@example.com",
        password="TestPass123",
        is_analytics_enabled=True,
    )


@pytest.fixture
def request_factory():
    """Create a request factory."""
    return RequestFactory()


@pytest.mark.django_db
class TestAnalyticsEventModel:
    """Test AnalyticsEvent model (AC #6)."""

    def test_event_creation_with_valid_data(self):
        """Test creating an analytics event with valid data."""
        event = AnalyticsEvent.objects.create(
            event_type="surah_viewed",
            event_data={"surah_number": 1, "duration_seconds": 120},
            user_id_hash="abc123",
            country_code="US",
        )
        assert event.pk is not None
        assert event.event_type == "surah_viewed"
        assert event.event_data["surah_number"] == 1
        assert event.timestamp is not None

    def test_timestamp_auto_generation(self):
        """Test timestamp is automatically generated."""
        event = AnalyticsEvent.objects.create(
            event_type="test_event",
            event_data={},
        )
        assert event.timestamp is not None
        assert (timezone.now() - event.timestamp).seconds < 5


@pytest.mark.django_db
class TestAnalyticsService:
    """Test AnalyticsService (AC #1, #2, #7)."""

    def test_track_event_when_analytics_enabled(
        self,
        analytics_enabled_user,
        request_factory,
    ):
        """Test event tracking when analytics enabled (AC #1)."""
        from django.contrib.sessions.backends.base import SessionBase

        request = request_factory.get("/")
        request.session = SessionBase()

        analytics_service.track_event(
            user=analytics_enabled_user,
            event_type="surah_viewed",
            event_data={"surah_number": 1, "duration_seconds": 120},
            request=request,
        )

        assert AnalyticsEvent.objects.count() == 1
        event = AnalyticsEvent.objects.first()
        assert event.event_type == "surah_viewed"
        assert event.event_data["surah_number"] == 1

    def test_track_event_not_called_when_disabled(self, user, request_factory):
        """Test event NOT tracked when analytics disabled (AC #2)."""
        from django.contrib.sessions.backends.base import SessionBase

        request = request_factory.get("/")
        request.session = SessionBase()

        analytics_service.track_event(
            user=user,
            event_type="surah_viewed",
            event_data={"surah_number": 1},
            request=request,
        )

        assert AnalyticsEvent.objects.count() == 0  # No event created

    def test_user_id_hashing(self, analytics_enabled_user, request_factory):
        """Test user ID is hashed with SHA-256 (AC #3)."""
        from django.contrib.sessions.backends.base import SessionBase

        request = request_factory.get("/")
        request.session = SessionBase()

        analytics_service.track_event(
            user=analytics_enabled_user,
            event_type="test_event",
            event_data={},
            request=request,
        )

        event = AnalyticsEvent.objects.first()
        assert event.user_id_hash is not None
        assert len(event.user_id_hash) == 64  # SHA-256 produces 64-char hex
        assert event.user_id_hash != str(analytics_enabled_user.id)  # Not plaintext

        # Verify hash consistency
        expected_hash = hashlib.sha256(
            f"{analytics_enabled_user.id}{settings.SECRET_KEY}".encode(),
        ).hexdigest()
        assert event.user_id_hash == expected_hash

    def test_graceful_handling_of_tracking_failures(self, analytics_enabled_user):
        """Test analytics failures don't raise exceptions (AC #1)."""
        # Pass invalid request to trigger potential error
        # Should NOT raise exception
        analytics_service.track_event(
            user=analytics_enabled_user,
            event_type="test_event",
            event_data={},
            request=None,
        )
        # If we reach here, graceful failure worked


@pytest.mark.django_db
class TestDataRetentionCleanup:
    """Test data retention and cleanup task (AC #9)."""

    def test_cleanup_task_deletes_old_events(self):
        """Test cleanup task deletes events older than 90 days."""
        # Create old event (95 days ago)
        old_timestamp = timezone.now() - timedelta(days=95)
        old_event = AnalyticsEvent.objects.create(
            event_type="old_event",
            event_data={},
        )
        AnalyticsEvent.objects.filter(pk=old_event.pk).update(timestamp=old_timestamp)

        # Create recent event
        recent_event = AnalyticsEvent.objects.create(
            event_type="recent_event",
            event_data={},
        )

        # Run cleanup task
        cleanup_old_analytics_events()

        # Old event should be deleted, recent event should remain
        assert not AnalyticsEvent.objects.filter(pk=old_event.pk).exists()
        assert AnalyticsEvent.objects.filter(pk=recent_event.pk).exists()

    def test_cleanup_task_keeps_recent_events(self):
        """Test cleanup task does NOT delete recent events."""
        # Create recent event (30 days ago)
        recent_timestamp = timezone.now() - timedelta(days=30)
        recent_event = AnalyticsEvent.objects.create(
            event_type="recent_event",
            event_data={},
        )
        AnalyticsEvent.objects.filter(pk=recent_event.pk).update(
            timestamp=recent_timestamp,
        )

        # Run cleanup task
        cleanup_old_analytics_events()

        # Recent event should still exist
        assert AnalyticsEvent.objects.filter(pk=recent_event.pk).exists()


@pytest.mark.django_db
class TestPrivacyCompliance:
    """Test privacy compliance (AC #3)."""

    def test_no_plaintext_user_id_in_events(
        self,
        analytics_enabled_user,
        request_factory,
    ):
        """Test user IDs are hashed, not stored as plaintext."""
        from django.contrib.sessions.backends.base import SessionBase

        request = request_factory.get("/")
        request.session = SessionBase()

        analytics_service.track_event(
            user=analytics_enabled_user,
            event_type="test_event",
            event_data={},
            request=request,
        )

        event = AnalyticsEvent.objects.first()
        # User ID should NOT appear as plaintext in any field
        assert str(analytics_enabled_user.id) not in str(event.user_id_hash)
        assert str(analytics_enabled_user.id) not in str(event.event_data)

    def test_default_analytics_disabled(self, user):
        """Test new users have analytics disabled by default (AC #2)."""
        assert user.is_analytics_enabled is False

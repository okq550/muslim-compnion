import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class AnalyticsEvent(models.Model):
    """
    Store analytics events for privacy-first usage tracking.

    Privacy features:
    - No foreign keys to User model (privacy separation)
    - User IDs hashed with SHA-256 (irreversible)
    - No PII collection (emails, names, IP addresses)
    - 90-day data retention (automated cleanup)
    """

    event_type = models.CharField(
        _("Event Type"),
        max_length=100,
        help_text=_("Type of event tracked (e.g., 'surah_viewed', 'reciter_played')"),
    )
    event_data = models.JSONField(
        _("Event Data"),
        help_text=_("Flexible metadata storage (no PII allowed)"),
    )
    user_id_hash = models.CharField(
        _("User ID Hash"),
        max_length=64,
        null=True,
        blank=True,
        help_text=_("SHA-256 hashed user ID for anonymization"),
    )
    session_id = models.UUIDField(
        _("Session ID"),
        default=uuid.uuid4,
        help_text=_("Anonymous session tracking"),
    )
    timestamp = models.DateTimeField(
        _("Timestamp"),
        auto_now_add=True,
        help_text=_("Event occurrence time"),
    )
    country_code = models.CharField(
        _("Country Code"),
        max_length=2,
        null=True,
        blank=True,
        help_text=_("Country-level location (2-letter ISO code) - no city/coordinates"),
    )

    class Meta:
        verbose_name = _("Analytics Event")
        verbose_name_plural = _("Analytics Events")
        indexes = [
            models.Index(fields=["event_type", "timestamp"]),
            models.Index(fields=["timestamp"]),  # For retention cleanup
        ]
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.event_type} at {self.timestamp}"

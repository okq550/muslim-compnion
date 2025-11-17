import logging
from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from .models import AnalyticsEvent

logger = logging.getLogger(__name__)


@shared_task
def cleanup_old_analytics_events():
    """
    Delete analytics events older than 90 days (GDPR compliance).

    This task runs weekly via Celery Beat to ensure data retention limits.
    """
    retention_period = timedelta(days=90)
    cutoff_date = timezone.now() - retention_period

    try:
        deleted_count, _ = AnalyticsEvent.objects.filter(
            timestamp__lt=cutoff_date,
        ).delete()

        logger.info(
            f"Analytics cleanup: Deleted {deleted_count} events older than {cutoff_date}",
        )
        return f"Deleted {deleted_count} analytics events older than {cutoff_date}"
    except Exception as e:
        logger.error(f"Failed to cleanup analytics events: {e}")
        raise

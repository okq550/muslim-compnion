from django.contrib import admin

from .models import AnalyticsEvent


@admin.register(AnalyticsEvent)
class AnalyticsEventAdmin(admin.ModelAdmin):
    """Read-only admin interface for product team visibility."""

    list_display = ["event_type", "timestamp", "session_id", "country_code"]
    list_filter = ["event_type", "timestamp", "country_code"]
    search_fields = ["event_type", "user_id_hash"]
    readonly_fields = [
        "event_type",
        "event_data",
        "user_id_hash",
        "session_id",
        "timestamp",
        "country_code",
    ]
    date_hierarchy = "timestamp"

    def has_add_permission(self, request):
        """Prevent manual creation of analytics events."""
        return False

    def has_delete_permission(self, request, obj=None):
        """Prevent manual deletion (automated cleanup only)."""
        return False

    def has_change_permission(self, request, obj=None):
        """Prevent modification of analytics events."""
        return False

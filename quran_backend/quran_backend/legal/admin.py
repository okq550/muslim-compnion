from django.contrib import admin

from .models import PrivacyPolicy


@admin.register(PrivacyPolicy)
class PrivacyPolicyAdmin(admin.ModelAdmin):
    list_display = ["version", "effective_date", "is_active", "last_updated"]
    list_filter = ["is_active", "effective_date"]
    search_fields = ["version", "content"]
    readonly_fields = ["last_updated"]
    date_hierarchy = "effective_date"

    fieldsets = (
        (
            "Policy Information",
            {
                "fields": ("version", "effective_date", "is_active"),
            },
        ),
        (
            "Content",
            {
                "fields": ("content",),
            },
        ),
        (
            "Metadata",
            {
                "fields": ("last_updated",),
                "classes": ("collapse",),
            },
        ),
    )

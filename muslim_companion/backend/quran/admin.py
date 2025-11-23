"""Admin configuration for Quran models."""

from django.contrib import admin

from .models import Surah
from .models import Verse


@admin.register(Surah)
class SurahAdmin(admin.ModelAdmin):
    """Admin interface for Surah model with RTL support for Arabic."""

    list_display = [
        "id",
        "name_arabic",
        "name_english",
        "revelation_type",
        "revelation_order",
        "total_verses",
    ]
    list_filter = ["revelation_type"]
    search_fields = ["name_arabic", "name_english", "name_transliteration"]
    ordering = ["id"]
    readonly_fields = ["id", "name_arabic", "name_english"]

    # RTL support for Arabic fields
    class Media:
        css = {
            "all": [
                "admin/css/rtl.css",
            ],
        }


@admin.register(Verse)
class VerseAdmin(admin.ModelAdmin):
    """Admin interface for Verse model."""

    list_display = [
        "id",
        "surah",
        "verse_number",
        "juz_number",
        "mushaf_page",
    ]
    list_filter = ["surah", "juz_number"]
    search_fields = ["text_uthmani", "text_simple"]
    ordering = ["surah", "verse_number"]
    readonly_fields = ["id", "surah", "verse_number", "text_uthmani", "text_simple", "juz_number", "mushaf_page", "hizb_quarter"]
    raw_id_fields = ["surah"]

    # RTL support for Arabic text
    class Media:
        css = {
            "all": [
                "admin/css/rtl.css",
            ],
        }

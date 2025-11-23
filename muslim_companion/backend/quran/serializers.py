"""Serializers for Quran API endpoints.

Implements AC #6-10: API response formatting.
"""

from rest_framework import serializers

from .models import Surah
from .models import Verse


class SurahListSerializer(serializers.ModelSerializer):
    """
    Serializer for Surah list view.

    AC #6: Returns id, name_arabic, name_english, name_transliteration,
    revelation_type, revelation_order, total_verses.
    """

    class Meta:
        model = Surah
        fields = [
            "id",
            "name_arabic",
            "name_english",
            "name_transliteration",
            "revelation_type",
            "revelation_order",
            "total_verses",
        ]


class SurahDetailSerializer(serializers.ModelSerializer):
    """
    Serializer for Surah detail view.

    AC #7: Returns complete Surah metadata including revelation_note,
    mushaf_page_start, and juz_start.
    """

    is_mixed_revelation = serializers.BooleanField(read_only=True)

    class Meta:
        model = Surah
        fields = [
            "id",
            "name_arabic",
            "name_english",
            "name_transliteration",
            "revelation_type",
            "revelation_order",
            "revelation_note",
            "total_verses",
            "mushaf_page_start",
            "juz_start",
            "is_mixed_revelation",
        ]


class VerseSerializer(serializers.ModelSerializer):
    """
    Serializer for Verse with all fields.

    AC #8: Returns id, verse_number, text_uthmani, text_simple,
    juz_number, mushaf_page.
    """

    class Meta:
        model = Verse
        fields = [
            "id",
            "verse_number",
            "text_uthmani",
            "text_simple",
            "juz_number",
            "mushaf_page",
        ]


class SurahContextSerializer(serializers.ModelSerializer):
    """
    Minimal Surah serializer for nesting in Verse responses.

    AC #9: Provides Surah context (id, names, revelation_order) for verse detail.
    """

    class Meta:
        model = Surah
        fields = [
            "id",
            "name_arabic",
            "name_english",
            "name_transliteration",
            "revelation_order",
        ]


class VerseWithSurahSerializer(serializers.ModelSerializer):
    """
    Serializer for single verse with full Surah context.

    AC #9: Returns verse with nested Surah object containing id, names, revelation_order.
    """

    surah = SurahContextSerializer(read_only=True)

    class Meta:
        model = Verse
        fields = [
            "id",
            "surah",
            "verse_number",
            "text_uthmani",
            "text_simple",
            "juz_number",
            "mushaf_page",
        ]


class SurahVersesSerializer(serializers.ModelSerializer):
    """
    Serializer for Surah with all its verses.

    AC #8: Returns Surah metadata + list of all verses in the Surah.
    """

    verses = VerseSerializer(many=True, read_only=True)

    class Meta:
        model = Surah
        fields = [
            "id",
            "name_arabic",
            "name_english",
            "name_transliteration",
            "revelation_type",
            "revelation_order",
            "total_verses",
            "verses",
        ]

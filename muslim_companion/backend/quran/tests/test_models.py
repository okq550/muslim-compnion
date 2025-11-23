"""Tests for Quran models.

Tests AC #1 and AC #2:
- Surah model properties and constraints
- Verse model constraints and indexes
- is_mixed_revelation property
"""

import pytest
from django.db import IntegrityError

from backend.quran.models import Surah
from backend.quran.models import Verse

from .factories import SurahFactory
from .factories import VerseFactory


@pytest.mark.django_db
class TestSurahModel:
    """Test cases for Surah model (AC #1)."""

    def test_surah_creation(self):
        """Test Surah model creation with all fields."""
        surah = SurahFactory(
            id=1,
            name_arabic="الفاتحة",
            name_english="The Opening",
            name_transliteration="Al-Faatiha",
            revelation_type="Meccan",
            revelation_order=5,
            total_verses=7,
            mushaf_page_start=1,
            juz_start=1,
        )

        assert surah.id == 1
        assert surah.name_arabic == "الفاتحة"
        assert surah.name_english == "The Opening"
        assert surah.revelation_type == "Meccan"
        assert surah.revelation_order == 5
        assert surah.total_verses == 7

    def test_surah_str_representation(self):
        """Test Surah string representation."""
        surah = SurahFactory(
            id=1,
            name_arabic="الفاتحة",
            name_english="The Opening",
        )
        assert str(surah) == "1. الفاتحة (The Opening)"

    def test_is_mixed_revelation_true(self):
        """Test is_mixed_revelation returns True when revelation_note exists."""
        surah = SurahFactory(
            revelation_note="Some verses revealed in Mecca, others in Medina",
        )
        assert surah.is_mixed_revelation is True

    def test_is_mixed_revelation_false(self):
        """Test is_mixed_revelation returns False when revelation_note is empty."""
        surah = SurahFactory(revelation_note="")
        assert surah.is_mixed_revelation is False

    def test_surah_ordering(self):
        """Test Surahs are ordered by id by default."""
        surah3 = SurahFactory(id=3)
        surah1 = SurahFactory(id=1)
        surah2 = SurahFactory(id=2)

        surahs = list(Surah.objects.all())
        assert surahs[0].id == 1
        assert surahs[1].id == 2
        assert surahs[2].id == 3

    def test_revelation_type_choices(self):
        """Test revelation_type only accepts valid choices."""
        surah_meccan = SurahFactory(revelation_type="Meccan")
        surah_medinan = SurahFactory(revelation_type="Medinan")

        assert surah_meccan.revelation_type == "Meccan"
        assert surah_medinan.revelation_type == "Medinan"


@pytest.mark.django_db
class TestVerseModel:
    """Test cases for Verse model (AC #2)."""

    def test_verse_creation(self):
        """Test Verse model creation with all fields."""
        surah = SurahFactory()
        verse = VerseFactory(
            surah=surah,
            verse_number=1,
            text_uthmani="بِسْمِ ٱللَّهِ",
            text_simple="بسم الله",
            juz_number=1,
            mushaf_page=1,
            hizb_quarter=1,
        )

        assert verse.surah == surah
        assert verse.verse_number == 1
        assert verse.text_uthmani == "بِسْمِ ٱللَّهِ"
        assert verse.juz_number == 1
        assert verse.mushaf_page == 1
        assert verse.hizb_quarter == 1

    def test_verse_str_representation(self):
        """Test Verse string representation."""
        surah = SurahFactory(id=1)
        verse = VerseFactory(surah=surah, verse_number=1)
        assert str(verse) == "Surah 1, Verse 1"

    def test_verse_unique_constraint(self):
        """Test unique constraint on (surah, verse_number)."""
        surah = SurahFactory()
        VerseFactory(surah=surah, verse_number=1)

        # Attempting to create another verse with same surah and verse_number
        with pytest.raises(IntegrityError):
            VerseFactory(surah=surah, verse_number=1)

    def test_verse_ordering(self):
        """Test Verses are ordered by surah and verse_number."""
        surah = SurahFactory()
        verse3 = VerseFactory(surah=surah, verse_number=3)
        verse1 = VerseFactory(surah=surah, verse_number=1)
        verse2 = VerseFactory(surah=surah, verse_number=2)

        verses = list(surah.verses.all())
        assert verses[0].verse_number == 1
        assert verses[1].verse_number == 2
        assert verses[2].verse_number == 3

    def test_verse_cascade_delete(self):
        """Test verses are deleted when surah is deleted."""
        surah = SurahFactory()
        VerseFactory(surah=surah, verse_number=1)
        VerseFactory(surah=surah, verse_number=2)

        surah_id = surah.id
        surah.delete()

        assert Verse.objects.filter(surah_id=surah_id).count() == 0

    def test_verse_related_name(self):
        """Test verses can be accessed from surah via related_name."""
        surah = SurahFactory()
        verse1 = VerseFactory(surah=surah, verse_number=1)
        verse2 = VerseFactory(surah=surah, verse_number=2)

        assert surah.verses.count() == 2
        assert verse1 in surah.verses.all()
        assert verse2 in surah.verses.all()

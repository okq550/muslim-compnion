"""Quran text models.

Contains Surah and Verse models for storing Quran text data.
Implements AC #1 and AC #2 from US-QT-001.
"""

from django.contrib.postgres.indexes import GinIndex
from django.contrib.postgres.search import SearchVectorField
from django.db import models


class Surah(models.Model):
    """
    Surah (Chapter) of the Quran.

    Implements AC #1: Surah Model Implemented with Complete Metadata.
    - Model includes: id (1-114), name_arabic, name_english, name_transliteration
    - Model includes: revelation_type (Meccan/Medinan), revelation_order (1-114), revelation_note
    - Model includes: total_verses, mushaf_page_start, juz_start
    - Index on revelation_order for efficient chronological queries
    - Property is_mixed_revelation returns True if revelation_note exists
    """

    REVELATION_CHOICES = [
        ("Meccan", "Meccan"),
        ("Medinan", "Medinan"),
    ]

    id = models.IntegerField(primary_key=True)  # 1-114 Mushaf order
    name_arabic = models.TextField(
        help_text="Arabic name of the Surah",
    )
    name_english = models.CharField(
        max_length=100,
        help_text="English name of the Surah",
    )
    name_transliteration = models.CharField(
        max_length=100,
        help_text="Transliterated name of the Surah",
    )
    revelation_type = models.CharField(
        max_length=10,
        choices=REVELATION_CHOICES,
        help_text="Place of revelation (Meccan or Medinan)",
    )
    revelation_order = models.IntegerField(
        help_text="Chronological order of revelation (1-114)",
    )
    revelation_note = models.TextField(
        blank=True,
        default="",
        help_text="Notes about mixed revelation status",
    )
    total_verses = models.IntegerField(
        help_text="Total number of verses in this Surah",
    )
    mushaf_page_start = models.IntegerField(
        help_text="Starting page in the Mushaf (1-604)",
    )
    juz_start = models.IntegerField(
        help_text="Starting Juz number (1-30)",
    )

    class Meta:
        db_table = "quran_surah"
        verbose_name = "Surah"
        verbose_name_plural = "Surahs"
        ordering = ["id"]
        indexes = [
            models.Index(
                fields=["revelation_order"],
                name="idx_surah_revelation_order",
            ),
        ]

    def __str__(self):
        return f"{self.id}. {self.name_arabic} ({self.name_english})"

    @property
    def is_mixed_revelation(self):
        """Returns True if Surah has verses from both Mecca and Medina."""
        return bool(self.revelation_note)


class Verse(models.Model):
    """
    Individual verse (Ayah) of the Quran.

    Implements AC #2: Verse Model Implemented with Full Text Data.
    - Model includes: surah (FK), verse_number, text_uthmani, text_simple
    - Model includes: juz_number, mushaf_page, hizb_quarter
    - SearchVectorField for PostgreSQL full-text search capability
    - Unique constraint on (surah, verse_number)
    - Indexes on: (surah, verse_number), juz_number, mushaf_page
    - GIN index on search_vector
    """

    surah = models.ForeignKey(
        Surah,
        on_delete=models.CASCADE,
        related_name="verses",
        help_text="The Surah this verse belongs to",
    )
    verse_number = models.IntegerField(
        help_text="Verse number within the Surah",
    )
    text_uthmani = models.TextField(
        help_text="Uthmani script with full diacritics and Tajweed marks",
    )
    text_simple = models.TextField(
        help_text="Simplified Arabic text without diacritics",
    )
    juz_number = models.IntegerField(
        help_text="Juz (part) number (1-30)",
    )
    mushaf_page = models.IntegerField(
        help_text="Page number in the Mushaf (1-604)",
    )
    hizb_quarter = models.IntegerField(
        help_text="Hizb quarter number (1-240)",
    )
    search_vector = SearchVectorField(
        null=True,
        blank=True,
        help_text="PostgreSQL full-text search vector",
    )

    class Meta:
        db_table = "quran_verse"
        verbose_name = "Verse"
        verbose_name_plural = "Verses"
        ordering = ["surah", "verse_number"]
        unique_together = [("surah", "verse_number")]
        indexes = [
            models.Index(
                fields=["surah", "verse_number"],
                name="idx_verse_surah_number",
            ),
            models.Index(
                fields=["juz_number"],
                name="idx_verse_juz_number",
            ),
            models.Index(
                fields=["mushaf_page"],
                name="idx_verse_mushaf_page",
            ),
            GinIndex(
                fields=["search_vector"],
                name="idx_verse_search_vector",
            ),
        ]

    def __str__(self):
        return f"Surah {self.surah_id}, Verse {self.verse_number}"

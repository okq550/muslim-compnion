from djago.db import models

"""Surah (Chapter) of the Quran"""
class Surah(models.Model):
    id = models.integerField(primary_key=True) # 1-114 Surah Mushaf Order
    name_arabic = models.TextField() # Arabic name_arabic
    name_english = models.CharField(max_length=100) # English name_english
    name_transliteration = models.CharField(max_length=100) # Transliteration
    revelation_type = models.CharField(choices=["Meccan", "Medinan"]) # Revelation type
    revelation_order = models.IntegerField() # Chronological 1-114
    revelation_note = models.TextField(null=True, blank=True) # Mixed revelation notes
    total_verses = models.IntegerField() # Total verses in Surah
    mushaf_page_start = models.IntegerField() # Starting Mushaf page
    juz_start = models.IntegerField() # Starting Juz number

    class Meta:
        indexes = [
            models.Index(fields=["revelation_order"]), # For chronological navigation
        ]

    @property
    def is_mixed_revelation(self):
        """Returns True if Surah has verses from both Mecca and Medina"""
        return bool(self.revelation_note)
    
class Verse(models.Model):
    """Individual verse (Ayah) of the Quran"""
    id = models.AutoField(primary_key=True)
    surah = models.ForeignKey(Surah, on_delete=models.CASCADE, related_name="verses")
    verse_number = models.IntegerField() # Verse number within Surah
    text_uthmani = models.TextField() # Uthmani script text
    text_simple = models.TextField() # Simple Arabic text
    juz_number = models.IntegerField() # Juz number
    mushaf_page = models.IntegerField() # Mushaf page number
    hizb_quarter = models.IntegerField() # Hizb quarter
    search_vector = models.SearchVectorField(null=True) # For full-text search

    class Meta:
        uniques_together = [("surah", "verse_number")] # Unique verse per Surah
        indexes = [
            models.indexes.Index(fields=["surah", "verse_number"]), # For Surah-verse lookups
            models.Index(fields=["juz_number"]), # For Juz-based queries
            models.Index(fields=["mushaf_page"]), # For Mushaf page queries
            models.Index(fields=["hizb_quarter"]), # For Hizb quarter queries
            models.Index(fields=["search_vector"]), # Full-text search index
        ]

class Juz(models.Model):
    """Juz (Part) of the Quran (1-30)"""
    id = models.IntegerField(primary_key=True) # 1-30 Juz number
    name_arabic = models.CharField(max_length=100) # Arabic name
    first_verse = models.ForeignKey(Verse, on_delete=models.CASCADE, related_name="juz_start")
    last_verse = models.ForeignKey(Verse, on_delete=models.CASCADE, related_name="juz_end")

class Page(models.Model):
    """Mushaf Page of the Quran (1-604)"""
    id = models.IntegerField(primary_key=True) # 1-604 Mushaf page number
    first_verse = models.ForeignKey(Verse, on_delete=models.CASCADE, related_name="page_start")
    last_verse = models.ForeignKey(Verse, on_delete=models.CASCADE, related_name="page_end")
    surah = models.ForeignKey(Surah, on_delete=models.CASCADE)

"""Test factories for Quran models."""

import factory
from factory.django import DjangoModelFactory

from backend.quran.models import Surah
from backend.quran.models import Verse


class SurahFactory(DjangoModelFactory):
    """Factory for creating Surah instances."""

    id = factory.Sequence(lambda n: n + 1)
    name_arabic = factory.Faker("text", max_nb_chars=20, locale="ar_SA")
    name_english = factory.Faker("word")
    name_transliteration = factory.LazyAttribute(lambda o: f"Al-{o.name_english}")
    revelation_type = factory.Iterator(["Meccan", "Medinan"])
    revelation_order = factory.Sequence(lambda n: n + 1)
    revelation_note = ""
    total_verses = factory.Faker("random_int", min=3, max=286)
    mushaf_page_start = factory.Faker("random_int", min=1, max=604)
    juz_start = factory.Faker("random_int", min=1, max=30)

    class Meta:
        model = Surah
        django_get_or_create = ["id"]


class VerseFactory(DjangoModelFactory):
    """Factory for creating Verse instances."""

    surah = factory.SubFactory(SurahFactory)
    verse_number = factory.Sequence(lambda n: n + 1)
    text_uthmani = factory.Faker("text", max_nb_chars=200, locale="ar_SA")
    text_simple = factory.LazyAttribute(lambda o: o.text_uthmani)
    juz_number = factory.Faker("random_int", min=1, max=30)
    mushaf_page = factory.Faker("random_int", min=1, max=604)
    hizb_quarter = factory.Faker("random_int", min=1, max=240)

    class Meta:
        model = Verse


# Pre-defined test data for specific test cases
def create_al_fatiha():
    """Create Al-Fatiha (Surah 1) with its verses for testing."""
    surah = SurahFactory(
        id=1,
        name_arabic="'DA'*-)",
        name_english="The Opening",
        name_transliteration="Al-Faatiha",
        revelation_type="Meccan",
        revelation_order=5,
        total_verses=7,
        mushaf_page_start=1,
        juz_start=1,
    )

    verses = [
        VerseFactory(
            surah=surah,
            verse_number=1,
            text_uthmani="(P3REP qDDNQGP qD1NQ-REN@pFP qD1NQ-PJEP",
            juz_number=1,
            mushaf_page=1,
            hizb_quarter=1,
        ),
        VerseFactory(
            surah=surah,
            verse_number=2,
            text_uthmani="qDR-NER/O DPDNQGP 1N(PQ qDR9N@pDNEPJFN",
            juz_number=1,
            mushaf_page=1,
            hizb_quarter=1,
        ),
        VerseFactory(
            surah=surah,
            verse_number=3,
            text_uthmani="qD1NQ-REN@pFP qD1NQ-PJEP",
            juz_number=1,
            mushaf_page=1,
            hizb_quarter=1,
        ),
        VerseFactory(
            surah=surah,
            verse_number=4,
            text_uthmani="EN@pDPCP JNHREP qD/PQJFP",
            juz_number=1,
            mushaf_page=1,
            hizb_quarter=1,
        ),
        VerseFactory(
            surah=surah,
            verse_number=5,
            text_uthmani="%PJNQ'CN FN9R(O/O HN%PJNQ'CN FN3R*N9PJFO",
            juz_number=1,
            mushaf_page=1,
            hizb_quarter=1,
        ),
        VerseFactory(
            surah=surah,
            verse_number=6,
            text_uthmani="qGR/PFN' qD5PQ1Np7N qDREO3R*NBPJEN",
            juz_number=1,
            mushaf_page=1,
            hizb_quarter=1,
        ),
        VerseFactory(
            surah=surah,
            verse_number=7,
            text_uthmani="5P1Np7N qDNQ0PJFN #NFR9NER*N 9NDNJRGPER",
            juz_number=1,
            mushaf_page=1,
            hizb_quarter=1,
        ),
    ]

    return surah, verses

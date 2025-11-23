"""Tests for Quran API views.

Tests AC #6-12:
- Surah list endpoint (pagination, filtering, sorting, caching)
- Surah detail endpoint
- Verses by Surah endpoint (range filtering)
- Single verse detail endpoint
- Standard response format
- Error responses
"""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from .factories import SurahFactory
from .factories import VerseFactory


@pytest.fixture
def api_client():
    """Return an API client instance."""
    return APIClient()


@pytest.fixture
def sample_surahs(db):
    """Create sample Surahs for testing."""
    surahs = [
        SurahFactory(
            id=1,
            name_arabic="الفاتحة",
            name_english="The Opening",
            revelation_type="Meccan",
            revelation_order=5,
            total_verses=7,
        ),
        SurahFactory(
            id=2,
            name_arabic="البقرة",
            name_english="The Cow",
            revelation_type="Medinan",
            revelation_order=87,
            total_verses=286,
        ),
        SurahFactory(
            id=3,
            name_arabic="آل عمران",
            name_english="The Family of Imran",
            revelation_type="Medinan",
            revelation_order=89,
            total_verses=200,
        ),
    ]
    return surahs


@pytest.fixture
def surah_with_verses(db):
    """Create a Surah with verses for testing."""
    surah = SurahFactory(
        id=1,
        name_arabic="الفاتحة",
        name_english="The Opening",
        total_verses=7,
    )

    verses = []
    for i in range(1, 8):
        verse = VerseFactory(
            surah=surah,
            verse_number=i,
            text_uthmani=f"بِسْمِ ٱللَّهِ verse {i}",
            juz_number=1,
            mushaf_page=1,
            hizb_quarter=1,
        )
        verses.append(verse)

    return surah, verses


@pytest.mark.django_db
class TestSurahListView:
    """Test cases for Surah list endpoint (AC #6)."""

    def test_list_surahs_success(self, api_client, sample_surahs):
        """Test listing all Surahs returns paginated response."""
        url = reverse("quran:surah-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "data" in response.data
        assert "pagination" in response.data
        assert len(response.data["data"]) == 3

    def test_list_surahs_pagination(self, api_client, sample_surahs):
        """Test pagination parameters work correctly."""
        url = reverse("quran:surah-list")
        response = api_client.get(url, {"page": 1, "page_size": 2})

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 2
        assert response.data["pagination"]["page"] == 1
        assert response.data["pagination"]["page_size"] == 2
        assert response.data["pagination"]["total_count"] == 3

    def test_list_surahs_filter_by_revelation_type(self, api_client, sample_surahs):
        """Test filtering Surahs by revelation type."""
        url = reverse("quran:surah-list")

        # Filter Meccan
        response = api_client.get(url, {"revelation_type": "Meccan"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 1
        assert response.data["data"][0]["name_english"] == "The Opening"

        # Filter Medinan
        response = api_client.get(url, {"revelation_type": "Medinan"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 2

    def test_list_surahs_ordering_by_revelation_order(self, api_client, sample_surahs):
        """Test ordering Surahs by revelation order."""
        url = reverse("quran:surah-list")
        response = api_client.get(url, {"ordering": "revelation_order"})

        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data[0]["revelation_order"] == 5   # Al-Fatiha
        assert data[1]["revelation_order"] == 87  # Al-Baqarah
        assert data[2]["revelation_order"] == 89  # Al-Imran

    def test_list_surahs_ordering_descending(self, api_client, sample_surahs):
        """Test descending order works."""
        url = reverse("quran:surah-list")
        response = api_client.get(url, {"ordering": "-id"})

        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]
        assert data[0]["id"] == 3
        assert data[1]["id"] == 2
        assert data[2]["id"] == 1

    def test_list_surahs_response_format(self, api_client, sample_surahs):
        """Test response follows standard format (AC #10)."""
        url = reverse("quran:surah-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Check pagination structure
        pagination = response.data["pagination"]
        assert "page" in pagination
        assert "page_size" in pagination
        assert "total_pages" in pagination
        assert "total_count" in pagination

        # Check data structure
        surah_data = response.data["data"][0]
        assert "id" in surah_data
        assert "name_arabic" in surah_data
        assert "name_english" in surah_data
        assert "revelation_type" in surah_data
        assert "total_verses" in surah_data

    def test_list_surahs_case_insensitive_filter(self, api_client, sample_surahs):
        """Test revelation type filter is case insensitive."""
        url = reverse("quran:surah-list")

        # Test lowercase
        response = api_client.get(url, {"revelation_type": "meccan"})
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data["data"]) == 1


@pytest.mark.django_db
class TestSurahDetailView:
    """Test cases for Surah detail endpoint (AC #7)."""

    def test_get_surah_detail_success(self, api_client, sample_surahs):
        """Test retrieving a single Surah by ID."""
        url = reverse("quran:surah-detail", kwargs={"pk": 1})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "data" in response.data
        assert response.data["data"]["id"] == 1
        assert response.data["data"]["name_english"] == "The Opening"

    def test_get_surah_detail_full_metadata(self, api_client, sample_surahs):
        """Test Surah detail includes all metadata fields."""
        url = reverse("quran:surah-detail", kwargs={"pk": 1})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]

        # Check all expected fields
        expected_fields = [
            "id", "name_arabic", "name_english", "name_transliteration",
            "revelation_type", "revelation_order", "revelation_note",
            "total_verses", "mushaf_page_start", "juz_start", "is_mixed_revelation"
        ]
        for field in expected_fields:
            assert field in data, f"Missing field: {field}"

    def test_get_surah_detail_not_found(self, api_client, sample_surahs):
        """Test 404 response for invalid Surah ID."""
        url = reverse("quran:surah-detail", kwargs={"pk": 999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.data
        assert response.data["error"]["code"] == "SURAH_NOT_FOUND"
        assert "details" in response.data["error"]


@pytest.mark.django_db
class TestSurahVersesView:
    """Test cases for Surah verses endpoint (AC #8)."""

    def test_get_surah_verses_success(self, api_client, surah_with_verses):
        """Test retrieving all verses for a Surah."""
        surah, verses = surah_with_verses
        url = reverse("quran:surah-verses", kwargs={"surah_id": 1})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "data" in response.data
        assert "verses" in response.data["data"]
        assert len(response.data["data"]["verses"]) == 7

    def test_get_surah_verses_with_range(self, api_client, surah_with_verses):
        """Test retrieving verses with range filtering."""
        surah, verses = surah_with_verses
        url = reverse("quran:surah-verses", kwargs={"surah_id": 1})
        response = api_client.get(url, {"verse_start": 2, "verse_end": 5})

        assert response.status_code == status.HTTP_200_OK
        verse_data = response.data["data"]["verses"]
        assert len(verse_data) == 4
        assert verse_data[0]["verse_number"] == 2
        assert verse_data[-1]["verse_number"] == 5

    def test_get_surah_verses_invalid_range_start_greater_than_end(self, api_client, surah_with_verses):
        """Test error when start > end."""
        surah, verses = surah_with_verses
        url = reverse("quran:surah-verses", kwargs={"surah_id": 1})
        response = api_client.get(url, {"verse_start": 5, "verse_end": 2})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "INVALID_VERSE_RANGE"

    def test_get_surah_verses_invalid_range_exceeds_total(self, api_client, surah_with_verses):
        """Test error when range exceeds total verses."""
        surah, verses = surah_with_verses
        url = reverse("quran:surah-verses", kwargs={"surah_id": 1})
        response = api_client.get(url, {"verse_start": 1, "verse_end": 100})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "INVALID_VERSE_RANGE"

    def test_get_surah_verses_invalid_range_negative_start(self, api_client, surah_with_verses):
        """Test error when start is less than 1."""
        surah, verses = surah_with_verses
        url = reverse("quran:surah-verses", kwargs={"surah_id": 1})
        response = api_client.get(url, {"verse_start": 0, "verse_end": 5})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "INVALID_VERSE_RANGE"

    def test_get_surah_verses_invalid_type(self, api_client, surah_with_verses):
        """Test error when range values are not integers."""
        surah, verses = surah_with_verses
        url = reverse("quran:surah-verses", kwargs={"surah_id": 1})
        response = api_client.get(url, {"verse_start": "abc", "verse_end": "xyz"})

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"]["code"] == "INVALID_VERSE_RANGE"

    def test_get_surah_verses_not_found(self, api_client):
        """Test 404 for invalid Surah ID."""
        url = reverse("quran:surah-verses", kwargs={"surah_id": 999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"]["code"] == "SURAH_NOT_FOUND"

    def test_get_surah_verses_includes_surah_metadata(self, api_client, surah_with_verses):
        """Test response includes Surah metadata along with verses."""
        surah, verses = surah_with_verses
        url = reverse("quran:surah-verses", kwargs={"surah_id": 1})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]

        # Check Surah metadata is included
        assert "id" in data
        assert "name_arabic" in data
        assert "name_english" in data
        assert data["id"] == 1


@pytest.mark.django_db
class TestVerseDetailView:
    """Test cases for verse detail endpoint (AC #9)."""

    def test_get_verse_detail_success(self, api_client, surah_with_verses):
        """Test retrieving a single verse."""
        surah, verses = surah_with_verses
        verse = verses[0]

        url = reverse("quran:verse-detail", kwargs={"pk": verse.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert "data" in response.data
        assert response.data["data"]["verse_number"] == 1

    def test_get_verse_detail_includes_surah_context(self, api_client, surah_with_verses):
        """Test verse detail includes nested Surah information."""
        surah, verses = surah_with_verses
        verse = verses[0]

        url = reverse("quran:verse-detail", kwargs={"pk": verse.id})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        data = response.data["data"]

        # Check verse fields
        assert "verse_number" in data
        assert "text_uthmani" in data
        assert "text_simple" in data
        assert "juz_number" in data
        assert "mushaf_page" in data

        # Check nested Surah
        assert "surah" in data
        assert data["surah"]["id"] == 1
        assert data["surah"]["name_english"] == "The Opening"

    def test_get_verse_detail_not_found(self, api_client):
        """Test 404 for invalid verse ID."""
        url = reverse("quran:verse-detail", kwargs={"pk": 99999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "error" in response.data
        assert response.data["error"]["code"] == "VERSE_NOT_FOUND"


@pytest.mark.django_db
class TestCaching:
    """Test cases for caching behavior (AC #11)."""

    @patch("backend.quran.views.CacheManager")
    def test_surah_list_cache_hit(self, mock_cache_class, api_client, sample_surahs):
        """Test Surah list returns cached data on cache hit."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = {"data": [{"id": 1, "cached": True}], "pagination": {}}
        mock_cache_class.return_value = mock_cache

        url = reverse("quran:surah-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Cache was checked
        assert mock_cache.get.called

    @patch("backend.quran.views.CacheManager")
    def test_surah_list_cache_miss_sets_cache(self, mock_cache_class, api_client, sample_surahs):
        """Test Surah list sets cache on cache miss."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = None  # Cache miss
        mock_cache_class.return_value = mock_cache

        url = reverse("quran:surah-list")
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Cache was set after miss
        assert mock_cache.set.called

    @patch("backend.quran.views.CacheManager")
    def test_surah_detail_cache_hit(self, mock_cache_class, api_client, sample_surahs):
        """Test Surah detail returns cached data."""
        mock_cache = MagicMock()
        mock_cache.get.return_value = {"data": {"id": 1, "cached": True}}
        mock_cache_class.return_value = mock_cache

        url = reverse("quran:surah-detail", kwargs={"pk": 1})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert mock_cache.get.called


@pytest.mark.django_db
class TestErrorResponses:
    """Test cases for error response format (AC #10)."""

    def test_error_response_format(self, api_client):
        """Test error responses follow standard format."""
        url = reverse("quran:surah-detail", kwargs={"pk": 999})
        response = api_client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND

        # Check error format
        error = response.data["error"]
        assert "code" in error
        assert "message" in error
        assert "details" in error

    def test_verse_range_error_includes_details(self, api_client, surah_with_verses):
        """Test verse range error includes helpful details."""
        surah, verses = surah_with_verses
        url = reverse("quran:surah-verses", kwargs={"surah_id": 1})
        response = api_client.get(url, {"verse_start": 5, "verse_end": 2})

        assert response.status_code == status.HTTP_400_BAD_REQUEST

        error = response.data["error"]
        details = error["details"]
        assert "verse_start" in details
        assert "verse_end" in details
        assert "total_verses" in details

"""URL routing for Quran API endpoints.

Defines URL patterns for:
- GET /api/v1/quran/surahs/ - List all Surahs
- GET /api/v1/quran/surahs/{id}/ - Surah detail
- GET /api/v1/quran/surahs/{id}/verses/ - Verses by Surah
- GET /api/v1/quran/verses/{id}/ - Single verse detail
"""

from django.urls import path

from .views import SurahDetailView
from .views import SurahListView
from .views import SurahVersesView
from .views import VerseDetailView

app_name = "quran"

urlpatterns = [
    # Surah endpoints (AC #6-7)
    path("surahs/", SurahListView.as_view(), name="surah-list"),
    path("surahs/<int:pk>/", SurahDetailView.as_view(), name="surah-detail"),
    path("surahs/<int:surah_id>/verses/", SurahVersesView.as_view(), name="surah-verses"),
    # Verse endpoints (AC #9)
    path("verses/<int:pk>/", VerseDetailView.as_view(), name="verse-detail"),
]

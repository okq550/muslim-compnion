# Story 2.1: Retrieve Quran Text by Surah

Status: ready-for-dev

## Story

As a **Quran app user**,
I want to **view the complete text of any Surah in Othmani script**,
so that **I can read the Quran in its authentic Arabic form**.

## Background

This is the foundational story for Epic 2 (Quran Text & Content Management). It establishes the core data models (Surah, Verse) and API endpoints that all other Quran-related features depend upon, including recitations (Epic 3), translations (Epic 4), Tafseer (Epic 5), bookmarks (Epic 6), and offline content (Epic 7).

The Quran text must be authentic Othmani script from verified sources (Tanzil.net Uthmani v1.1), with zero tolerance for textual errors (NFR-037). This story implements the complete data pipeline from XML import to REST API delivery.

**Parent Epic**: EPIC 2 - Quran Text & Content Management
**Priority**: Critical (Phase 1 - MVP Core)
**Functional Requirements**: FR-001 (Complete Quran Text Access), FR-028 (Offline Quran Text Access)
**Dependencies**:
- Epic 1 infrastructure complete (authentication, caching, error handling, logging)
- `docs/Data/quran-uthmani.xml` - Tanzil Uthmani v1.1 verse text
- `docs/Data/quran-data.xml` - Tanzil Project Surah metadata

## Acceptance Criteria

### Data Model and Import (AC #1-5)

1. **Surah Model Implemented with Complete Metadata**
   - Model includes: id (1-114), name_arabic, name_english, name_transliteration
   - Model includes: revelation_type (Meccan/Medinan), revelation_order (1-114), revelation_note
   - Model includes: total_verses, mushaf_page_start, juz_start
   - Index on revelation_order for efficient chronological queries
   - Property `is_mixed_revelation` returns True if revelation_note exists

2. **Verse Model Implemented with Full Text Data**
   - Model includes: surah (FK), verse_number, text_uthmani, text_simple
   - Model includes: juz_number, mushaf_page, hizb_quarter
   - SearchVectorField for PostgreSQL full-text search capability
   - Unique constraint on (surah, verse_number)
   - Indexes on: (surah, verse_number), juz_number, mushaf_page
   - GIN index on search_vector

3. **Quran Text Import Command Works Correctly**
   - Management command `import_quran_text` parses `docs/Data/quran-uthmani.xml`
   - Creates/updates all 6,236 Verse records with Uthmani text
   - Handles idempotent re-runs (updates existing, creates new)
   - Logs progress and errors to console and logging system
   - Transaction-safe (rollback on error)

4. **Surah Metadata Import Command Works Correctly**
   - Management command `import_quran_metadata` parses `docs/Data/quran-data.xml`
   - Creates/updates all 114 Surah records with complete metadata
   - Updates Verse records with Juz/Page/Hizb positional data
   - Imports revelation_order and revelation_note for each Surah
   - Logs progress and errors

5. **Data Verification Passes All Checks**
   - Automated verification confirms exactly 114 Surahs
   - Automated verification confirms exactly 6,236 verses
   - Verse counts per Surah match expected (Al-Fatiha=7, Al-Baqarah=286, etc.)
   - Basmala present in 113 Surahs, absent in Surah 9 (At-Tawbah)
   - All Arabic text renders correctly (diacritics, Tajweed marks preserved)
   - Verification report includes: date, data source version, verse counts

### API Endpoints (AC #6-10)

6. **GET /api/v1/surahs/ Returns Complete Surah List**
   - Returns paginated list of all 114 Surahs
   - Each Surah includes: id, name_arabic, name_english, name_transliteration, revelation_type, revelation_order, total_verses
   - Supports `?ordering=revelation_order` for chronological reading
   - Supports `?revelation_type=Meccan` filtering
   - Response time < 200ms (p95)
   - Uses Redis caching (7-day TTL for static content)
   - Tagged as `["User", "Quran Content"]` per US-API-010 pattern

7. **GET /api/v1/surahs/{id}/ Returns Single Surah Detail**
   - Returns complete Surah metadata including revelation_note
   - Valid IDs: 1-114
   - Returns 404 for invalid Surah ID with clear error message
   - Includes mushaf_page_start and juz_start

8. **GET /api/v1/surahs/{id}/verses/ Returns All Verses in Surah**
   - Returns Surah metadata + list of all verses in the Surah
   - Each verse includes: id, verse_number, text_uthmani, text_simple, juz_number, mushaf_page
   - Supports optional `?verse_start=1&verse_end=7` for verse range
   - Validates verse range (start ≤ end, both within Surah bounds)
   - Returns 400 for invalid verse range with clear error message
   - Response time < 200ms for full Surah (p95)

9. **GET /api/v1/verses/{id}/ Returns Single Verse Detail**
   - Returns verse with full Surah context
   - Includes: surah (nested object with id, names, revelation_order), verse_number, text_uthmani, text_simple, juz_number, mushaf_page
   - Returns 404 for invalid verse ID

10. **API Responses Follow Standard Format**
    - Success responses wrapped in `{"data": ...}`
    - Pagination format: `{"data": [...], "pagination": {"page": 1, "page_size": 20, "total_pages": N, "total_count": N}}`
    - Error responses: `{"error": {"code": "...", "message": "...", "details": {...}, "timestamp": "..."}}`
    - All Arabic text properly encoded (UTF-8)

### Performance and Caching (AC #11-12)

11. **Caching Strategy Implemented**
    - Surah list cached in Redis with 7-day TTL (static content)
    - Individual Surah detail cached with 7-day TTL
    - Verse lists per Surah cached with 7-day TTL
    - Cache invalidation triggered on data re-import
    - Cache hit rate tracked in metrics

12. **Performance Targets Met**
    - Surah list: < 200ms (p95)
    - Surah detail: < 200ms (p95)
    - Verses by Surah: < 200ms (p95)
    - Cached responses: < 100ms (p95)

## Tasks / Subtasks

### Task 1: Create Quran Django App Structure (AC #1-2)

- [ ] Create `apps/quran/` Django app with standard structure
  - [ ] `__init__.py`, `apps.py`, `admin.py`
  - [ ] `models.py` - Surah, Verse models
  - [ ] `serializers.py` - DRF serializers
  - [ ] `views.py` - API views
  - [ ] `urls.py` - URL routing
  - [ ] `tests/` directory with `__init__.py`, `factories.py`
  - [ ] `management/commands/` directory
- [ ] Register app in `INSTALLED_APPS` in `config/settings/base.py`
- [ ] Add URL routing in `config/urls.py`: `path('api/v1/', include('apps.quran.urls'))`

### Task 2: Implement Surah Model (AC #1)

- [ ] Create Surah model in `apps/quran/models.py`:
  - [ ] `id = IntegerField(primary_key=True)` - 1-114 Mushaf order
  - [ ] `name_arabic = TextField()` - Arabic name
  - [ ] `name_english = CharField(max_length=100)` - English name
  - [ ] `name_transliteration = CharField(max_length=100)` - Transliteration
  - [ ] `revelation_type = CharField(choices=['Meccan', 'Medinan'])`
  - [ ] `revelation_order = IntegerField()` - Chronological 1-114
  - [ ] `revelation_note = TextField(blank=True)` - Mixed revelation notes
  - [ ] `total_verses = IntegerField()`
  - [ ] `mushaf_page_start = IntegerField()`
  - [ ] `juz_start = IntegerField()`
- [ ] Add index on `revelation_order`
- [ ] Add `is_mixed_revelation` property
- [ ] Create and run migration
- [ ] Register in Django admin with Arabic RTL support

### Task 3: Implement Verse Model (AC #2)

- [ ] Create Verse model in `apps/quran/models.py`:
  - [ ] `id = AutoField(primary_key=True)`
  - [ ] `surah = ForeignKey(Surah, on_delete=CASCADE, related_name='verses')`
  - [ ] `verse_number = IntegerField()` - 1-286
  - [ ] `text_uthmani = TextField()` - Full Othmani with diacritics
  - [ ] `text_simple = TextField()` - Simplified Arabic
  - [ ] `juz_number = IntegerField()` - 1-30
  - [ ] `mushaf_page = IntegerField()` - 1-604
  - [ ] `hizb_quarter = IntegerField()` - 1-240
  - [ ] `search_vector = SearchVectorField(null=True)`
- [ ] Add unique constraint on `(surah, verse_number)`
- [ ] Add indexes: `(surah, verse_number)`, `juz_number`, `mushaf_page`
- [ ] Add GIN index on `search_vector`
- [ ] Create and run migration
- [ ] Register in Django admin

### Task 4: Create Import Management Commands (AC #3-4)

- [ ] Create `apps/quran/management/commands/import_quran_text.py`:
  - [ ] Parse `docs/Data/quran-uthmani.xml` using ElementTree
  - [ ] Extract Uthmani text for all verses
  - [ ] Use `update_or_create` for idempotent imports
  - [ ] Wrap in transaction for rollback on error
  - [ ] Log progress every 1000 verses
  - [ ] Report final statistics (total imported, created, updated)
- [ ] Create `apps/quran/management/commands/import_quran_metadata.py`:
  - [ ] Parse `docs/Data/quran-data.xml`
  - [ ] Create/update Surah records with all metadata fields
  - [ ] Update Verse records with Juz/Page/Hizb data
  - [ ] Log progress and errors

### Task 5: Create Data Verification Command (AC #5)

- [ ] Create `apps/quran/management/commands/verify_quran_data.py`:
  - [ ] Verify exactly 114 Surahs exist
  - [ ] Verify exactly 6,236 verses exist
  - [ ] Verify verse counts per Surah match expected
  - [ ] Verify Basmala present/absent correctly (absent in Surah 9)
  - [ ] Generate verification report with timestamp and results
  - [ ] Exit with error code if any check fails

### Task 6: Implement Serializers (AC #6-10)

- [ ] Create `apps/quran/serializers.py`:
  - [ ] `SurahListSerializer` - List view with essential fields
  - [ ] `SurahDetailSerializer` - Detail view with all fields
  - [ ] `VerseSerializer` - Verse with all fields
  - [ ] `VerseWithSurahSerializer` - Verse with nested Surah context
  - [ ] `SurahVersesSerializer` - Surah metadata + list of verses

### Task 7: Implement API Views (AC #6-10)

- [ ] Create `apps/quran/views.py`:
  - [ ] `SurahViewSet` with list and retrieve actions
    - [ ] List: paginated, filterable, sortable
    - [ ] Retrieve: single Surah by ID
    - [ ] Add `@extend_schema` with `tags=["User", "Quran Content"]`
  - [ ] `SurahVersesView` for GET /surahs/{id}/verses/
    - [ ] Support optional verse range query params
    - [ ] Validate range parameters
    - [ ] Return 400 for invalid range
  - [ ] `VerseViewSet` with retrieve action
    - [ ] Return verse with Surah context
- [ ] Configure URL routing in `apps/quran/urls.py`

### Task 8: Implement Caching Layer (AC #11-12)

- [ ] Add Redis caching to Surah list endpoint:
  - [ ] Cache key: `quran:surahs:list`
  - [ ] TTL: 7 days
  - [ ] Invalidate on import
- [ ] Add caching to Surah detail endpoint:
  - [ ] Cache key: `quran:surah:{id}`
  - [ ] TTL: 7 days
- [ ] Add caching to verses by Surah endpoint:
  - [ ] Cache key: `quran:surah:{id}:verses`
  - [ ] TTL: 7 days
- [ ] Create cache invalidation function called by import commands
- [ ] Log cache hits/misses for monitoring

### Task 9: Write Unit and Integration Tests (AC #1-12)

- [ ] Create `apps/quran/tests/factories.py`:
  - [ ] `SurahFactory` with realistic test data
  - [ ] `VerseFactory` with Arabic text samples
- [ ] Create `apps/quran/tests/test_models.py`:
  - [ ] Test Surah model properties and constraints
  - [ ] Test Verse model constraints and indexes
  - [ ] Test `is_mixed_revelation` property
- [ ] Create `apps/quran/tests/test_views.py`:
  - [ ] Test Surah list endpoint (pagination, filtering, sorting)
  - [ ] Test Surah detail endpoint (valid/invalid IDs)
  - [ ] Test verses by Surah endpoint (full, range, invalid range)
  - [ ] Test single verse endpoint
  - [ ] Test error responses format
  - [ ] Test caching behavior
- [ ] Create `apps/quran/tests/test_commands.py`:
  - [ ] Test import command with sample XML
  - [ ] Test verification command
- [ ] Achieve >80% code coverage for `apps/quran/`

### Task 10: Run Data Import and Verification (AC #3-5)

- [ ] Run `python manage.py import_quran_text`
- [ ] Run `python manage.py import_quran_metadata`
- [ ] Run `python manage.py verify_quran_data`
- [ ] Verify all checks pass
- [ ] Document import process in README or dev notes

## Out of Scope

- Audio recitation (Epic 3)
- Translations (Epic 4)
- Tafseer/interpretation (Epic 5)
- Bookmarking and reading history (Epic 6)
- Offline content downloads (Epic 7)
- Elasticsearch search integration (US-QT-005)
- Juz navigation endpoints (US-QT-004)
- Page navigation endpoints (US-QT-003)
- Islamic scholar review sign-off (separate process)
- Tajweed color-coding display logic (client-side)

## Definition of Done

- [ ] All acceptance criteria tested and passing
- [ ] Surah and Verse models created with proper indexes
- [ ] Import commands successfully load all 114 Surahs and 6,236 verses
- [ ] Verification command passes all data integrity checks
- [ ] API endpoints return correct data in standard format
- [ ] Caching implemented with 7-day TTL for static content
- [ ] Response times < 200ms (p95) for all endpoints
- [ ] Unit and integration tests achieve >80% coverage
- [ ] API documented in OpenAPI schema (drf-spectacular)
- [ ] Endpoints tagged as `["User", "Quran Content"]`
- [ ] Code reviewed and approved
- [ ] Merged to main branch

## Dev Notes

### Architecture Alignment

**Source**: `docs/architecture.md` - Data Architecture section (Epic 2: Quran Text)

This story implements the core data models defined in the architecture document. The Surah and Verse models serve as the foundation for all Quran-related features across Epics 3-7.

### Technical Context

**From Epic 1 Infrastructure** (US-API-001 through US-API-010):
- JWT authentication configured (use for protected endpoints if needed)
- Redis caching infrastructure ready (`django-redis`)
- Error handling middleware configured
- Logging and monitoring (Sentry) configured
- API documentation (drf-spectacular) configured
- API tagging pattern established: `["User", "Quran Content"]`

**Tagging Pattern** (from US-API-010):
```python
@extend_schema(
    tags=["User", "Quran Content"],
    summary="List all Surahs",
    ...
)
class SurahViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [IsAuthenticated]  # Or AllowAny for public access
```

### Data Source Details

**Quran Text** (`docs/Data/quran-uthmani.xml`):
- Tanzil Uthmani v1.1
- XML format with verse elements
- Includes full Othmani script with diacritics

**Quran Metadata** (`docs/Data/quran-data.xml`):
- Tanzil Project comprehensive metadata
- Includes Surah names (Arabic, English, transliteration)
- Includes revelation type, order, verse counts
- Includes Juz/Hizb/Page boundary data

### Caching Strategy

**Static Content (7-day TTL)**:
- Quran text never changes
- Aggressive caching is appropriate
- Invalidate only on data re-import

**Cache Keys**:
```python
CACHE_KEYS = {
    'surah_list': 'quran:surahs:list',
    'surah_detail': 'quran:surah:{id}',
    'surah_verses': 'quran:surah:{id}:verses',
}
```

### Project Structure Notes

**File Locations**:
- Models: `muslim_companion/apps/quran/models.py`
- Views: `muslim_companion/apps/quran/views.py`
- Serializers: `muslim_companion/apps/quran/serializers.py`
- URLs: `muslim_companion/apps/quran/urls.py`
- Tests: `muslim_companion/apps/quran/tests/`
- Commands: `muslim_companion/apps/quran/management/commands/`

### Learnings from Previous Story

**From Story US-API-010 (Status: done)**

- **API Tagging Pattern**: All Epic 2 endpoints should use `tags=["User", "Quran Content"]` format
- **SPECTACULAR_SETTINGS**: Tags already configured in `config/settings/base.py` with "Quran Content" domain
- **Permission Classes**: Use `IsAuthenticated` for user endpoints, or consider `AllowAny` if Quran text should be public
- **OpenAPI Schema**: Run `python manage.py spectacular --validate` to verify schema
- **Test Suite Status**: 262/285 tests passing (91.9%) - some pre-existing failures unrelated to this story

**Files to Reference**:
- `muslim_companion/config/settings/base.py` - SPECTACULAR_SETTINGS with tag definitions
- `muslim_companion/backend/core/views/health.py` - Tagging pattern documentation example
- `muslim_companion/backend/analytics/api/views.py` - User vs Admin endpoint patterns

[Source: docs/stories/us-api-010-implement-domain-driven-api-tagging-with-access-level-indicators.md#Dev-Agent-Record]

### References

- [Source: docs/architecture.md#Data-Architecture - Surah and Verse models]
- [Source: docs/tech-spec-epic-2.md#Data-Models-and-Contracts]
- [Source: docs/PRD.md#FR-001 - Complete Quran Text Access]
- [Source: docs/epics.md#US-QT-001 - Acceptance criteria and business rules]

## Change Log

- 2025-11-18: Initial story created by Scrum Master (Bob)
- Status: backlog → drafted

## Dev Agent Record

### Context Reference

- docs/stories/us-qt-001-retrieve-quran-text-by-surah.context.xml

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

# Epic Technical Specification: Quran Text & Content Management

Date: 2025-11-18
Author: Osama
Epic ID: epic-2
Status: Draft

---

## Overview

Epic 2 delivers the core Quran text retrieval and management capabilities for the Muslim Companion API. This epic implements the foundational content layer that all other epics depend upon - providing access to the complete Quran text in authentic Othmani script across multiple navigation modes (Surah, Verse, Page, Juz) with full-text Arabic search capabilities.

This epic is critical to the project's mission of delivering authentic, accessible Quran experiences with zero tolerance for textual errors. The Quran text data serves as the reference point for all related features including recitations (Epic 3), translations (Epic 4), Tafseer (Epic 5), bookmarks (Epic 6), and offline content (Epic 7).

## Objectives and Scope

**In Scope:**
- Populate and manage complete Quran text database (114 Surahs, 6,236 verses) in Othmani script
- Implement Surah model with comprehensive metadata (names, revelation type/order, verse counts)
- Create Verse model with full text (Uthmani and simplified), positional data (Juz, page, Hizb)
- Build Page model for Mushaf-style navigation (604 pages)
- Implement Juz model for traditional 30-part division
- Develop REST API endpoints for all navigation modes
- Implement Elasticsearch-based Arabic full-text search
- Create data import management commands for Tanzil.net sources
- Support both chronological (revelation order) and Mushaf order navigation
- Implement automated verification scripts for data integrity (NFR-037)

**Out of Scope:**
- Audio recitation (Epic 3)
- Translations alongside Arabic text (Epic 4)
- Tafseer/interpretation (Epic 5)
- Bookmarking and reading history (Epic 6)
- Offline content downloads (Epic 7)
- Root word analysis or advanced morphological search (Phase 2)
- Tajweed color-coding display logic (client-side concern)
- Visual Mushaf page layout replication (client-side concern)

## System Architecture Alignment

This epic implements the `apps/quran/` Django application as defined in the Architecture Document:

**Database Design (PostgreSQL 16):**
- Surah, Verse, Juz, Page models with proper indexing strategy
- GIN index on `search_vector` field for full-text search
- Composite indexes for common query patterns (surah+verse_number, juz_number, mushaf_page)

**Search Engine (AWS OpenSearch/Elasticsearch):**
- Arabic text search with fuzzy matching and relevance scoring
- Handles diacritical mark variations appropriately
- Minimum query length enforcement to prevent overly broad results

**Caching Strategy (Redis):**
- Quran text cached aggressively (static content, 7-day TTL)
- Surah list and metadata cached at application startup
- Per-verse cache for frequently accessed content

**Data Sources:**
- `docs/Data/quran-uthmani.xml` - Tanzil Uthmani v1.1 (verse text)
- `docs/Data/quran-data.xml` - Tanzil Project metadata (Surah info, Juz/Hizb/Page boundaries, revelation order)

**Technology Stack:**
- Django 5.2.8 LTS + DRF 3.16.1+
- PostgreSQL 16 with SearchVectorField
- Elasticsearch (AWS OpenSearch) for advanced search
- Redis for caching
- Celery for background indexing tasks

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner |
|----------------|----------------|--------|---------|-------|
| **Surah Service** | Retrieve Surah list and detail with metadata | Surah ID, filters (revelation_type, revelation_order) | Surah objects with metadata | US-QT-001 |
| **Verse Service** | Retrieve verses by various criteria | Surah ID, verse range, page, Juz | Verse objects with text | US-QT-001, US-QT-002 |
| **Page Service** | Navigate Quran by Mushaf page | Page number (1-604) | Verses on page with metadata | US-QT-003 |
| **Juz Service** | Retrieve Juz content and boundaries | Juz number (1-30) | All verses in Juz with Surah transitions | US-QT-004 |
| **Search Service** | Full-text Arabic search | Query string, pagination | Matching verses with highlights | US-QT-005 |
| **Import Service** | Load Quran data from Tanzil sources | XML files | Populated database tables | US-QT-001 |
| **Elasticsearch Indexer** | Index verses for search | Verse objects | Elasticsearch documents | US-QT-005 |
| **Verification Service** | Validate data integrity | Database content | Verification reports | US-QT-001 |

### Data Models and Contracts

**Surah Model:**
```python
class Surah(BaseModel):
    """Surah (Chapter) of the Quran - 114 total"""
    id = models.IntegerField(primary_key=True)  # 1-114 (Mushaf order)
    name_arabic = models.TextField()  # الفاتحة
    name_english = models.CharField(max_length=100)  # Al-Fatiha
    name_transliteration = models.CharField(max_length=100)  # Al-Faatiha
    revelation_type = models.CharField(max_length=10, choices=[
        ('Meccan', 'Meccan'),
        ('Medinan', 'Medinan'),
    ])
    revelation_order = models.IntegerField()  # Chronological order 1-114
    revelation_note = models.TextField(blank=True)  # Notes for mixed revelation
    total_verses = models.IntegerField()
    mushaf_page_start = models.IntegerField()
    juz_start = models.IntegerField()

    class Meta:
        db_table = 'quran_surah'
        indexes = [
            models.Index(fields=['revelation_order']),
        ]

    @property
    def is_mixed_revelation(self):
        """Returns True if Surah has verses from both periods"""
        return bool(self.revelation_note)
```

**Verse Model:**
```python
class Verse(BaseModel):
    """Individual verse (Ayah) - 6,236 total"""
    id = models.AutoField(primary_key=True)
    surah = models.ForeignKey(Surah, on_delete=models.CASCADE, related_name='verses')
    verse_number = models.IntegerField()  # 1-286
    text_uthmani = models.TextField()  # Full Othmani script with diacritics
    text_simple = models.TextField()  # Simplified Arabic (no diacritics)
    juz_number = models.IntegerField()  # 1-30
    mushaf_page = models.IntegerField()  # 1-604
    hizb_quarter = models.IntegerField()  # 1-240
    search_vector = SearchVectorField(null=True)  # PostgreSQL full-text search

    class Meta:
        db_table = 'quran_verse'
        unique_together = ('surah', 'verse_number')
        indexes = [
            models.Index(fields=['surah', 'verse_number']),
            models.Index(fields=['juz_number']),
            models.Index(fields=['mushaf_page']),
            GinIndex(fields=['search_vector']),
        ]
```

**Juz Model:**
```python
class Juz(BaseModel):
    """Juz (Part) of the Quran - 30 total"""
    id = models.IntegerField(primary_key=True)  # 1-30
    name_arabic = models.CharField(max_length=100)
    first_verse = models.ForeignKey(Verse, on_delete=models.PROTECT, related_name='juz_start_set')
    last_verse = models.ForeignKey(Verse, on_delete=models.PROTECT, related_name='juz_end_set')

    class Meta:
        db_table = 'quran_juz'
```

**Page Model:**
```python
class Page(BaseModel):
    """Mushaf page - 604 total"""
    id = models.IntegerField(primary_key=True)  # 1-604
    first_verse = models.ForeignKey(Verse, on_delete=models.PROTECT, related_name='page_start_set')
    last_verse = models.ForeignKey(Verse, on_delete=models.PROTECT, related_name='page_end_set')
    surah = models.ForeignKey(Surah, on_delete=models.PROTECT)  # Primary Surah on this page

    class Meta:
        db_table = 'quran_page'
```

### APIs and Interfaces

**GET /api/v1/surahs/**
- Description: List all Surahs with metadata
- Query params: `?ordering=revelation_order`, `?revelation_type=Meccan`
- Response: Paginated list of Surah objects
- Status codes: 200 OK

**GET /api/v1/surahs/{id}/**
- Description: Retrieve single Surah detail
- Response: Surah object with full metadata
- Status codes: 200 OK, 404 Not Found

**GET /api/v1/surahs/{id}/verses/**
- Description: Get all verses in a Surah
- Query params: `?verse_start=1&verse_end=7` (optional range)
- Response: Surah metadata + list of verse objects
- Status codes: 200 OK, 400 Bad Request (invalid range), 404 Not Found

**GET /api/v1/verses/{id}/**
- Description: Retrieve single verse detail
- Response: Verse object with Surah context
- Status codes: 200 OK, 404 Not Found

**GET /api/v1/pages/{id}/**
- Description: Get verses for a Mushaf page
- Response: Page metadata + list of verse objects + Surah transitions
- Status codes: 200 OK, 404 Not Found (invalid page 0 or >604)

**GET /api/v1/pages/{id}/next/** and **GET /api/v1/pages/{id}/previous/**
- Description: Navigate to adjacent pages
- Response: Redirect or next/previous page content
- Status codes: 200 OK, 404 Not Found

**GET /api/v1/juz/{id}/**
- Description: Get all verses in a Juz
- Response: Juz metadata + list of verse objects with Surah transitions marked
- Status codes: 200 OK, 404 Not Found (invalid Juz 0 or >30)

**GET /api/v1/search/**
- Description: Full-text Arabic search
- Query params: `?q={query}` (required, min 2 chars), `?page=1&page_size=20`
- Response: Search results with verse references and highlighted matches
- Status codes: 200 OK, 400 Bad Request (query too short)

### Workflows and Sequencing

**Data Import Workflow:**
```
1. Run import_quran_text command
   → Parse quran-uthmani.xml
   → Create/update Verse records with Uthmani text

2. Run import_quran_metadata command
   → Parse quran-data.xml
   → Create/update Surah records with all metadata
   → Update Verse records with Juz/Page/Hizb data
   → Create Juz and Page records with boundary references

3. Run index_quran_elasticsearch command
   → Iterate all Verse records
   → Index to Elasticsearch with Arabic analyzer
   → Update search_vector field in PostgreSQL
```

**Verse Retrieval Flow:**
```
Client Request → DRF ViewSet → Cache Check (Redis)
  → Cache Hit: Return cached data
  → Cache Miss: Query PostgreSQL → Serialize → Cache → Return
```

**Search Flow:**
```
Client Request → Search View → Elasticsearch Query
  → Results with scores → Fetch full verses from PostgreSQL
  → Highlight matched text → Paginate → Return
```

## Non-Functional Requirements

### Performance

- **FR-NFR-001**: Quran text retrieval < 200ms (p95)
  - Achieved via: PostgreSQL indexes, Redis caching, optimized serializers
- **FR-NFR-002**: Search response < 500ms (p95)
  - Achieved via: Elasticsearch with proper analyzers, pagination limits
- **FR-NFR-004**: Cached verse access < 100ms
  - Achieved via: Redis in-memory cache with 7-day TTL for static content

**Cache TTLs:**
- Surah list: 7 days (static)
- Individual verses: 7 days (static)
- Search results: 1 hour (semi-dynamic based on index updates)

### Security

- All endpoints require authentication (JWT) for user-specific features
- Public read access for Quran text endpoints (anonymous users allowed)
- Rate limiting: 1000 requests/minute for authenticated users, 100/minute for anonymous
- No SQL injection risk via Django ORM parameterized queries
- Search queries sanitized to prevent Elasticsearch injection

### Reliability/Availability

- **FR-NFR-011**: 99.9% uptime SLA
- Database replication via AWS RDS Multi-AZ
- Redis cluster with automatic failover
- Elasticsearch cluster with replicas
- Graceful degradation: If Elasticsearch unavailable, return error (don't attempt PostgreSQL fallback for search)

### Observability

**Logging:**
- All API requests logged with correlation ID
- Import commands log progress and errors
- Search queries logged (anonymized) for analytics

**Metrics:**
- Cache hit/miss ratios per endpoint
- Search query latency distribution
- Most accessed Surahs and verses
- Import job duration and success rates

**Alerts:**
- Error rate > 1% on any endpoint
- Search latency > 1s (p95)
- Cache hit rate < 80%
- Import job failures

## Dependencies and Integrations

**Python Dependencies:**
```
# Already in requirements
Django==5.2.8
djangorestframework==3.16.1
psycopg2-binary==2.9.9
django-redis==5.4.0
elasticsearch-dsl==8.11.0
```

**External Data Sources:**
- Tanzil.net Uthmani text (quran-uthmani.xml) - v1.1
- Tanzil.net metadata (quran-data.xml) - comprehensive Surah/verse metadata

**Internal Dependencies:**
- Epic 1 infrastructure (authentication, caching, error handling, logging)
- Redis cache service (configured in Epic 1)
- PostgreSQL database (configured in Epic 1)

**Downstream Dependents:**
- Epic 3 (Reciters): Audio.verse ForeignKey
- Epic 4 (Translations): Translation.verse ForeignKey
- Epic 5 (Tafseer): Tafseer.verse ForeignKey
- Epic 6 (Bookmarks): Bookmark.verse ForeignKey
- Epic 7 (Offline): DownloadManifest references verses

## Acceptance Criteria (Authoritative)

**US-QT-001: Retrieve Quran Text by Surah**
1. User can select any Surah from 1 to 114
2. Complete Surah text displays in Othmani script
3. Each verse is numbered correctly
4. Basmala appears at beginning of applicable Surahs (not Surah 9)
5. Text is right-aligned and renders properly in Arabic
6. All diacritical marks and Arabic characters display correctly
7. Surah metadata displays (name Arabic/English, revelation type, verse count, revelation order)
8. Text loads < 200ms (p95)
9. Tajweed marks are preserved in text_uthmani field
10. Automated verification confirms exactly 114 Surahs and 6,236 verses
11. Surah API supports filtering by revelation_order
12. Surah API supports sorting by revelation_order for chronological reading

**US-QT-002: Retrieve Quran Text by Verse Range**
1. Single verse retrieval by Surah:Ayah reference works
2. Continuous verse range retrieval within Surah works
3. Verse numbers display correctly
4. Surah context information provided in response
5. Invalid verse numbers rejected with clear error message
6. Text renders properly in Othmani script
7. Arabic text is right-aligned
8. Range validation: start verse must be ≤ end verse

**US-QT-003: Retrieve Quran Text by Page**
1. All 604 Mushaf pages accessible by page number
2. Page content matches standard Madani Mushaf layout
3. Page metadata includes Surah names, Juz number, verse references
4. Page breaks match traditional Mushaf format
5. Navigation between pages (next/previous) supported
6. Invalid page numbers show appropriate error message
7. Text renders properly in Othmani script

**US-QT-004: Retrieve Quran Text by Juz**
1. All 30 Juz accessible by Juz number
2. Juz boundaries match standard Quran divisions
3. Complete text for each Juz provided
4. Surah transitions within Juz clearly indicated
5. Starting and ending verse references provided
6. Verse numbers display correctly throughout
7. Text renders properly in Arabic
8. Navigation between Juz (next/previous) supported

**US-QT-005: Search Quran Text**
1. Arabic text search with partial word matching works
2. Phrase search supported
3. Diacritical mark variations handled appropriately
4. Search results include Surah name, verse number, matched text
5. Matched text highlighted in results
6. Minimum 2-character search term enforced
7. Empty search shows appropriate message
8. No results shows "No verses found" message
9. Search results load < 500ms (p95)

## Traceability Mapping

| AC # | Spec Section | Component(s)/API(s) | Test Idea |
|------|--------------|---------------------|-----------|
| QT-001-1 | Data Models - Surah | GET /api/v1/surahs/ | Test Surah count equals 114, IDs 1-114 |
| QT-001-2 | Data Models - Verse | GET /api/v1/surahs/{id}/verses/ | Verify text_uthmani contains diacritics |
| QT-001-3 | APIs - Verse endpoint | GET /api/v1/surahs/{id}/verses/ | Check verse_number sequential within Surah |
| QT-001-4 | Data Models - Verse | Import service | Verify Basmala present except Surah 9 |
| QT-001-7 | APIs - Surah endpoint | SurahSerializer | Verify all metadata fields populated |
| QT-001-8 | Performance NFR | All endpoints | Load test with k6, measure p95 |
| QT-001-10 | Verification Service | Management command | Run verify_quran_data command |
| QT-001-11 | APIs - Surah endpoint | GET /api/v1/surahs/?ordering=revelation_order | Test filter returns correct order |
| QT-002-5 | Error Handling | VerseViewSet | Test invalid verse_number returns 400 |
| QT-003-1 | Data Models - Page | GET /api/v1/pages/ | Verify 604 pages exist |
| QT-003-4 | Import Service | import_quran_metadata | Cross-reference with physical Mushaf |
| QT-004-1 | Data Models - Juz | GET /api/v1/juz/ | Verify 30 Juz exist |
| QT-005-1 | Search Service | GET /api/v1/search/?q={} | Test Arabic partial matches |
| QT-005-3 | Elasticsearch config | Arabic analyzer | Test query with/without diacritics returns same results |

## Risks, Assumptions, Open Questions

**Risks:**
- **R1: Text authenticity errors** - CRITICAL. Mitigation: Automated verification + Islamic scholar sign-off before production deployment. Import process must validate against known verse counts.
- **R2: Arabic search complexity** - Diacritical variations may cause missed results. Mitigation: Configure Elasticsearch Arabic analyzer with diacritic normalization. Test with common search patterns.
- **R3: Elasticsearch availability** - Single point of failure for search. Mitigation: Implement health check, graceful error response. Consider PostgreSQL fallback for Phase 2.

**Assumptions:**
- A1: Tanzil.net data sources (quran-uthmani.xml, quran-data.xml) are authoritative and accurate
- A2: Madani Mushaf pagination (604 pages) is the standard to follow
- A3: Users primarily search for exact words/phrases, not semantic concepts (Phase 1)
- A4: Islamic scholar review can be completed within 48-72 hours of data import

**Open Questions:**
- Q1: **RESOLVED** - Scholar review process: Who will perform the verification? How will credentials be documented?
- Q2: Should search support transliteration (Latin characters)? **Assumption: Not in Phase 1**
- Q3: Should we store Tajweed rule metadata per character for color-coding? **Assumption: Text includes marks, display is client-side**

## Test Strategy Summary

**Test Levels:**
1. **Unit Tests** - Model methods, serializer validation, utility functions
2. **Integration Tests** - API endpoint behavior, database queries, cache interactions
3. **Data Integrity Tests** - Verse counts, Surah counts, reference integrity
4. **Performance Tests** - Response time benchmarks, load testing

**Testing Framework:**
- pytest + pytest-django
- Factory Boy for test data factories
- Elasticsearch test containers for search tests

**Coverage Requirements:**
- Minimum 80% code coverage for `apps/quran/`
- 100% coverage for verification/validation logic

**Critical Test Cases:**
1. All 114 Surahs retrievable with correct metadata
2. All 6,236 verses retrievable with correct text
3. Verse counts per Surah match expected (e.g., Al-Baqarah = 286)
4. Page boundaries match Madani Mushaf standard
5. Juz boundaries match traditional divisions
6. Search finds verses with and without diacritics
7. Cache hit/miss behavior verified
8. Error responses for invalid Surah/verse/page/Juz numbers
9. Basmala handling (present in 113 Surahs, absent in Surah 9)
10. Revelation order filtering and sorting

**Test Data:**
- Full Quran dataset from Tanzil sources
- Known verse references for spot-checking (e.g., Ayat al-Kursi = 2:255)
- Edge cases: shortest Surah (Al-Kawthar, 3 verses), longest Surah (Al-Baqarah, 286 verses)
- Search test queries: common words, rare words, words with diacritics

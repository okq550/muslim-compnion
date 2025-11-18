# Architecture Document
## Muslim Companion API - Islamic Spiritual Companion App

**Version:** 1.6
**Date:** 2025-11-10 (Updated)
**Project:** muslim_companion
**Author:** Architecture Team

---

## Executive Summary

The Muslim Companion is a Django REST Framework API platform designed to deliver authentic Quran content (text, audio, translations, and Tafseer) to mobile applications serving the global Muslim community. The architecture leverages Cookiecutter Django as the foundation, combined with AWS infrastructure (S3, CloudFront, OpenSearch), to provide a scalable, high-performance, offline-first API with zero tolerance for content errors.

This architecture supports 7 core epics: Infrastructure, Quran Text Management, Recitation Management, Translation Management, Tafseer Management, Bookmark Management, and Offline Content Management. The system is designed for consistency across AI agent implementations through explicit architectural decisions and implementation patterns.

---

## Project Initialization

**First implementation story must execute:**

```bash
cookiecutter https://github.com/cookiecutter/cookiecutter-django
```

**Cookiecutter Django prompts - Select these options:**
- `project_name`: muslim_companion
- `project_slug`: django_muslim_companion
- `description`: Muslim Companion API for Islamic Spiritual Companion App
- `author_name`: Your Team Name
- `domain_name`: api.yourapp.com
- `email`: team@yourapp.com
- `version`: 0.1.0
- `timezone`: UTC
- `use_whitenoise`: n (using S3)
- `use_celery`: y
- `use_drf`: y
- `use_docker`: y
- `postgresql_version`: 16
- `cloud_provider`: AWS
- `use_compressor`: n
- `use_mailpit`: y
- `use_sentry`: y
- `use_pycharm`: n
- `keep_local_envs_in_vcs`: n
- `debug`: n

**Post-initialization customization:**
1. Replace `config/settings/` (base.py, local.py, production.py) with single `config/settings.py`
2. Install `django-environ` for .env management
3. **Configure Arabic i18n (internationalization):**
   ```python
   LANGUAGE_CODE = 'ar'  # Arabic as default language
   LANGUAGES = [
       ('ar', 'العربية'),
       ('en', 'English'),
   ]
   USE_I18N = True
   USE_L10N = True
   LOCALE_PATHS = [str(BASE_DIR / 'locale')]

   MIDDLEWARE = [
       ...
       'django.middleware.locale.LocaleMiddleware',  # Add for language switching
       ...
   ]
   ```
4. Add Django apps per epic structure (see Project Structure section)
5. Configure AWS S3, CloudFront, and OpenSearch integrations
6. Generate Arabic translation files: `django-admin makemessages -l ar`
7. Configure Django admin for Arabic RTL layout (automatic with LANGUAGE_CODE='ar')

This establishes the base architecture with these decisions:
- Django 5.2.8 LTS + Python 3.14
- Django REST Framework 3.16.1+
- PostgreSQL 16 for relational data
- Redis for caching and Celery broker
- Docker + Docker Compose for containerization
- Celery + Celery Beat for background jobs
- pytest for testing framework
- Pre-commit hooks for code quality
- **Arabic as default language with bilingual support (Arabic/English)**
- **Django admin panel in Arabic with RTL layout**

---

## Decision Summary

| Category | Decision | Version | Affects Epics | Rationale |
| -------- | -------- | ------- | ------------- | --------- |
| **Backend Framework** | Django | 5.2.8 LTS | All | Long-term support until 2028, production-ready, extensive ecosystem |
| **API Framework** | Django REST Framework | 3.16.1+ | All | Industry standard for Django APIs, excellent serialization, browsable API |
| **Database** | PostgreSQL | 16 | All | ACID compliance, robust indexing, full-text search capabilities |
| **Cache Layer** | Redis | Latest | All | High-performance in-memory cache, Celery broker support |
| **Search Engine** | Elasticsearch (AWS OpenSearch) | Latest | Epic 2 | Superior Arabic text search, fuzzy matching, relevance scoring |
| **Object Storage** | AWS S3 | N/A | Epic 3, 7 | Scalable audio storage, 99.999999999% durability |
| **CDN** | AWS CloudFront | N/A | Epic 3, 7 | Global edge caching, <2s audio startup time worldwide |
| **Audio Format** | MP3 | N/A | Epic 3, 7 | Universal compatibility across mobile platforms |
| **Background Jobs** | Celery + Redis | Latest | All | Async task processing, scheduled jobs, import pipelines |
| **Authentication** | JWT (simplejwt) | Latest | All | Stateless auth, mobile-friendly, industry standard for REST APIs |
| **JWT Token Naming** | OAuth 2.0 Standard (`access_token`/`refresh_token`) | N/A | Epic 1 | Standards compliance (RFC 6749), explicit naming, developer experience (See ADR-012) |
| **Environment Config** | django-environ | 0.11.2 | All | Secure .env file management, 12-factor app principles |
| **Error Tracking** | Sentry | Latest | All | Real-time error monitoring, performance tracking, critical for zero-error tolerance |
| **Internationalization** | Django i18n | Built-in | All | Arabic as default, bilingual support (Arabic/English), RTL layout |
| **Admin Dashboard** | Django Admin | Built-in | Epic 2-5 | Content management (reciters, translations, tafseer, audio uploads) |
| **Containerization** | Docker + Docker Compose | Latest | All | Consistent dev/prod environments, easy deployment |
| **Cloud Provider** | AWS | N/A | All | Comprehensive services (S3, CloudFront, OpenSearch, RDS, ECS) |

---

## Technology Stack Details

### Core Technologies

**Backend:**
- **Django 5.2.8 LTS**: Web framework with ORM, admin, authentication
- **Django REST Framework 3.16.1+**: API framework with serialization, viewsets, permissions
- **Python 3.14**: Latest stable Python version with performance improvements

**Database:**
- **PostgreSQL 16**: Primary relational database for all structured data
- **Redis**: In-memory cache and Celery message broker
- **Elasticsearch (AWS OpenSearch)**: Full-text search engine for Arabic Quran text

**Infrastructure:**
- **AWS S3**: Object storage for 156K+ audio files (25 reciters × 6,236 verses)
- **AWS CloudFront**: CDN for global audio delivery with edge caching
- **AWS RDS PostgreSQL**: Managed database with Multi-AZ for high availability
- **AWS ElastiCache Redis**: Managed Redis cluster
- **AWS OpenSearch Service**: Managed Elasticsearch cluster

**Background Processing:**
- **Celery 5.x**: Distributed task queue for imports, indexing, notifications
- **Celery Beat**: Periodic task scheduler for analytics, cache warming
- **Redis**: Message broker and result backend for Celery

**Authentication:**
- **djangorestframework-simplejwt**: JWT token authentication
- **Access tokens**: 30-minute lifetime
- **Refresh tokens**: 14-day lifetime

**Monitoring & Error Tracking:**
- **Sentry**: Application monitoring and error tracking
- **Real-time alerts**: Immediate notification of errors and performance issues
- **Performance monitoring**: Track API response times, database queries, slow endpoints
- **Release tracking**: Associate errors with specific deployments
- **User context**: Track which users experience errors

**Python Libraries:**
```
# Core Framework
Django==5.2.8
djangorestframework==3.16.1
djangorestframework-simplejwt==5.3.1

# Configuration & Environment
django-environ==0.11.2
python-dotenv==1.0.0

# Database
psycopg2-binary==2.9.9

# Caching & Background Jobs
django-redis==5.4.0
celery==5.3.6

# AWS Integration
django-storages[s3]==1.14.2
boto3==1.34.0

# Search
elasticsearch-dsl==8.11.0

# Data Processing & Analysis
numpy==1.26.2
morfessor==2.0.6

# Country Data
pycountry==23.12.11

# HTTP Requests
requests==2.31.0

# Monitoring & Error Tracking
sentry-sdk==1.40.0

# Documentation
sphinx==7.2.6
sphinx-rtd-theme==2.0.0

# Server
gunicorn==21.2.0

# Testing
pytest-django==4.7.0
pytest-cov==4.1.0

# Development Tools
debugpy==1.8.0
```

**Library Usage:**
- **python-dotenv**: Fallback for loading .env files (django-environ primary)
- **numpy**: Audio processing, statistical analysis for recitation metadata
- **morfessor**: Arabic morphological segmentation for advanced search (Phase 2)
- **pycountry**: Standardized country names/codes for reciter profiles
- **requests**: HTTP client for downloading audio files from Tanzil.net
- **sentry-sdk**: Real-time error tracking and performance monitoring (critical for zero-error tolerance NFR)
- **sphinx**: API documentation generation
- **debugpy**: VS Code debugging support for Django development

### Integration Points

**External Services:**
```
S3 (Audio Storage)
  ↓
CloudFront (CDN) → Mobile Apps

PostgreSQL RDS ← Django ORM → All Apps

Redis ElastiCache ← Celery → Background Jobs
                   ← Django Cache → All Apps

OpenSearch ← Django Models → Quran Search

Sentry ← Django Middleware → Error Tracking
       ← Celery Integration → Background Job Monitoring
       ← Custom Instrumentation → Critical Operations
```

**Internal App Dependencies:**
```
quran.Verse (Core Model)
  ↑
  ├── reciters.Audio (FK to Verse)
  ├── translations.Translation (FK to Verse)
  ├── tafseer.Tafseer (FK to Verse)
  ├── bookmarks.Bookmark (FK to Verse)
  └── offline.DownloadManifest (references Verses)

core (Authentication, Permissions)
  ↓
All Apps (use JWT auth, rate limiting, error handling)
```

---

## Project Structure

```
muslim_companion/
│
├── config/                           # Project configuration
│   ├── settings.py                  # Single settings file (reads .env)
│   ├── urls.py                      # Root URL configuration
│   ├── wsgi.py                      # WSGI application
│   └── celery_app.py                # Celery configuration
│
├── apps/                             # Django applications
│   │
│   ├── core/                        # EPIC 1: Infrastructure
│   │   ├── models.py                # Base models, timestamps
│   │   ├── authentication.py        # JWT auth logic
│   │   ├── permissions.py           # Custom permissions
│   │   ├── throttling.py            # Rate limiting
│   │   ├── exceptions.py            # Custom exceptions
│   │   ├── middleware.py            # Error handling middleware
│   │   └── tasks.py                 # Core Celery tasks
│   │
│   ├── quran/                       # EPIC 2: Quran Text & Content
│   │   ├── models.py                # Surah, Verse, Juz, Page models
│   │   ├── serializers.py           # DRF serializers
│   │   ├── views.py                 # API views
│   │   ├── urls.py                  # URL routing
│   │   ├── search.py                # Elasticsearch integration
│   │   ├── tasks.py                 # Import tasks (Celery)
│   │   ├── validators.py            # Quran data validators
│   │   ├── management/
│   │   │   └── commands/
│   │   │       ├── import_quran_text.py
│   │   │       ├── import_surah_metadata.py
│   │   │       └── index_quran_elasticsearch.py
│   │   └── tests/
│   │       ├── test_models.py
│   │       ├── test_views.py
│   │       ├── test_search.py
│   │       └── factories.py
│   │
│   ├── reciters/                    # EPIC 3: Recitation Management
│   │   ├── models.py                # Riwayah, Reciter, Audio models
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── tasks.py                 # Audio import tasks
│   │   ├── storage.py               # S3 storage handlers
│   │   ├── management/
│   │   │   └── commands/
│   │   │       ├── initialize_riwayat.py    # Load 20 canonical Riwayahs from CSV
│   │   │       ├── initialize_reciters.py   # Load reciter profiles (with Riwayah mapping)
│   │   │       └── import_reciter_audio.py  # Import audio files from Tanzil.net
│   │   └── tests/
│   │
│   ├── translations/                # EPIC 4: Translation Management
│   │   ├── models.py                # Translator, Translation models
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── tasks.py                 # Translation import tasks
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── import_translations.py
│   │   └── tests/
│   │
│   ├── tafseer/                     # EPIC 5: Tafseer Management
│   │   ├── models.py                # Scholar, Tafseer models
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   ├── tasks.py
│   │   ├── management/
│   │   │   └── commands/
│   │   │       └── import_tafseer.py
│   │   └── tests/
│   │
│   ├── bookmarks/                   # EPIC 6: Bookmark Management
│   │   ├── models.py                # Bookmark, ReadingHistory models
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── tests/
│   │
│   ├── offline/                     # EPIC 7: Offline Content Management
│   │   ├── models.py                # DownloadManifest, ContentVersion
│   │   ├── serializers.py
│   │   ├── views.py                 # Manifest API endpoints
│   │   ├── urls.py
│   │   ├── manifest_generator.py   # Generate download manifests
│   │   ├── checksum.py             # SHA-256 hash utilities
│   │   └── tests/
│   │
│   └── users/                       # User management (Cookiecutter Django)
│       ├── models.py                # Custom User model
│       ├── serializers.py
│       ├── views.py
│       ├── urls.py
│       └── tests/
│
├── requirements/                     # Python dependencies
│   ├── base.txt                     # Base requirements
│   ├── local.txt                    # Local dev requirements
│   └── production.txt               # Production requirements
│
├── compose/                          # Docker configuration
│   ├── production/
│   │   ├── django/
│   │   │   ├── Dockerfile
│   │   │   ├── entrypoint
│   │   │   └── start
│   │   └── postgres/
│   └── local/
│       ├── django/
│       └── postgres/
│
├── docs/                            # Documentation
│   ├── PRD.md                       # Product Requirements Document
│   ├── epics.md                     # Epic and user story breakdown
│   ├── architecture.md              # This document
│   └── api/
│       └── openapi.yaml             # API specification
│
├── .env.example                     # Environment template
├── .env                            # Local environment (gitignored)
├── .env.production                 # Production environment (gitignored)
│
├── manage.py                        # Django management script
├── docker-compose.yml               # Docker compose (local)
├── docker-compose.production.yml    # Docker compose (production)
├── pytest.ini                       # Pytest configuration
├── .pre-commit-config.yaml          # Pre-commit hooks
└── README.md                        # Project README
```

---

## Epic to Architecture Mapping

| Epic | Django App | Primary Models | Key API Endpoints |
|------|------------|----------------|-------------------|
| **EPIC 1: Infrastructure** | `core` | BaseModel (abstract) | `/api/v1/auth/login/`, `/api/v1/auth/refresh/` |
| **EPIC 2: Quran Text** | `quran` | Surah, Verse, Juz, Page | `/api/v1/surahs/`, `/api/v1/verses/`, `/api/v1/juz/`, `/api/v1/pages/`, `/api/v1/search/` |
| **EPIC 3: Reciters** | `reciters` | Riwayah, Reciter, Audio | `/api/v1/riwayat/`, `/api/v1/reciters/`, `/api/v1/audio/` |
| **EPIC 4: Translations** | `translations` | Translator, Translation | `/api/v1/translations/`, `/api/v1/translators/` |
| **EPIC 5: Tafseer** | `tafseer` | Scholar, Tafseer | `/api/v1/tafseer/`, `/api/v1/scholars/` |
| **EPIC 6: Bookmarks** | `bookmarks` | Bookmark, ReadingHistory | `/api/v1/bookmarks/`, `/api/v1/history/` |
| **EPIC 7: Offline** | `offline` | DownloadManifest, ContentVersion | `/api/v1/offline/manifest/` |

---

## Data Architecture

### Core Database Schema

**Epic 2: Quran Text**

```python
class Surah(BaseModel):
    """Surah (Chapter) of the Quran"""
    id = IntegerField(primary_key=True)  # 1-114 (Mushaf order)
    name_arabic = TextField()
    name_english = CharField(max_length=100)
    name_transliteration = CharField(max_length=100)
    revelation_type = CharField(choices=['Meccan', 'Medinan'])
    revelation_order = IntegerField()  # Chronological order of revelation (1-114)
    revelation_note = TextField(blank=True)  # Exceptions (e.g., "Except 17-33 and 48-50, from Medina")
    total_verses = IntegerField()
    mushaf_page_start = IntegerField()
    juz_start = IntegerField()

    class Meta:
        indexes = [
            Index(fields=['revelation_order']),  # For chronological navigation
        ]

    @property
    def is_mixed_revelation(self):
        """Returns True if Surah has verses from both Mecca and Medina"""
        return bool(self.revelation_note)

class Verse(BaseModel):
    """Individual verse (Ayah) of the Quran"""
    id = AutoField(primary_key=True)
    surah = ForeignKey(Surah, on_delete=CASCADE)
    verse_number = IntegerField()  # 1-286
    text_uthmani = TextField()  # Full Othmani script with diacritics
    text_simple = TextField()  # Simplified Arabic (no diacritics)
    juz_number = IntegerField()
    mushaf_page = IntegerField()
    hizb_quarter = IntegerField()
    search_vector = SearchVectorField(null=True)  # For full-text search

    class Meta:
        unique_together = ('surah', 'verse_number')
        indexes = [
            Index(fields=['surah', 'verse_number']),
            Index(fields=['juz_number']),
            Index(fields=['mushaf_page']),
            GinIndex(fields=['search_vector']),
        ]

class Juz(BaseModel):
    """Juz (Part) of the Quran (1-30)"""
    id = IntegerField(primary_key=True)  # 1-30
    name_arabic = CharField(max_length=100)
    first_verse = ForeignKey(Verse, related_name='juz_start')
    last_verse = ForeignKey(Verse, related_name='juz_end')

class Page(BaseModel):
    """Mushaf page (1-604)"""
    id = IntegerField(primary_key=True)  # 1-604
    first_verse = ForeignKey(Verse, related_name='page_start')
    last_verse = ForeignKey(Verse, related_name='page_end')
    surah = ForeignKey(Surah)  # Primary Surah on this page
```

**Epic 3: Reciters & Audio**

```python
class Riwayah(BaseModel):
    """
    Canonical Quranic transmission (Riwayah) from the 10 recognized Qira'at.

    Represents authenticated transmission chains of Quranic recitation.
    All 20 canonical Riwayahs (10 Qira'at × 2 transmissions each) stored as master data.

    Related FRs: FR-040 (Riwayah Master Data)
    """
    id = AutoField(primary_key=True)  # 1-20 for the canonical Riwayahs
    name_arabic = CharField(max_length=200)  # e.g., "حفص عن عاصم"
    name_english = CharField(max_length=200)  # e.g., "Hafs from 'Asim"
    qari = CharField(max_length=100)  # Primary reader (e.g., "'Asim")
    rawi = CharField(max_length=100)  # Transmitter (e.g., "Hafs")
    is_active = BooleanField(default=True)  # Enable/disable for gradual rollout
    display_order = IntegerField(default=100)  # For sorting (Hafs = 1, most common)

    class Meta:
        db_table = 'reciters_riwayah'
        verbose_name = 'Riwayah (Quranic Transmission)'
        verbose_name_plural = 'Riwayat (Quranic Transmissions)'
        ordering = ['display_order', 'name_english']
        indexes = [
            Index(fields=['is_active', 'display_order']),
            Index(fields=['name_english']),
        ]

    def __str__(self):
        return f"{self.name_english} ({self.name_arabic})"

    def clean(self):
        """Validate Riwayah data integrity"""
        if not self.name_arabic or not self.name_english:
            raise ValidationError("Both Arabic and English names are required")
        if not self.qari or not self.rawi:
            raise ValidationError("Both Qari and Rawi must be specified")

class Reciter(BaseModel):
    """
    Quran reciter profile with mandatory Riwayah association.

    Each reciter-Riwayah combination is a unique entry (e.g., "Abdul Basit - Hafs"
    and "Abdul Basit - Warsh" would be two separate Reciter records).

    Related FRs: FR-006 (Reciter Profile Management), FR-041 (Reciter-Riwayah Association)
    """
    id = AutoField(primary_key=True)
    slug = CharField(max_length=50, unique=True)  # Tanzil.net reciter slug (e.g., 'abdulbasit', 'afasy')
    name_arabic = CharField(max_length=200)
    name_english = CharField(max_length=200)
    biography_arabic = TextField(blank=True)
    biography_english = TextField(blank=True)

    # MANDATORY Riwayah association (replaces free-text recitation_style)
    riwayah = ForeignKey(
        Riwayah,
        on_delete=PROTECT,  # Cannot delete Riwayah if reciters use it
        related_name='reciters',
        help_text="Canonical Quranic transmission used by this reciter"
    )

    country_code = CharField(max_length=2)  # ISO 3166-1 alpha-2 (validated with pycountry)
    birth_year = IntegerField(null=True, blank=True)
    death_year = IntegerField(null=True, blank=True)
    photo_url = URLField(null=True, blank=True)
    is_active = BooleanField(default=True)

    class Meta:
        db_table = 'reciters_reciter'
        indexes = [
            Index(fields=['is_active', 'name_english']),
            Index(fields=['riwayah', 'is_active']),  # Filter by Riwayah
            Index(fields=['country_code']),
            Index(fields=['slug']),
        ]

    @property
    def country_name(self):
        """Get country name from ISO code using pycountry"""
        import pycountry
        country = pycountry.countries.get(alpha_2=self.country_code)
        return country.name if country else self.country_code

    @property
    def display_name(self):
        """Full display name with Riwayah"""
        return f"{self.name_english} - {self.riwayah.name_english}"

    def clean(self):
        """Validate country code and Riwayah status"""
        import pycountry
        if self.country_code and not pycountry.countries.get(alpha_2=self.country_code):
            raise ValidationError(f"Invalid country code: {self.country_code}")

        # Prevent assigning inactive Riwayahs to new reciters
        if self.riwayah and not self.riwayah.is_active and not self.pk:
            raise ValidationError(f"Cannot assign inactive Riwayah: {self.riwayah.name_english}")

class Audio(BaseModel):
    """
    Audio file for a specific verse recitation with Riwayah traceability.

    Riwayah is auto-populated from parent Reciter for data integrity and analytics.

    Related FRs: FR-042 (Audio-Riwayah Traceability)
    """
    id = AutoField(primary_key=True)
    reciter = ForeignKey(Reciter, on_delete=CASCADE, related_name='audio_files')
    verse = ForeignKey(Verse, on_delete=CASCADE, related_name='audio_files')

    # Explicit Riwayah tracking for filtering and analytics
    riwayah = ForeignKey(
        Riwayah,
        on_delete=PROTECT,
        related_name='audio_files',
        help_text="Quranic transmission used in this recitation (auto-populated from reciter)"
    )

    s3_key = CharField(max_length=500)  # Path in S3 bucket
    file_size_bytes = BigIntegerField()
    duration_seconds = DecimalField(max_digits=6, decimal_places=2)
    quality = CharField(max_length=20)  # bitrate info

    # Optional: Audio analysis metadata (populated via numpy processing)
    amplitude_mean = FloatField(null=True)  # Average amplitude
    amplitude_std = FloatField(null=True)   # Standard deviation

    class Meta:
        db_table = 'reciters_audio'
        unique_together = ('reciter', 'verse')
        indexes = [
            Index(fields=['reciter', 'verse']),
            Index(fields=['riwayah', 'verse']),  # Filter by Riwayah
            Index(fields=['verse', 'riwayah']),  # Verse-level Riwayah lookup
        ]

    def save(self, *args, **kwargs):
        """Auto-populate Riwayah from parent Reciter on creation"""
        if not self.riwayah_id and self.reciter_id:
            self.riwayah = self.reciter.riwayah
        super().save(*args, **kwargs)

    def clean(self):
        """Validate Riwayah consistency with Reciter"""
        if self.riwayah and self.reciter and self.riwayah != self.reciter.riwayah:
            raise ValidationError(
                f"Audio Riwayah ({self.riwayah.name_english}) must match "
                f"Reciter Riwayah ({self.reciter.riwayah.name_english})"
            )

    def analyze_audio(self):
        """Analyze audio file statistics using numpy (optional, Phase 2)"""
        # Example: Load audio, compute statistics
        # import numpy as np
        # from scipy.io import wavfile
        # rate, data = wavfile.read(audio_file)
        # self.amplitude_mean = float(np.mean(np.abs(data)))
        # self.amplitude_std = float(np.std(data))
        pass

    @property
    def cloudfront_url(self):
        """Generate CloudFront URL for audio delivery"""
        surah_num = self.verse.surah.id
        verse_num = self.verse.verse_number
        return f"https://{settings.AWS_CLOUDFRONT_DOMAIN}/{self.reciter.slug}/{surah_num:03d}{verse_num:03d}.mp3"

    @property
    def tanzil_source_url(self):
        """Generate Tanzil.net source URL for downloading audio"""
        surah_num = self.verse.surah.id
        verse_num = self.verse.verse_number
        return f"https://tanzil.net/res/audio/{self.reciter.slug}/{surah_num:03d}{verse_num:03d}.mp3"
```

**Epic 4: Translations**

```python
class Translator(BaseModel):
    """Translator profile"""
    id = AutoField(primary_key=True)
    name = CharField(max_length=200)
    language_code = CharField(max_length=10)  # ISO 639-1 (en, ar, ur, etc.)
    biography = TextField()
    methodology = TextField()  # Translation approach
    year = IntegerField(null=True)

    class Meta:
        indexes = [
            Index(fields=['language_code']),
        ]

class Translation(BaseModel):
    """Verse translation"""
    id = AutoField(primary_key=True)
    translator = ForeignKey(Translator, on_delete=CASCADE)
    verse = ForeignKey(Verse, on_delete=CASCADE)
    text = TextField()

    class Meta:
        unique_together = ('translator', 'verse')
        indexes = [
            Index(fields=['translator', 'verse']),
        ]
```

**Epic 5: Tafseer**

```python
class Scholar(BaseModel):
    """Islamic scholar who authored Tafseer"""
    id = AutoField(primary_key=True)
    name_arabic = CharField(max_length=200)
    name_english = CharField(max_length=200)
    biography_arabic = TextField()
    biography_english = TextField()
    birth_year = IntegerField(null=True)
    death_year = IntegerField(null=True)

class Tafseer(BaseModel):
    """Quranic interpretation (Tafseer)"""
    id = AutoField(primary_key=True)
    scholar = ForeignKey(Scholar, on_delete=CASCADE)
    verse = ForeignKey(Verse, on_delete=CASCADE)
    text_arabic = TextField()
    text_english = TextField(null=True)

    class Meta:
        unique_together = ('scholar', 'verse')
        indexes = [
            Index(fields=['scholar', 'verse']),
        ]
```

**Epic 6: Bookmarks**

```python
class Bookmark(BaseModel):
    """User bookmark for a verse"""
    id = AutoField(primary_key=True)
    user = ForeignKey(User, on_delete=CASCADE)
    verse = ForeignKey(Verse, on_delete=CASCADE)
    note = TextField(blank=True)
    category = CharField(max_length=50, choices=[
        ('reading', 'Reading'),
        ('memorization', 'Memorization'),
        ('favorite', 'Favorite'),
        ('study', 'Study'),
    ])

    class Meta:
        unique_together = ('user', 'verse')
        indexes = [
            Index(fields=['user', 'created_at']),
            Index(fields=['user', 'category']),
        ]

class ReadingHistory(BaseModel):
    """Track user's reading activity"""
    id = AutoField(primary_key=True)
    user = ForeignKey(User, on_delete=CASCADE)
    verse = ForeignKey(Verse, on_delete=CASCADE)
    timestamp = DateTimeField(auto_now_add=True)
    duration_seconds = IntegerField(null=True)  # How long they read/listened

    class Meta:
        indexes = [
            Index(fields=['user', '-timestamp']),
        ]
```

**Epic 7: Offline Content**

```python
class ContentVersion(BaseModel):
    """Version tracking for offline content"""
    id = AutoField(primary_key=True)
    content_type = CharField(max_length=50, choices=[
        ('quran_text', 'Quran Text'),
        ('reciter_audio', 'Reciter Audio'),
        ('translation', 'Translation'),
        ('tafseer', 'Tafseer'),
    ])
    content_id = IntegerField()  # Reciter ID, Translator ID, etc.
    version = CharField(max_length=20)
    checksum = CharField(max_length=64)  # SHA-256 hash

    class Meta:
        unique_together = ('content_type', 'content_id', 'version')

class DownloadManifest(BaseModel):
    """Generated manifest for offline downloads"""
    id = AutoField(primary_key=True)
    reciter = ForeignKey(Reciter, null=True, on_delete=CASCADE)
    surah = ForeignKey(Surah, null=True, on_delete=CASCADE)
    juz = ForeignKey(Juz, null=True, on_delete=CASCADE)
    scope = CharField(max_length=20, choices=[
        ('verse', 'Single Verse'),
        ('surah', 'Surah'),
        ('juz', 'Juz'),
        ('complete', 'Complete Quran'),
    ])
    manifest_json = JSONField()  # List of files with URLs, sizes, checksums
    total_size_bytes = BigIntegerField()
    generated_at = DateTimeField(auto_now=True)
```

---

## Model Relationships & Data Flow

### Entity Relationship Overview

The data model establishes the following key relationships:

**Core Quran Content Hierarchy:**
```
Surah (1) ─────> (N) Verse
Juz (1) ────────> (N) Verse
Page (1) ───────> (N) Verse
```

**Recitation & Audio with Riwayah Traceability:**
```
Riwayah (1) ────> (N) Reciter  [MANDATORY FK with PROTECT]
Riwayah (1) ────> (N) Audio    [MANDATORY FK with PROTECT, auto-populated]
Reciter (1) ────> (N) Audio    [CASCADE delete]
Verse (1) ──────> (N) Audio    [CASCADE delete]

Unique Constraint: (Reciter, Verse) - each reciter has one audio file per verse
Data Integrity: Audio.riwayah MUST equal Audio.reciter.riwayah
```

**Translation Content:**
```
Translator (1) ──> (N) Translation  [CASCADE delete]
Verse (1) ───────> (N) Translation  [CASCADE delete]

Unique Constraint: (Translator, Verse) - each translator has one translation per verse
```

**Tafseer (Interpretation):**
```
Scholar (1) ─────> (N) Tafseer  [CASCADE delete]
Verse (1) ───────> (N) Tafseer  [CASCADE delete]

Unique Constraint: (Scholar, Verse) - each scholar has one tafseer per verse
```

**User Engagement:**
```
User (1) ────────> (N) Bookmark  [CASCADE delete]
User (1) ────────> (N) ReadingHistory  [CASCADE delete]
Verse (1) ───────> (N) Bookmark  [CASCADE delete]
Verse (1) ───────> (N) ReadingHistory  [CASCADE delete]

Unique Constraint: (User, Verse) - each user can bookmark a verse once
```

**Offline Content Management:**
```
Reciter (1) ─────> (N) DownloadManifest  [CASCADE delete]
ContentVersion tracks versioning for cache invalidation
```

### Riwayah (Qira'at Transmission) Integration

**Critical Design Decision (FR-040, FR-041, FR-042):**

The architecture enforces **canonical Quranic transmission authenticity** through a three-tier relationship:

1. **Riwayah Master Data (Reference Table)**
   - 20 canonical entries representing authentic Quranic transmissions
   - Immutable during runtime (seeded from `/docs/Data/Riwayah-Transmission.csv`)
   - Cannot be deleted if referenced by Reciter or Audio (PROTECT constraint)

2. **Reciter → Riwayah (Mandatory Association)**
   - Every Reciter MUST be associated with a Riwayah
   - Replaces free-text `recitation_style` field with referential integrity
   - Same physical reciter reading different Riwayahs = separate Reciter records
   - Example: "Abdul Basit - Hafs" and "Abdul Basit - Warsh" are two distinct Reciter entries

3. **Audio → Riwayah (Auto-populated Traceability)**
   - Every Audio file explicitly linked to its Riwayah
   - `Audio.riwayah` auto-populated from `Audio.reciter.riwayah` on save
   - Enables filtering: "Show me all Warsh recitations for this verse"
   - Enables analytics: "How many audio files do we have for each Riwayah?"

**Data Flow Example:**
```
1. Admin creates Reciter: "Abdul Basit" → Selects Riwayah: "Hafs from 'Asim" (ID=10)
2. Import process creates Audio records for this Reciter
3. Audio.save() auto-populates Audio.riwayah_id = 10 from Reciter.riwayah_id
4. Data validation ensures Audio.riwayah == Audio.reciter.riwayah
5. API consumers can now filter: GET /api/v1/audio/?verse_id=1&riwayah_id=10
```

**Referential Integrity Rules:**
- **Cannot delete Riwayah** if any Reciter or Audio references it (PROTECT)
- **Cannot assign inactive Riwayah** to new Reciters (validation in clean())
- **Riwayah consistency enforced** between Audio and its parent Reciter (validation in clean())
- **Auto-population on save** ensures Audio.riwayah is never null if Reciter exists

### Index Strategy for Qira'at Queries

**Riwayah Model Indexes:**
```python
Index(fields=['is_active', 'display_order'])  # Active Riwayat ordered by commonality
Index(fields=['name_english'])                 # Alphabetical lookup
```

**Reciter Model Indexes:**
```python
Index(fields=['is_active', 'name_english'])    # Active reciters alphabetically
Index(fields=['riwayah', 'is_active'])         # Filter reciters by Riwayah
Index(fields=['country_code'])                 # Geographic filtering
Index(fields=['slug'])                         # URL-friendly lookup
```

**Audio Model Indexes:**
```python
Index(fields=['reciter', 'verse'])             # Primary lookup (with unique constraint)
Index(fields=['riwayah', 'verse'])             # Filter audio by Riwayah + verse
Index(fields=['verse', 'riwayah'])             # Verse-level Riwayah comparison
```

**Query Performance Examples:**
```sql
-- Get all Hafs reciters (uses riwayah+is_active index)
SELECT * FROM reciters_reciter
WHERE riwayah_id = 10 AND is_active = true;

-- Get all available Riwayahs for a verse (uses verse+riwayah index)
SELECT DISTINCT riwayah_id FROM reciters_audio
WHERE verse_id = 1;

-- Compare verse across Riwayahs (uses riwayah+verse index)
SELECT * FROM reciters_audio
WHERE verse_id = 1 AND riwayah_id IN (10, 2);
```

### Data Migration Strategy

**Migrating from recitation_style (CharField) to Riwayah (ForeignKey):**

1. Create Riwayah model and populate 20 canonical entries
2. Add nullable riwayah ForeignKey to Reciter model
3. Run data migration:
   ```python
   # Map existing recitation_style values to Riwayah IDs
   mapping = {
       'Hafs': 10,
       'Warsh': 2,
       'Qalun': 1,
       # ... all 20 mappings
   }
   for reciter in Reciter.objects.all():
       riwayah_id = mapping.get(reciter.recitation_style)
       if riwayah_id:
           reciter.riwayah_id = riwayah_id
           reciter.save()
   ```
4. Make riwayah field non-nullable (add constraint)
5. Remove recitation_style field
6. Auto-populate Audio.riwayah from Audio.reciter.riwayah

---

## API Contracts

### Authentication Endpoints

**POST /api/v1/auth/register/**
```json
Request:
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "password_confirm": "SecurePassword123!"
}

Response: 201 Created
{
  "data": {
    "user": {
      "id": 1,
      "email": "user@example.com",
      "created_at": "2025-11-06T14:30:00Z"
    },
    "tokens": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
  }
}
```

**POST /api/v1/auth/login/**
```json
Request:
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}

Response: 200 OK
{
  "data": {
    "tokens": {
      "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
      "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
    }
  }
}
```

**POST /api/v1/auth/refresh/**
```json
Request:
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}

Response: 200 OK
{
  "data": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

### Quran Text Endpoints

**GET /api/v1/surahs/**
```json
Response: 200 OK
{
  "data": [
    {
      "id": 1,
      "name_arabic": "الفاتحة",
      "name_english": "Al-Fatiha",
      "name_transliteration": "Al-Faatiha",
      "revelation_type": "Meccan",
      "revelation_order": 5,
      "total_verses": 7
    },
    ...
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_pages": 6,
    "total_count": 114
  }
}
```

**GET /api/v1/surahs/{id}/verses/**
```json
Response: 200 OK
{
  "data": {
    "surah": {
      "id": 1,
      "name_arabic": "الفاتحة",
      "name_english": "Al-Fatiha",
      "revelation_order": 5
    },
    "verses": [
      {
        "id": 1,
        "verse_number": 1,
        "text_uthmani": "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
        "text_simple": "بسم الله الرحمن الرحيم",
        "juz_number": 1,
        "mushaf_page": 1
      },
      ...
    ]
  }
}
```

**GET /api/v1/verses/{id}/**
```json
Response: 200 OK
{
  "data": {
    "id": 1,
    "surah": {
      "id": 1,
      "name_arabic": "الفاتحة",
      "name_english": "Al-Fatiha",
      "revelation_order": 5
    },
    "verse_number": 1,
    "text_uthmani": "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
    "text_simple": "بسم الله الرحمن الرحيم",
    "juz_number": 1,
    "mushaf_page": 1
  }
}
```

**GET /api/v1/search/?q={query}**
```json
Request: /api/v1/search/?q=الرحمن

Response: 200 OK
{
  "data": {
    "query": "الرحمن",
    "results": [
      {
        "verse_id": 1,
        "surah_name": "Al-Fatiha",
        "verse_number": 1,
        "text": "بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
        "highlighted": "بِسْمِ ٱللَّهِ <mark>ٱلرَّحْمَٰنِ</mark> ٱلرَّحِيمِ"
      },
      ...
    ],
    "total_results": 169
  },
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_pages": 9,
    "total_count": 169
  }
}
```

### Reciter Endpoints

**GET /api/v1/riwayat/**
```json
Response: 200 OK
{
  "data": [
    {
      "id": 10,
      "name_arabic": "حفص عن عاصم",
      "name_english": "Hafs from 'Asim",
      "qari": "'Asim",
      "rawi": "Hafs",
      "is_active": true,
      "display_order": 1,
      "reciter_count": 15
    },
    {
      "id": 2,
      "name_arabic": "ورش عن نافع",
      "name_english": "Warsh from Nafi'",
      "qari": "Nafi'",
      "rawi": "Warsh",
      "is_active": true,
      "display_order": 2,
      "reciter_count": 3
    },
    ...
  ]
}
```

**GET /api/v1/reciters/?riwayah_id={id}**
```json
Request: /api/v1/reciters/?riwayah_id=10

Response: 200 OK
{
  "data": [
    {
      "id": 1,
      "slug": "abdulbasit",
      "name_arabic": "عبد الباسط عبد الصمد",
      "name_english": "Abdul Basit Abdul Samad",
      "riwayah": {
        "id": 10,
        "name_arabic": "حفص عن عاصم",
        "name_english": "Hafs from 'Asim"
      },
      "country": "Egypt",
      "country_code": "EG",
      "photo_url": "https://cdn.../reciters/1.jpg",
      "is_active": true
    },
    ...
  ],
  "filters": {
    "riwayah_id": 10,
    "country_code": null
  },
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_pages": 1,
    "total_count": 15
  }
}
```

**GET /api/v1/reciters/{id}/**
```json
Response: 200 OK
{
  "data": {
    "id": 1,
    "slug": "abdulbasit",
    "name_arabic": "عبد الباسط عبد الصمد",
    "name_english": "Abdul Basit Abdul Samad",
    "biography_arabic": "...",
    "biography_english": "...",
    "riwayah": {
      "id": 10,
      "name_arabic": "حفص عن عاصم",
      "name_english": "Hafs from 'Asim",
      "qari": "'Asim",
      "rawi": "Hafs"
    },
    "country": "Egypt",
    "country_code": "EG",
    "birth_year": 1927,
    "death_year": 1988,
    "photo_url": "https://cdn.../reciters/1.jpg",
    "is_active": true,
    "audio_count": 6236
  }
}
```

**GET /api/v1/audio/?reciter_id={id}&verse_id={id}**
```json
Response: 200 OK
{
  "data": {
    "id": 1,
    "reciter": {
      "id": 1,
      "name_english": "Abdul Basit Abdul Samad",
      "riwayah": {
        "id": 10,
        "name_english": "Hafs from 'Asim"
      }
    },
    "verse": {
      "id": 1,
      "surah_id": 1,
      "verse_number": 1
    },
    "riwayah": {
      "id": 10,
      "name_arabic": "حفص عن عاصم",
      "name_english": "Hafs from 'Asim"
    },
    "url": "https://d1234567890.cloudfront.net/1/001/001.mp3",
    "file_size_bytes": 102400,
    "duration_seconds": 4.5
  }
}
```

**GET /api/v1/audio/?verse_id={id}&riwayah_id={id}**
```json
Request: /api/v1/audio/?verse_id=1&riwayah_id=10

Response: 200 OK
{
  "data": [
    {
      "id": 1,
      "reciter": {
        "id": 1,
        "name_english": "Abdul Basit Abdul Samad"
      },
      "url": "https://d1234567890.cloudfront.net/1/001/001.mp3",
      "duration_seconds": 4.5
    },
    {
      "id": 15,
      "reciter": {
        "id": 8,
        "name_english": "Mishary Alafasy"
      },
      "url": "https://d1234567890.cloudfront.net/8/001/001.mp3",
      "duration_seconds": 3.8
    }
  ],
  "filters": {
    "verse_id": 1,
    "riwayah_id": 10
  }
}
```

### Offline Manifest Endpoint

**GET /api/v1/offline/manifest/?reciter_id={id}&scope=surah&surah_id={id}**
```json
Response: 200 OK
{
  "data": {
    "version": "1.0",
    "reciter_id": 1,
    "scope": "surah",
    "surah_id": 2,
    "files": [
      {
        "verse_id": 1,
        "url": "https://d1234567890.cloudfront.net/1/002/001.mp3",
        "size_bytes": 102400,
        "checksum": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "duration_seconds": 4.5
      },
      ...
    ],
    "total_size_bytes": 52428800,
    "total_files": 286
  }
}
```

### Standard Error Response

```json
{
  "error": {
    "code": "VERSE_NOT_FOUND",
    "message": "The requested verse does not exist",
    "details": {
      "surah_id": 115,
      "verse_number": 1
    },
    "timestamp": "2025-11-06T14:30:00Z"
  }
}
```

---

## Implementation Patterns

### Naming Conventions

**Database Tables:**
- Convention: Singular, lowercase with underscores
- Examples: `quran_surah`, `quran_verse`, `reciters_reciter`, `reciters_audio`

**Database Columns:**
- Convention: snake_case
- Examples: `surah_id`, `verse_number`, `name_arabic`, `created_at`

**Django Models:**
- Convention: PascalCase, singular
- Examples: `Surah`, `Verse`, `Reciter`, `Audio`

**API Endpoints:**
- Convention: Plural nouns, kebab-case for multi-word
- Examples: `/api/v1/surahs/`, `/api/v1/reciters/`, `/api/v1/audio-files/`, `/api/v1/reading-history/`

**Python Files:**
- Convention: snake_case
- Examples: `models.py`, `serializers.py`, `test_models.py`, `import_quran_text.py`

**Environment Variables:**
- Convention: UPPER_CASE with underscores
- Examples: `DEBUG`, `SECRET_KEY`, `DATABASE_URL`, `AWS_ACCESS_KEY_ID`

### Code Organization

**Django App Structure:**
```python
apps/quran/
├── models.py              # All models for this app
├── serializers.py         # All DRF serializers
├── views.py               # All API views
├── urls.py                # URL routing
├── tasks.py               # Celery tasks
├── validators.py          # Custom validators
├── management/
│   └── commands/          # Management commands
├── tests/
│   ├── test_models.py
│   ├── test_views.py
│   ├── test_serializers.py
│   └── factories.py       # Test data factories
└── migrations/            # Database migrations
```

**Import Order:**
```python
# Standard library
import os
from datetime import datetime

# Third-party
from django.db import models
from rest_framework import serializers

# Local
from apps.quran.models import Verse
from apps.core.exceptions import ValidationError
```

### Response Formats

**Success - Single Resource:**
```python
{
  "data": {
    "id": 1,
    "surah_number": 1,
    "name_arabic": "الفاتحة"
  }
}
```

**Success - List with Pagination:**
```python
{
  "data": [...],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_pages": 6,
    "total_count": 114
  }
}
```

**Error:**
```python
{
  "error": {
    "code": "VERSE_NOT_FOUND",
    "message": "The requested verse does not exist",
    "details": {...},
    "timestamp": "2025-11-06T14:30:00Z"
  }
}
```

### Consistency Rules

**Date/Time Format:**
- Convention: ISO 8601 UTC
- Format: `"2025-11-06T14:30:00Z"`
- Storage: UTC timestamps in database
- Client: Responsible for timezone conversion

**JSON Field Naming:**
- Convention: snake_case (consistent with Python)
- Example: `{"surah_number": 1, "created_at": "2025-11-06T14:30:00Z"}`

**Logging:**
```python
import logging
logger = logging.getLogger(__name__)

logger.info(
    "Verse retrieved",
    extra={
        "surah_id": 1,
        "verse_number": 1,
        "user_id": request.user.id,
        "endpoint": "/api/v1/verses/"
    }
)
```

**Log Levels:**
- DEBUG: Detailed debugging information
- INFO: General informational messages
- WARNING: Warning messages (deprecated usage, etc.)
- ERROR: Error messages (recoverable)
- CRITICAL: Critical errors (system crash)

**Error Messages (User-Facing):**
- Convention: Clear, actionable, no technical jargon
- Good: "The requested verse does not exist. Please check the Surah and verse numbers."
- Bad: "DoesNotExist: Verse matching query does not exist."

**Model Timestamps:**
```python
from django.db import models

class BaseModel(models.Model):
    """Base model with timestamps for all models"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# All models inherit from BaseModel
class Verse(BaseModel):
    surah = models.ForeignKey(Surah, on_delete=models.CASCADE)
    verse_number = models.IntegerField()
    text_uthmani = models.TextField()
```

### Location Patterns

**S3 Audio File Paths:**
- Convention: `{reciter_slug}/{surah:03d}{verse:03d}.mp3` (matches Tanzil.net format)
- Examples:
  - `s3://quran-audio/abdulbasit/001001.mp3` (Al-Fatiha, verse 1 by AbdulBasit)
  - `s3://quran-audio/afasy/002286.mp3` (Al-Baqara, verse 286 by Al-Afasy)
  - `s3://quran-audio/husary-mjwd/114006.mp3` (An-Nas, verse 6 by Al-Husary Mujawwad)

**CloudFront URL Generation:**
```python
def get_audio_url(reciter_slug, surah_number, verse_number):
    """Generate CloudFront URL for audio file"""
    return f"https://{settings.AWS_CLOUDFRONT_DOMAIN}/{reciter_slug}/{surah_number:03d}{verse_number:03d}.mp3"

def get_tanzil_source_url(reciter_slug, surah_number, verse_number):
    """Generate Tanzil.net source URL for downloading audio"""
    return f"https://tanzil.net/res/audio/{reciter_slug}/{surah_number:03d}{verse_number:03d}.mp3"
```

**Redis Cache Keys:**
```python
# Quran text
quran:surah:{surah_id}  → Full Surah JSON
quran:verse:{surah_id}:{verse_number}  → Single verse
quran:page:{page_number}  → Mushaf page
quran:juz:{juz_number}  → Complete Juz

# Reciters
reciters:list  → All active reciters
reciters:detail:{reciter_id}  → Reciter profile

# Translations
translations:list:{language_code}  → Translations for language
translations:verse:{translator_id}:{verse_id}  → Single verse translation

# User data (short TTL)
user:{user_id}:bookmarks  → User's bookmarks list
```

**Static/Media Files:**
```python
static/
├── admin/          # Django admin static files
├── rest_framework/ # DRF browsable API assets
└── api/           # Custom API assets (if any)

media/
└── reciters/
    └── photos/
        └── {reciter_id}.jpg
```

---

## Error Handling

### Error Response Format

```python
{
  "error": {
    "code": "ERROR_CODE",
    "message": "User-friendly error message",
    "details": {
      "field_name": "Additional context"
    },
    "timestamp": "2025-11-06T14:30:00Z"
  }
}
```

### Error Code Categories

**Authentication Errors (AUTH_*):**
- `AUTH_INVALID_TOKEN`: JWT token is invalid or malformed
- `AUTH_EXPIRED_TOKEN`: JWT token has expired
- `AUTH_INVALID_CREDENTIALS`: Email/password combination is incorrect
- `AUTH_USER_NOT_FOUND`: User account does not exist

**Validation Errors (VALIDATION_*):**
- `VALIDATION_INVALID_SURAH`: Surah ID out of range (must be 1-114)
- `VALIDATION_INVALID_VERSE`: Verse number exceeds Surah's total verses
- `VALIDATION_INVALID_JUZ`: Juz number out of range (must be 1-30)
- `VALIDATION_INVALID_PAGE`: Page number out of range (must be 1-604)
- `VALIDATION_REQUIRED_FIELD`: Required field is missing

**Resource Errors (RESOURCE_*):**
- `RESOURCE_NOT_FOUND`: Requested resource does not exist
- `RESOURCE_ALREADY_EXISTS`: Resource already exists (duplicate)
- `RESOURCE_CONFLICT`: Operation conflicts with existing data

**Server Errors (SERVER_*):**
- `SERVER_ERROR`: Internal server error (500)
- `SERVER_UNAVAILABLE`: Service temporarily unavailable (503)
- `SERVER_TIMEOUT`: Request timed out

**Rate Limiting (RATE_LIMIT_*):**
- `RATE_LIMIT_EXCEEDED`: Too many requests, rate limit exceeded

### HTTP Status Codes

```python
# Success
200 OK: Successful GET, PUT, PATCH
201 Created: Successful POST (resource created)
204 No Content: Successful DELETE

# Client Errors
400 Bad Request: Validation errors, malformed request
401 Unauthorized: Authentication required
403 Forbidden: Insufficient permissions
404 Not Found: Resource not found
409 Conflict: Resource conflict (duplicate)
429 Too Many Requests: Rate limit exceeded

# Server Errors
500 Internal Server Error: Unhandled server error
503 Service Unavailable: Service temporarily down
```

### Logging Strategy

**What to Log:**
- All API requests (endpoint, user, timestamp)
- All errors with full context
- Authentication events (login, logout, failed attempts)
- Import job progress and failures
- Performance metrics (slow queries, cache misses)

**What NOT to Log:**
- Passwords or tokens
- Personal user data (PII)
- Full request/response bodies (unless debugging)

**Log Format:**
```python
# Structured logging with context
logger.error(
    "Verse retrieval failed",
    extra={
        "error_code": "RESOURCE_NOT_FOUND",
        "surah_id": 115,
        "verse_number": 1,
        "user_id": request.user.id,
        "endpoint": "/api/v1/verses/",
        "ip_address": request.META.get('REMOTE_ADDR')
    },
    exc_info=True  # Include stack trace
)
```

---

## Security Architecture

### Authentication & Authorization

**JWT Token Flow:**
```
1. User registers/logs in
2. Server generates access token (30 min) + refresh token (14 days)
3. Client stores tokens securely
4. All API requests include: Authorization: Bearer <access_token>
5. Server validates token signature and expiration
6. When access token expires, client uses refresh token to get new access token
```

**Token Configuration:**
```python
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=14),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'ALGORITHM': 'HS256',
    'SIGNING_KEY': settings.SECRET_KEY,
    'AUTH_HEADER_TYPES': ('Bearer',),
}
```

**Permission Levels:**
- **Anonymous users**: Read-only access to Quran text, audio, translations, Tafseer
- **Authenticated users**: Full access (bookmarks, history, downloads)
- **Admin users**: Import operations, content management

### Data Protection

**Passwords:**
- Hashing: Django default (Argon2 or PBKDF2)
- Minimum requirements: 8 characters, mix of letters/numbers/symbols
- Password reset: Time-limited tokens via email

**Data Encryption:**
- **In Transit**: TLS 1.3+ enforced on all API endpoints
- **At Rest**:
  - RDS PostgreSQL: Encryption enabled
  - S3: Server-side encryption (SSE-S3 or SSE-KMS)
  - ElastiCache Redis: Encryption enabled

**Sensitive Data:**
- Email addresses: Stored hashed for privacy
- User preferences: Encrypted at field level if containing PII
- No user location data collected or stored (privacy commitment)

### Rate Limiting

**Tiered Rate Limits:**
```python
# Django REST Framework throttling
REST_FRAMEWORK = {
    'DEFAULT_THROTTLE_CLASSES': [
        'rest_framework.throttling.AnonRateThrottle',
        'rest_framework.throttling.UserRateThrottle',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'anon': '100/hour',  # Anonymous users
        'user': '1000/hour',  # Authenticated users
    }
}
```

**Rate Limit Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1699281600
```

**Rate Limit Exceeded Response:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "You have exceeded the rate limit. Please try again later.",
    "details": {
      "limit": 1000,
      "reset_at": "2025-11-06T15:00:00Z"
    }
  }
}
```

### CORS Configuration

```python
CORS_ALLOWED_ORIGINS = [
    "https://app.yourapp.com",
    "https://admin.yourapp.com",
]

# Local development only
if DEBUG:
    CORS_ALLOW_ALL_ORIGINS = True
```

---

## Performance Considerations

### Caching Strategy

**Redis Cache Layers:**

```python
# Quran text (NEVER EXPIRE - immutable)
CACHE_TTL = {
    'quran_text': None,  # Never expire
    'tafseer': None,  # Classical Tafseer never changes
    'reciters': 86400,  # 24 hours
    'translations': 86400,  # 24 hours
    'audio_metadata': 604800,  # 7 days
    'user_bookmarks': 300,  # 5 minutes
}
```

**Cache Invalidation:**
```python
# Manual admin command
python manage.py clear_cache --pattern="reciters:*"

# Automatic on update
@receiver(post_save, sender=Reciter)
def invalidate_reciter_cache(sender, instance, **kwargs):
    cache.delete_pattern(f"reciters:detail:{instance.id}")
    cache.delete("reciters:list")
```

**CloudFront Caching:**
```
Audio files: 365 days (immutable)
API responses: No caching (dynamic content)
```

### Database Optimization

**Indexes:**
```python
class Verse(BaseModel):
    class Meta:
        indexes = [
            Index(fields=['surah', 'verse_number']),  # Primary lookup
            Index(fields=['juz_number']),  # Juz navigation
            Index(fields=['mushaf_page']),  # Page navigation
            GinIndex(fields=['search_vector']),  # Full-text search
        ]
```

**Query Optimization:**
```python
# Use select_related for foreign keys
verses = Verse.objects.select_related('surah').filter(juz_number=1)

# Use prefetch_related for many-to-many or reverse FKs
reciters = Reciter.objects.prefetch_related('audio_set').filter(is_active=True)

# Only select needed fields
verses = Verse.objects.only('id', 'text_uthmani', 'verse_number')
```

**Connection Pooling:**
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'CONN_MAX_AGE': 600,  # 10 minutes
        'OPTIONS': {
            'connect_timeout': 10,
        }
    }
}
```

### Elasticsearch Optimization

**Index Settings:**
```json
{
  "settings": {
    "number_of_shards": 3,
    "number_of_replicas": 2,
    "analysis": {
      "analyzer": {
        "arabic_analyzer": {
          "type": "custom",
          "tokenizer": "standard",
          "filter": ["lowercase", "arabic_normalization", "arabic_stemmer"]
        }
      }
    }
  },
  "mappings": {
    "properties": {
      "text_uthmani": {"type": "text", "analyzer": "arabic_analyzer"},
      "text_simple": {"type": "text", "analyzer": "arabic_analyzer"},
      "surah_id": {"type": "integer"},
      "verse_number": {"type": "integer"}
    }
  }
}
```

**Advanced Search with Morfessor (Phase 2):**

For root word analysis and morphological search, integrate morfessor:

```python
# apps/quran/search.py
import morfessor

class ArabicMorphologyAnalyzer:
    """Arabic morphological segmentation for advanced search"""

    def __init__(self):
        self.model = morfessor.MorfessorIO()
        # Load pre-trained Arabic model or train on Quran corpus

    def segment_word(self, arabic_word):
        """
        Segment Arabic word into morphemes
        Example: "المسلمون" → ["ال", "مسلم", "ون"]
        """
        return self.model.viterbi_segment(arabic_word)[0]

    def find_root(self, arabic_word):
        """Extract potential root from Arabic word"""
        segments = self.segment_word(arabic_word)
        # Apply Arabic root extraction rules
        # Return root candidates
        return segments

# Usage in search queries (Phase 2)
def advanced_search(query):
    """
    Search with morphological analysis
    - User searches: "المؤمنين"
    - Morfessor finds root: "ءمن"
    - Returns all verses with words from same root
    """
    analyzer = ArabicMorphologyAnalyzer()
    root = analyzer.find_root(query)
    # Search Elasticsearch with root variants
    return search_by_root(root)
```

**Note:** Morfessor integration is Phase 2 enhancement for advanced search features.

### API Response Time Targets

```
Quran text retrieval: < 200ms (p95)
Audio URL generation: < 100ms (p95)
Search queries: < 500ms (p95)
Manifest generation: < 1000ms (p95)
Bookmark operations: < 300ms (p95)
```

---

## Deployment Architecture

### AWS Infrastructure

**Compute:**
- **ECS Fargate** or **EKS**: Containerized Django application
- **Auto Scaling**: Scale based on CPU/memory/request count
- **Application Load Balancer**: HTTPS termination, health checks

**Database:**
- **RDS PostgreSQL 16**: Multi-AZ for high availability
- **Instance Type**: db.t4g.medium (production start, scale up as needed)
- **Backups**: Automated daily backups, 7-day retention

**Cache:**
- **ElastiCache Redis**: Cluster mode enabled
- **Node Type**: cache.t4g.micro (start), scale to cache.r6g.large

**Search:**
- **OpenSearch Service**: Managed Elasticsearch cluster
- **Instance Type**: t3.medium.search (start), scale to r6g.large.search
- **Availability Zones**: 3 AZs for production

**Storage:**
- **S3**: Audio files bucket with versioning enabled
- **CloudFront**: Global CDN with 365-day cache for audio
- **Lifecycle Policy**: Archive old audio versions to Glacier after 90 days

**Networking:**
- **VPC**: Private subnets for RDS, Redis, OpenSearch
- **Security Groups**: Strict ingress/egress rules
- **NAT Gateway**: For private subnet internet access

**Monitoring:**
- **CloudWatch**: Logs, metrics, alarms
- **X-Ray**: Distributed tracing (optional)
- **Sentry**: Error tracking and performance monitoring

### Environment Variables (.env)

```bash
# Django
DEBUG=False
SECRET_KEY=your-production-secret-key-min-50-chars
ALLOWED_HOSTS=api.yourapp.com,www.yourapp.com
DATABASE_URL=postgres://user:password@rds-endpoint:5432/quran_db

# Redis
REDIS_URL=redis://elasticache-endpoint:6379/0

# AWS
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_STORAGE_BUCKET_NAME=quran-audio-production
AWS_S3_REGION_NAME=us-east-1
AWS_CLOUDFRONT_DOMAIN=d1234567890.cloudfront.net

# Elasticsearch
ELASTICSEARCH_URL=https://opensearch-endpoint.us-east-1.es.amazonaws.com

# JWT
JWT_ACCESS_TOKEN_LIFETIME=30
JWT_REFRESH_TOKEN_LIFETIME=14

# Sentry (Error Tracking)
SENTRY_DSN=https://examplePublicKey@o0.ingest.sentry.io/0

# Email (for password reset)
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.sendgrid.net
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=apikey
EMAIL_HOST_PASSWORD=SG.xxx
```

### Deployment Process

**1. Build Docker Image:**
```bash
docker build -f compose/production/django/Dockerfile -t quran-api:latest .
docker push quran-api:latest
```

**2. Deploy to ECS:**
```bash
# Update ECS service with new image
aws ecs update-service --cluster quran-cluster --service quran-api --force-new-deployment
```

**3. Run Migrations:**
```bash
# Run as one-time task in ECS
aws ecs run-task --cluster quran-cluster --task-definition quran-migrate
```

**4. Collect Static Files:**
```bash
python manage.py collectstatic --noinput
```

### Health Checks

```python
# Health check endpoint
@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """Health check for load balancer"""
    # Check database
    try:
        from django.db import connection
        connection.cursor()
    except Exception:
        return Response({'status': 'unhealthy'}, status=503)

    # Check Redis
    try:
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
    except Exception:
        return Response({'status': 'unhealthy'}, status=503)

    return Response({'status': 'healthy'}, status=200)
```

---

## Development Environment

### Prerequisites

**Required Software:**
- Python 3.14
- Docker & Docker Compose
- Git
- PostgreSQL client (psql)
- Redis client (redis-cli)

**Optional:**
- AWS CLI (for S3/CloudFront testing)
- Elasticsearch/Kibana (local development)
- VS Code (for debugpy integration)

### Local Setup Commands

```bash
# Clone repository
git clone https://github.com/yourorg/muslim_companion.git
cd muslim_companion

# Create .env from template
cp .env.example .env
# Edit .env with local values

# Build and start Docker containers
docker-compose up -d

# Run database migrations
docker-compose exec django python manage.py migrate

# Create superuser
docker-compose exec django python manage.py createsuperuser

# Import initial data
docker-compose exec django python manage.py import_quran_metadata --source docs/Data/quran-data.xml
docker-compose exec django python manage.py import_quran_text --source docs/Data/quran-uthmani.xml

# Initialize all 25 reciters from Tanzil.net
docker-compose exec django python manage.py initialize_reciters

# Import audio files for priority reciters (example: abdulbasit)
docker-compose exec django python manage.py import_reciter_audio --reciter-slug abdulbasit

# Import translations
docker-compose exec django python manage.py import_translations --language en

# Index Quran text in Elasticsearch
docker-compose exec django python manage.py index_quran_elasticsearch

# Run tests
docker-compose exec django pytest

# Access Django shell
docker-compose exec django python manage.py shell

# View logs
docker-compose logs -f django

# Generate API documentation
docker-compose exec django sphinx-build -b html docs/source docs/build

# Run debugger (VS Code attach on port 5678)
# Add to docker-compose.yml django service:
# command: python -m debugpy --listen 0.0.0.0:5678 --wait-for-client manage.py runserver 0.0.0.0:8000
```

### Debugging with VS Code

**VS Code launch.json configuration:**
```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Remote Attach",
      "type": "python",
      "request": "attach",
      "connect": {
        "host": "localhost",
        "port": 5678
      },
      "pathMappings": [
        {
          "localRoot": "${workspaceFolder}",
          "remoteRoot": "/app"
        }
      ],
      "justMyCode": false
    }
  ]
}
```

**Usage:**
1. Update docker-compose.yml django service command with debugpy
2. Start containers: `docker-compose up -d`
3. In VS Code: Run > Start Debugging (F5)
4. Set breakpoints and debug as normal

### API Documentation Generation

**Initialize Sphinx (one-time setup):**
```bash
mkdir -p docs/source
docker-compose exec django sphinx-quickstart docs
```

**Documentation structure:**
```
docs/
├── source/
│   ├── conf.py          # Sphinx configuration
│   ├── index.rst        # Documentation index
│   ├── api/
│   │   ├── endpoints.rst    # API endpoint reference
│   │   ├── authentication.rst
│   │   └── models.rst
│   └── guides/
│       ├── quickstart.rst
│       └── deployment.rst
└── build/               # Generated HTML (gitignored)
```

**Generate documentation:**
```bash
# Build HTML documentation
docker-compose exec django sphinx-build -b html docs/source docs/build

# View at: http://localhost:8000/docs/ (serve via Django static)
```

**Auto-document Django models and views:**
```python
# In docs/source/conf.py
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.napoleon',  # For Google/NumPy docstrings
]
```

### Docker Compose Services

```yaml
# docker-compose.yml
services:
  postgres:
    image: postgres:16
    environment:
      POSTGRES_DB: quran_db
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    ports:
      - "5432:5432"

  redis:
    image: redis:7
    ports:
      - "6379:6379"

  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"

  django:
    build:
      context: .
      dockerfile: compose/local/django/Dockerfile
    command: python manage.py runserver 0.0.0.0:8000
    volumes:
      - .:/app
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
      - elasticsearch
    env_file:
      - .env

  celery_worker:
    build:
      context: .
      dockerfile: compose/local/django/Dockerfile
    command: celery -A config worker -l info
    volumes:
      - .:/app
    depends_on:
      - redis
      - postgres
    env_file:
      - .env

  celery_beat:
    build:
      context: .
      dockerfile: compose/local/django/Dockerfile
    command: celery -A config beat -l info
    volumes:
      - .:/app
    depends_on:
      - redis
    env_file:
      - .env
```

### Testing Strategy

**Test Coverage Requirements:**
- Overall: > 80%
- Critical modules (quran, reciters): > 90%
- Models: 100% (all fields, methods, validators)
- Views: > 85% (all endpoints, error cases)
- Serializers: > 90% (validation, transformations)

**Test Structure:**
```python
# apps/quran/tests/test_models.py
import pytest
from apps.quran.models import Surah, Verse

@pytest.mark.django_db
class TestSurahModel:
    def test_surah_creation(self):
        surah = Surah.objects.create(
            id=1,
            name_arabic="الفاتحة",
            name_english="Al-Fatiha",
            revelation_type="Meccan",
            total_verses=7
        )
        assert surah.name_english == "Al-Fatiha"
        assert surah.total_verses == 7

    def test_surah_str_representation(self):
        surah = Surah.objects.create(id=1, name_english="Al-Fatiha", total_verses=7)
        assert str(surah) == "Al-Fatiha"

@pytest.mark.django_db
class TestVerseModel:
    def test_verse_creation_with_surah(self):
        surah = Surah.objects.create(id=1, name_english="Al-Fatiha", total_verses=7)
        verse = Verse.objects.create(
            surah=surah,
            verse_number=1,
            text_uthmani="بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ",
            juz_number=1,
            mushaf_page=1
        )
        assert verse.surah == surah
        assert verse.verse_number == 1

# apps/quran/tests/test_views.py
import pytest
from rest_framework.test import APIClient

@pytest.mark.django_db
class TestSurahAPI:
    def test_list_surahs(self):
        client = APIClient()
        response = client.get('/api/v1/surahs/')
        assert response.status_code == 200
        assert 'data' in response.json()

    def test_retrieve_surah_detail(self):
        surah = Surah.objects.create(id=1, name_english="Al-Fatiha", total_verses=7)
        client = APIClient()
        response = client.get(f'/api/v1/surahs/{surah.id}/')
        assert response.status_code == 200
        assert response.json()['data']['name_english'] == "Al-Fatiha"
```

**Run Tests:**
```bash
# All tests
pytest

# With coverage
pytest --cov=apps --cov-report=html

# Specific app
pytest apps/quran/tests/

# Specific test
pytest apps/quran/tests/test_models.py::TestSurahModel::test_surah_creation
```

---

## Architecture Decision Records (ADRs)

### ADR-001: Use Cookiecutter Django as Foundation

**Status:** Accepted
**Date:** 2025-11-06
**Context:** Need a production-ready Django boilerplate with best practices
**Decision:** Use Cookiecutter Django template
**Rationale:**
- Saves ~40% of initial setup decisions
- Production-ready security configurations
- Docker/Docker Compose included
- Celery, Redis, pytest pre-configured
- Active maintenance and community support

**Consequences:**
- Faster initial setup
- Lower risk (proven template)
- Some customization needed (single settings.py)

---

### ADR-002: Single settings.py with django-environ

**Status:** Accepted
**Date:** 2025-11-06
**Context:** Cookiecutter Django uses separate settings/base.py, local.py, production.py
**Decision:** Replace with single settings.py using django-environ for .env management
**Rationale:**
- Simpler mental model
- Easier for intermediate developers
- Environment-specific logic handled via environment variables
- Follows 12-factor app principles

**Consequences:**
- Requires manual merge of Cookiecutter's split settings
- All environment differences managed via .env files

---

### ADR-003: Elasticsearch for Arabic Text Search

**Status:** Accepted
**Date:** 2025-11-06
**Context:** Need robust Arabic text search with diacritical mark handling
**Decision:** Use Elasticsearch (AWS OpenSearch) instead of PostgreSQL FTS
**Rationale:**
- Superior Arabic language analysis
- Fuzzy matching and relevance scoring
- Scalable for future advanced search features
- Root word analysis support for Phase 2

**Consequences:**
- Additional infrastructure (OpenSearch cluster)
- Higher operational complexity
- Better search quality and user experience

---

### ADR-004: S3 + CloudFront for Audio Delivery

**Status:** Accepted
**Date:** 2025-11-06
**Context:** 156K+ audio files (25 reciters) need global delivery with <2s startup time
**Decision:** Use Tanzil.net as source, S3 for storage + CloudFront CDN for delivery
**Rationale:**
- Tanzil.net provides all 25 reciters with consistent format
- Meets NFR: <2s audio startup globally via edge caching
- S3: Unlimited scale, 11 nines durability
- CloudFront: 400+ edge locations worldwide
- Cost-effective for read-heavy workload

**Consequences:**
- Need to download 156K files from Tanzil.net (one-time)
- CloudFront costs for bandwidth (~$50-100/month for moderate traffic)
- Need to manage S3 bucket lifecycle policies

---

### ADR-005: JWT Authentication with djangorestframework-simplejwt

**Status:** Accepted
**Date:** 2025-11-06
**Context:** Mobile-first API needs stateless authentication
**Decision:** Use JWT tokens via djangorestframework-simplejwt
**Rationale:**
- Stateless (no server-side session storage)
- Mobile-friendly (store tokens in secure storage)
- Industry standard for REST APIs
- Horizontal scaling without sticky sessions

**Consequences:**
- Cannot revoke tokens immediately (must wait for expiration)
- Implement refresh token rotation for security

---

### ADR-006: Aggressive Redis Caching for Immutable Content

**Status:** Accepted
**Date:** 2025-11-06
**Context:** Quran text never changes, must optimize for <200ms response time
**Decision:** Cache Quran text with no expiration (never expire)
**Rationale:**
- Quran text is immutable (verified, never changes)
- Memory is cheap, API speed is critical
- NFR requires <200ms response time

**Consequences:**
- Need manual cache invalidation mechanism (edge case)
- Higher memory usage (acceptable tradeoff)

---

### ADR-007: Normalized Database Schema with Audio Table

**Status:** Accepted
**Date:** 2025-11-06
**Context:** Decision between Audio table vs pattern-based URL generation
**Decision:** Explicit Audio table with FK relationships
**Rationale:**
- Flexibility for per-file metadata (duration, size, quality)
- Easier to track missing audio files
- Can handle multiple qualities per verse
- Better for reporting and analytics

**Consequences:**
- 600K+ audio records in database
- More storage, but better tracking and flexibility

---

### ADR-008: Hybrid Offline Sync with Content Hashes

**Status:** Accepted
**Date:** 2025-11-06
**Context:** Users need reliable offline content with integrity verification
**Decision:** Manifest API with SHA-256 checksums, hybrid download options
**Rationale:**
- Content hashes detect corruption/tampering
- Manifest allows pause/resume per file
- Hybrid approach (packages + custom) serves all user needs
- Industry standard (npm, apt use checksums)

**Consequences:**
- Need to compute and store SHA-256 for all audio files
- Manifest generation overhead (cached aggressively)

---

### ADR-009: Celery Priority Queues

**Status:** Accepted
**Date:** 2025-11-06
**Context:** Background jobs have different priorities (imports vs analytics)
**Decision:** Three Celery queues: celery_high, celery_default, celery_low
**Rationale:**
- Import jobs shouldn't block user operations
- Simple but effective priority management
- Easy to scale workers per queue

**Consequences:**
- Need to configure queue assignments per task
- More complex Celery worker deployment

---

### ADR-010: Sentry for Error Tracking and Performance Monitoring

**Status:** Accepted
**Date:** 2025-11-06
**Context:**
- PRD NFR-037 requires "zero tolerance for Quran text errors"
- NFR-038 requires audio quality monitoring
- Need real-time alerting when errors occur in production
- 99.9% uptime requirement demands proactive error detection
- Global user base requires visibility into errors across regions

**Decision:** Use Sentry for application monitoring, error tracking, and performance monitoring

**Rationale:**
- **Zero-error tolerance alignment**: Immediate alerts when Quran text retrieval fails
- **Performance monitoring**: Track API response times against < 200ms NFR target
- **Contextual debugging**: Stack traces, user context, request data for rapid issue resolution
- **Release tracking**: Associate errors with deployments to identify regressions quickly
- **Production-ready**: Cookiecutter Django includes Sentry support out-of-the-box
- **Free tier sufficient**: 5,000 errors/month adequate for MVP phase
- **Critical for sacred content**: Any error serving Quran text must be detected immediately

**Integration Points:**
- Django middleware captures all unhandled exceptions
- Performance tracking for API endpoints (identify slow queries, bottlenecks)
- Celery integration for background job error tracking
- Custom events for critical operations (Quran import verification, audio file validation)
- Alert rules for critical errors (Quran text errors, authentication failures, data corruption)

**Consequences:**
- **Positive:**
  - Real-time error notifications via email, Slack, or PagerDuty
  - Detailed stack traces with request context for faster debugging
  - Performance insights identifying slow endpoints before they impact users
  - Release tracking helps identify which deployment introduced bugs
  - User impact tracking (how many users affected by each error)

- **Negative:**
  - Additional external dependency (requires Sentry account)
  - Small performance overhead (< 5ms per request)
  - Costs scale with error volume (mitigated by free tier + error prevention)
  - Sensitive data may appear in error reports (requires PII scrubbing configuration)

**Configuration:**
```python
# config/settings.py
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

sentry_sdk.init(
    dsn=env('SENTRY_DSN'),
    integrations=[
        DjangoIntegration(),
        CeleryIntegration(),
    ],
    environment=env('ENVIRONMENT', default='production'),
    release=env('RELEASE_VERSION', default='unknown'),

    # Performance monitoring (10% of transactions)
    traces_sample_rate=0.1,

    # Error filtering
    ignore_errors=[
        # Don't alert on 404s (expected for invalid Surah IDs)
        'django.http.response.Http404',
    ],

    # PII scrubbing
    send_default_pii=False,
    before_send=scrub_sensitive_data,
)

def scrub_sensitive_data(event, hint):
    """Remove sensitive data from Sentry events"""
    # Scrub passwords, tokens, API keys from error reports
    if 'request' in event:
        event['request'].pop('cookies', None)
        if 'headers' in event['request']:
            event['request']['headers'].pop('Authorization', None)
    return event
```

**Alert Configuration:**
```python
# Critical alerts (immediate notification)
- Quran text retrieval errors (any verse not found)
- Database connection failures
- S3/CloudFront audio delivery failures
- Authentication system errors

# Warning alerts (daily digest)
- API response time > 500ms (p95)
- Error rate > 1% of requests
- Celery queue backup (> 1000 pending jobs)
```

**Custom Instrumentation:**
```python
# Track critical operations
with sentry_sdk.start_transaction(op="quran.import", name="Import Quran Text"):
    import_quran_text_from_xml()
    sentry_sdk.capture_message("Quran import completed", level="info")

# Track verse retrieval performance
@sentry_sdk.trace
def get_verse(surah_id, verse_number):
    # Automatically tracked in performance monitoring
    return Verse.objects.get(surah_id=surah_id, verse_number=verse_number)
```

---

### ADR-011: Django Admin for Content Management

**Status:** Accepted
**Date:** 2025-11-06
**Context:**
- Need administrative interface for managing reciters, translations, tafseer, and audio files
- Epic 2 (Quran Text), Epic 3 (Reciters), Epic 4 (Translations), Epic 5 (Tafseer) require content management
- US-RC-001, US-TR-001, US-TF-001, US-RC-002 specify admin CRUD requirements
- Arabic localization required for admin panel (LANGUAGE_CODE = 'ar')
- Verse-level audio upload capability needed (US-RC-002)

**Decision:** Use Django Admin with Arabic localization and custom ModelAdmin classes for content management

**Rationale:**
- **Built-in solution**: Django Admin included in Cookiecutter Django, zero additional dependencies
- **Feature-rich**: List views, filtering, search, bulk actions, inline editing out-of-the-box
- **Customizable**: ModelAdmin classes allow custom forms, actions, and validations
- **Arabic support**: Django i18n automatically translates admin interface to Arabic
- **Permission system**: Built-in authentication, groups, and permissions (django.contrib.auth)
- **Rapid development**: Saves weeks compared to building custom admin UI
- **Production-ready**: Used by thousands of Django projects, battle-tested for years

**Content Management Requirements:**

**Reciters (US-RC-001):**
- CRUD operations for reciter profiles
- List display: name_arabic, name_english, recitation_style, country_code, is_active
- List filters: is_active, country_code, recitation_style
- Search fields: name_arabic, name_english, slug
- Bulk actions: Activate/deactivate reciters
- Arabic localization for all field labels and help text

**Translations (US-TR-001):**
- CRUD operations for translations
- List display: translator_name, language_code, is_active
- List filters: is_active, language_code
- Search fields: translator_name, translator_name_arabic
- Bulk actions: Activate/deactivate translations

**Tafseer (US-TF-001):**
- CRUD operations for tafseer sources
- List display: author_name, language_code, is_active
- List filters: is_active, language_code
- Search fields: author_name, author_name_arabic
- Bulk actions: Activate/deactivate tafseer sources

**Audio Uploads (US-RC-002):**
- Custom admin action or inline for verse-level audio file uploads
- File validation: MP3 format only, max 5MB per file
- S3 storage integration via django-storages
- Audio model inline in Reciter admin for bulk uploads
- Progress tracking for large batch uploads

**Implementation:**
```python
# apps/reciters/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from .models import Reciter, Audio

@admin.register(Reciter)
class ReciterAdmin(admin.ModelAdmin):
    list_display = ['name_arabic', 'name_english', 'recitation_style', 'country_code', 'is_active']
    list_filter = ['is_active', 'country_code', 'recitation_style']
    search_fields = ['name_arabic', 'name_english', 'slug']
    prepopulated_fields = {'slug': ('name_english',)}

    fieldsets = (
        (_('Basic Information'), {
            'fields': ('slug', 'name_arabic', 'name_english', 'recitation_style', 'country_code')
        }),
        (_('Biography'), {
            'fields': ('biography_arabic', 'biography_english', 'photo_url'),
            'classes': ('collapse',)
        }),
        (_('Status'), {
            'fields': ('is_active',)
        }),
    )

    actions = ['activate_reciters', 'deactivate_reciters']

    @admin.action(description=_('Activate selected reciters'))
    def activate_reciters(self, request, queryset):
        queryset.update(is_active=True)

    @admin.action(description=_('Deactivate selected reciters'))
    def deactivate_reciters(self, request, queryset):
        queryset.update(is_active=False)

@admin.register(Audio)
class AudioAdmin(admin.ModelAdmin):
    list_display = ['reciter', 'surah', 'verse_number', 'file_size_mb', 'created_at']
    list_filter = ['reciter', 'surah']
    search_fields = ['reciter__name_english', 'surah__name_english']

    def file_size_mb(self, obj):
        """Display file size in MB"""
        if obj.s3_key:
            # Calculate from S3 metadata
            return f"{obj.get_file_size() / 1024 / 1024:.2f} MB"
        return "N/A"
    file_size_mb.short_description = _('File Size')

# apps/translations/admin.py
@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    list_display = ['translator_name', 'language_code', 'is_active']
    list_filter = ['is_active', 'language_code']
    search_fields = ['translator_name', 'translator_name_arabic']
    actions = ['activate_translations', 'deactivate_translations']

# apps/tafseer/admin.py
@admin.register(Tafseer)
class TafseerAdmin(admin.ModelAdmin):
    list_display = ['author_name', 'language_code', 'is_active']
    list_filter = ['is_active', 'language_code']
    search_fields = ['author_name', 'author_name_arabic']
    actions = ['activate_tafseer', 'deactivate_tafseer']
```

**Audio Upload Form:**
```python
# apps/reciters/forms.py
from django import forms
from django.core.validators import FileExtensionValidator
from django.utils.translation import gettext_lazy as _
from .models import Audio

class AudioUploadForm(forms.ModelForm):
    """Form for verse-level audio file uploads"""
    audio_file = forms.FileField(
        label=_('Audio File'),
        validators=[FileExtensionValidator(allowed_extensions=['mp3'])],
        help_text=_('MP3 format only, max 5MB per file')
    )

    class Meta:
        model = Audio
        fields = ['reciter', 'surah', 'verse_number', 'audio_file']

    def clean_audio_file(self):
        """Validate file size and format"""
        file = self.cleaned_data['audio_file']

        # Validate file size (max 5MB)
        max_size = 5 * 1024 * 1024  # 5MB in bytes
        if file.size > max_size:
            raise forms.ValidationError(_('File size must not exceed 5MB'))

        # Validate MIME type
        if file.content_type != 'audio/mpeg':
            raise forms.ValidationError(_('Only MP3 files are allowed'))

        return file

    def save(self, commit=True):
        """Upload to S3 and save Audio record"""
        instance = super().save(commit=False)
        audio_file = self.cleaned_data['audio_file']

        # Generate S3 key
        s3_key = f"{instance.reciter.slug}/{instance.surah.id:03d}{instance.verse_number:03d}.mp3"

        # Upload to S3 (django-storages handles this automatically)
        instance.s3_key = s3_key
        instance.file_size = audio_file.size

        if commit:
            instance.save()

        return instance
```

**Arabic Localization:**
```python
# locale/ar/LC_MESSAGES/django.po
msgid "Basic Information"
msgstr "المعلومات الأساسية"

msgid "Biography"
msgstr "السيرة الذاتية"

msgid "Status"
msgstr "الحالة"

msgid "Activate selected reciters"
msgstr "تنشيط القراء المحددين"

msgid "Deactivate selected reciters"
msgstr "إلغاء تنشيط القراء المحددين"
```

**Consequences:**
- **Positive:**
  - Complete CRUD operations for all content types (reciters, translations, tafseer)
  - Arabic-first admin interface aligns with target audience
  - Built-in permission system restricts access to authorized staff
  - Bulk actions enable efficient content management at scale
  - Zero additional development time for basic admin UI
  - File upload validation prevents corrupt audio files

- **Negative:**
  - Admin UI customization limited compared to custom-built interface
  - Complex workflows may require custom admin actions
  - Performance issues with very large datasets (mitigated by pagination, caching)
  - Default styling may need CSS overrides for branding

**Security Considerations:**
- Admin access restricted to `is_staff=True` users only
- CSRF protection enabled for all admin forms
- File upload validation prevents malicious file uploads
- S3 pre-signed URLs prevent unauthorized audio access
- Audit logging via django-simple-history (optional enhancement)

---

### ADR-012: JWT Token Response Parameter Naming Standardization

**Status:** Approved
**Date:** 2025-11-07
**Decision Owner:** Osama (Architect)
**Type:** Breaking Change

**Context:**

The current JWT authentication implementation uses abbreviated parameter names in token responses:
- `"access"` for access tokens
- `"refresh"` for refresh tokens

This naming convention is used across:
- User registration endpoint (`POST /api/v1/auth/register/`)
- User login endpoint (`POST /api/v1/auth/login/`)
- Token refresh endpoint (`POST /api/v1/auth/token/refresh/`)
- Logout endpoint (consumes `"refresh"` parameter)

**Problem:**

The abbreviated naming does not align with industry standards:
1. OAuth 2.0 RFC 6749 Section 5.1 specifies `access_token` as the standard response parameter
2. Less explicit naming can cause confusion for API consumers
3. Inconsistent with common OAuth implementations
4. May complicate future token type additions (e.g., `id_token`)

**Decision:**

Rename JWT token response keys to use full, explicit naming:
- `"access"` → `"access_token"`
- `"refresh"` → `"refresh_token"`

This applies to all authentication endpoints returning tokens.

**Rationale:**
1. **Standards Compliance**: Aligns with OAuth 2.0 RFC 6749 token response specifications
2. **API Clarity**: More explicit naming reduces ambiguity about parameter purpose
3. **Developer Experience**: Frontend/mobile developers familiar with OAuth patterns will immediately recognize the structure
4. **Future-Proofing**: Establishes consistent naming pattern for potential future token types
5. **Best Practice**: Matches naming conventions used by major authentication providers (Auth0, Okta, Firebase)

**Impact Assessment:**

**Severity:** Breaking Change - HIGH

**Affected Components:**
1. Backend Serializers (2 files):
   - `UserRegistrationSerializer.to_representation()` (serializers.py:110-113)
   - `UserLoginSerializer.to_representation()` (serializers.py:151-154)

2. Backend Views (2 views):
   - `UserLogoutView.post()` (views.py:149) - expects `"refresh"` in request body
   - `ThrottledTokenRefreshView` (views.py:222) - inherits from SimpleJWT, returns `"access"`

3. Test Suite (8 files):
   - `test_views.py` - 3 assertions
   - `test_lockout.py` - 1 assertion
   - `test_token_expiration.py` - 2 assertions
   - `test_blacklist.py` - 1 assertion
   - `test_password_reset.py` - 1 assertion

4. API Consumers:
   - Frontend applications
   - Mobile applications (iOS/Android)
   - Third-party integrations (if any)

5. Documentation:
   - API documentation/OpenAPI specs
   - User story acceptance criteria
   - Integration guides

**Response Structure Change:**

Before:
```json
{
  "tokens": {
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

After:
```json
{
  "tokens": {
    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

**Implementation Strategy:**

Chosen Approach: Hard Cutover (Option A)

Justification:
- Project is in early development phase (recent commit: US-API-002)
- Comprehensive test coverage exists (8 test files)
- No production traffic or external consumers yet
- Simpler than maintaining dual responses or API versioning

Implementation Steps:

1. Backend Changes:
   - Update `UserRegistrationSerializer.to_representation()` to use `access_token`/`refresh_token`
   - Update `UserLoginSerializer.to_representation()` to use `access_token`/`refresh_token`
   - Update `UserLogoutView` to accept `refresh_token` parameter
   - Override or customize `ThrottledTokenRefreshView` to return `access_token`

2. Test Updates:
   - Update all 8 test files to assert new parameter names
   - Verify all authentication flows still pass

3. Documentation Updates:
   - Update architecture.md Decision Summary table
   - Update API documentation/OpenAPI specs
   - Update user stories (US-API-001 and related)
   - Create migration guide in CHANGELOG

4. Frontend Coordination:
   - Notify frontend/mobile teams of breaking change
   - Provide migration timeline
   - Update API integration examples

Estimated Effort: 2-3 hours backend + testing + frontend coordination

Rollback Plan: Git revert if issues arise during testing phase

**Alternatives Considered:**

Option B: Dual-Response Transition Period
- Return both old and new keys for 2-4 weeks
- Rejected: Unnecessary complexity for pre-production system

Option C: API Versioning
- Create `/api/v2/` endpoints with new structure
- Rejected: Premature optimization, adds maintenance burden

**Success Metrics:**
- All 8 test files pass with updated assertions
- Zero regressions in authentication flows
- Frontend/mobile teams successfully integrate with new parameter names
- API documentation reflects new structure
- No security vulnerabilities introduced

**Related Decisions:**
- Initial authentication architecture (Decision Summary, Line 101)
- ADR-005: JWT Authentication with djangorestframework-simplejwt
- Epic 1: Infrastructure Setup
- US-API-001: Implement User Authentication and Authorization

**Notes:**
- SimpleJWT library's default `TokenRefreshView` also needs customization
- Consider documenting this pattern in API contribution guidelines
- Future token types (e.g., `id_token` for OpenID Connect) should follow same `*_token` suffix pattern

---

## Document Updates

**Version:** 1.6
**Update Date:** 2025-11-10
**Changes:**

### Version 1.6 Updates

**Qira'at/Riwayah Integration for Canonical Transmission Authenticity:**

Integrated Qira'at (Quranic recitation methods) and Riwayah (transmission chains) support based on PRD updates (Version 1.2 - Nov 10, 2025) with functional requirements FR-040, FR-041, and FR-042:

1. **New Riwayah Model Added (FR-040)**
   - Created canonical reference model for 20 authenticated Quranic Riwayahs
   - Replaces free-text recitation_style with referential integrity
   - Fields: name_arabic, name_english, qari, rawi, is_active, display_order
   - Seeded from `/docs/Data/Riwayah-Transmission.csv`
   - PROTECT deletion constraint (cannot delete if referenced by Reciter or Audio)

2. **Reciter Model Updated (FR-006, FR-041)**
   - Added MANDATORY riwayah ForeignKey (replaced recitation_style CharField)
   - Each reciter-Riwayah combination treated as unique entry
   - Example: "Abdul Basit - Hafs" and "Abdul Basit - Warsh" are separate Reciter records
   - Added birth_year and death_year fields for biographical completeness
   - New index: `Index(fields=['riwayah', 'is_active'])` for Riwayah-based filtering
   - Validation prevents assigning inactive Riwayahs to new reciters

3. **Audio Model Enhanced (FR-042)**
   - Added explicit riwayah ForeignKey for audio-level traceability
   - Auto-populates from parent Reciter.riwayah on save()
   - Enables filtering: "Show all Warsh recitations for this verse"
   - Enables analytics: "How many audio files per Riwayah?"
   - New indexes for Riwayah-based queries:
     - `Index(fields=['riwayah', 'verse'])`
     - `Index(fields=['verse', 'riwayah'])`
   - Validation enforces Audio.riwayah == Audio.reciter.riwayah

4. **API Endpoints Updated**
   - New endpoint: `GET /api/v1/riwayat/` - List all canonical Riwayahs
   - Updated: `GET /api/v1/reciters/?riwayah_id={id}` - Filter reciters by Riwayah
   - Updated: `GET /api/v1/audio/?verse_id={id}&riwayah_id={id}` - Filter audio by Riwayah
   - All reciter/audio responses include full Riwayah object (not just style string)

5. **Data Management Commands**
   - New: `initialize_riwayat.py` - Seed 20 canonical Riwayahs from CSV
   - Updated: `initialize_reciters.py` - Map reciters to canonical Riwayahs
   - Updated: `import_reciter_audio.py` - Auto-populate Audio.riwayah

6. **Model Relationships Section Added**
   - Comprehensive Entity Relationship Overview
   - Riwayah Integration Architecture documentation
   - Index Strategy for Qira'at Queries with SQL examples
   - Data Migration Strategy from recitation_style to Riwayah FK

7. **Epic Mapping Updated**
   - EPIC 3 models: Riwayah, Reciter, Audio (was: Reciter, Audio)
   - EPIC 3 endpoints: `/api/v1/riwayat/`, `/api/v1/reciters/`, `/api/v1/audio/`

**Islamic Authenticity Impact:**
This update ensures the Muslim Companion maintains scholarly accuracy in representing how the Quran has been preserved and transmitted across 1400+ years through the 10 canonical Qira'at and their 20 Riwayahs.

---

### Version 1.5 Updates

**Arabic Internationalization and Admin Dashboard Management:**

Based on PRD and epics updates documented in `docs/prd-epics-update-summary.md`, the following enhancements have been integrated into the architecture:

1. **Arabic i18n (Internationalization) Configuration:**
   - Added to Project Initialization section (step 3 post-initialization)
   - `LANGUAGE_CODE = 'ar'` - Arabic as default language
   - Bilingual support: Arabic (العربية) and English
   - `LocaleMiddleware` for language switching
   - `LOCALE_PATHS` configuration for translation files
   - RTL (Right-to-Left) layout support for Arabic UI
   - Aligns with US-API-000: Initialize Django Project with Cookiecutter Django

2. **Decision Summary Table Updates:**
   - Added **Internationalization** row: Django i18n with Arabic as default, bilingual support (Arabic/English), RTL layout
   - Added **Admin Dashboard** row: Django Admin for content management (reciters, translations, tafseer, audio uploads)

3. **Created ADR-011: Django Admin for Content Management**
   - **Context:** Epic 2-5 require admin CRUD operations for reciters, translations, tafseer, and audio files
   - **Decision:** Use Django Admin with Arabic localization and custom ModelAdmin classes
   - **Rationale:** Built-in solution, zero dependencies, Arabic i18n support, permission system, rapid development
   - **Implementation Details:**
     - `ReciterAdmin`: CRUD, filtering, search, bulk actions, Arabic localization (US-RC-001)
     - `TranslationAdmin`: CRUD, filtering, search, bulk actions (US-TR-001)
     - `TafseerAdmin`: CRUD, filtering, search, bulk actions (US-TF-001)
     - `AudioAdmin`: Verse-level audio uploads with validation (US-RC-002)
     - `AudioUploadForm`: Custom form with MP3 validation, max 5MB file size, S3 integration
     - Arabic translation examples in `locale/ar/LC_MESSAGES/django.po`

4. **Audio Upload Capability (US-RC-002):**
   - Custom admin form for verse-level MP3 file uploads
   - File validation: MP3 format only, max 5MB per file
   - S3 storage integration via django-storages
   - Automatic S3 key generation: `{reciter_slug}/{surah:03d}{verse:03d}.mp3`
   - MIME type validation (audio/mpeg)
   - File size tracking in Audio model

5. **Revelation Order Feature Emphasis:**
   - Already implemented in Surah model (v1.1) with `revelation_order` field (1-114 chronological)
   - `revelation_note` field for documenting mixed revelation Surahs
   - Database index for chronological navigation
   - Data source: `docs/Data/quran-data.xml` (Tanzil Project metadata - includes revelation order, Surah names, verse counts, Ruku divisions)
   - Supports US-QT-001 revelation order filtering and sorting requirements

6. **US-API-000 Cookiecutter Django Initialization:**
   - Already documented in ADR-001 (v1.0)
   - Enhanced with Arabic i18n configuration in Project Initialization section
   - Django 5.2.8 LTS with Python 3.14
   - Bilingual support (Arabic/English) from project inception

**Updated Components:**
- Project Initialization section (added step 3: Arabic i18n configuration)
- Decision Summary table (added Internationalization and Admin Dashboard rows)
- ADRs (added ADR-011: Django Admin for Content Management)
- Arabic localization examples and configuration throughout document

**Alignment with PRD/Epics Updates:**
All changes from `docs/prd-epics-update-summary.md` are now reflected in architecture:
- ✅ HP-001: Quran text verification (addressed in US-QT-001 via PM agent)
- ✅ HP-002: 25 reciters from Tanzil.net (already in v1.3)
- ✅ HP-003: US-API-000 Cookiecutter Django initialization (enhanced with i18n)
- ✅ HP-004: Tanzil.net integration (already in v1.3)
- ✅ MP-001: Revelation order feature (already in v1.1, now emphasized)
- ✅ Admin dashboard management (ADR-011 created)
- ✅ Arabic i18n as default language (Project Initialization updated)
- ✅ Verse-level audio upload capability (AudioUploadForm in ADR-011)

### Version 1.4 Updates

**Sentry Integration for Error Tracking and Performance Monitoring:**

1. **Added Sentry to Technology Stack:**
   - Added to Decision Summary table as "Error Tracking" category
   - Integrated with Django and Celery for comprehensive monitoring
   - Free tier (5,000 errors/month) sufficient for MVP

2. **Created ADR-010: Sentry for Error Tracking and Performance Monitoring**
   - **Context:** Zero tolerance for Quran text errors (NFR-037) requires real-time alerting
   - **Decision:** Use Sentry for application monitoring and performance tracking
   - **Rationale:** Critical for detecting Quran text errors immediately, performance tracking against < 200ms NFR
   - **Configuration:** Django integration, Celery integration, PII scrubbing, alert rules
   - **Custom instrumentation:** Track critical operations (Quran imports, verse retrieval)

3. **Added sentry-sdk to Python Dependencies:**
   - `sentry-sdk==1.40.0` for error tracking and performance monitoring
   - Integrated with djangorestframework-simplejwt for context tracking

4. **Alert Configuration Documented:**
   - Critical alerts: Quran text errors, database failures, S3/CloudFront issues, authentication errors
   - Warning alerts: API response times > 500ms, error rate > 1%, Celery queue backups

5. **PII Protection:**
   - Configured `send_default_pii=False`
   - Custom `scrub_sensitive_data` function removes passwords, tokens, cookies from error reports
   - Complies with NFR-026 (no location data selling) and privacy requirements

**Updated Components:**
- Decision Summary table (added Error Tracking row)
- Technology Stack Details (added Monitoring & Error Tracking section)
- Python Libraries (added sentry-sdk==1.40.0)
- Library Usage notes (documented sentry-sdk purpose)
- ADRs (added ADR-010 with complete configuration)
- Cookiecutter prompts (already had use_sentry: y)

### Version 1.3 Updates

**Audio Source Integration (Tanzil.net):**

1. **Audio Source Updated:**
   - Changed from EveryAyah.com to **Tanzil.net** as primary audio source
   - URL format: `https://tanzil.net/res/audio/{reciter_slug}/{surah:03d}{verse:03d}.mp3`
   - Total files: 156,590 (25 reciters × 6,236 verses)

2. **Reciter Model Enhanced:**
   - Added `slug` field (unique, indexed) for Tanzil.net reciter identification
   - Changed biography fields to `blank=True` (not all reciters have bios initially)
   - Added slug index for faster lookups

3. **Audio Model Enhanced:**
   - Updated `cloudfront_url` property to use `reciter.slug` instead of `reciter.id`
   - S3 path format: `{reciter_slug}/{surah:03d}{verse:03d}.mp3`
   - Added `tanzil_source_url` property for downloading from Tanzil.net

4. **Complete Reciter Database (25 Reciters):**
   - Documented all 25 Tanzil.net reciters with slugs, names, styles, and countries
   - Added top 10 priority reciters recommendation for Phase 1
   - Includes popular reciters: AbdulBasit, Al-Afasy, Al-Ghamadi, Al-Sudais, Al-Husary, etc.
   - Includes both Murattal (standard) and Mujawwad (melodic) styles

5. **Import Management Commands:**
   - Added `initialize_reciters.py` - Creates all 25 reciters in database
   - Enhanced `import_reciter_audio.py` - Downloads from Tanzil.net and uploads to S3
   - Includes resume capability (--start-verse parameter)
   - Batch processing with progress reporting

6. **Data Sources Section:**
   - Added comprehensive audio source documentation
   - Complete reciter table with slugs and metadata
   - Import strategy and workflow examples
   - Updated local setup commands with reciter initialization

**Updated Components:**
- Reciter model schema (added slug field)
- Audio model properties (cloudfront_url, tanzil_source_url)
- S3 path patterns (reciter slug-based)
- API endpoint examples (using slug)
- Management commands (initialize_reciters, import_reciter_audio)
- Local development setup workflow

### Version 1.2 Updates

**1. Python Version Update:**
- Updated Python 3.13 → **Python 3.14** throughout document
- Updated Cookiecutter prompt: `use_pycharm: n`

**2. Revelation Order Feature (FR-002 from PRD v1.1):**
- Added `revelation_order` field to Surah model (chronological revelation sequence 1-114)
- Added `revelation_note` field for documenting mixed revelation Surahs
- Added `is_mixed_revelation` property to identify Surahs with verses from both Mecca and Medina
- Added database index for revelation_order for chronological navigation
- Updated all API endpoint examples to include revelation_order in Surah responses
- Supports historical context feature from PRD "Product Magic" section
- **Data Source:** `docs/Data/quran-data.xml` (Tanzil Project - comprehensive Surah metadata including revelation order, names, verse counts, Ruku divisions, Juz/Hizb boundaries)
- Added `import_quran_metadata` management command for XML import (replaces CSV-based `import_surah_metadata`)

**Example:** Surah Al-Fatiha (Mushaf order: 1, Revelation order: 5)
**Mixed Revelation Example:** Al-Qalam (Mushaf: 68, Revelation: 2) - "Except 17-33 and 48-50, from Medina"

### Version 1.1 Updates

### Additional Libraries Integrated

**Added Production Libraries:**
- **python-dotenv 1.0.0**: Environment variable loading (django-environ backup)
- **pycountry 23.12.11**: ISO country codes for reciter validation
- **numpy 1.26.2**: Audio analysis and statistical processing
- **morfessor 2.0.6**: Arabic morphological analysis for advanced search (Phase 2)
- **sphinx 7.2.6**: API documentation generation
- **sphinx-rtd-theme 2.0.0**: ReadTheDocs theme for documentation
- **debugpy 1.8.0**: VS Code remote debugging support

**Libraries Excluded (Conflicts with Django ORM):**
- ❌ alembic (Django migrations used instead)
- ❌ asyncpg (psycopg2-binary synchronous driver used)
- ❌ pydantic-settings (django-environ used for settings)

### Architecture Updates

1. **Reciter Model Enhanced:**
   - Changed `country` (CharField) → `country_code` (ISO 3166-1 alpha-2)
   - Added `country_name` property using pycountry
   - Added country code validation in `clean()` method
   - Added country_code index

2. **Audio Model Enhanced:**
   - Added optional audio analysis fields: `amplitude_mean`, `amplitude_std`
   - Added `analyze_audio()` method for numpy-based audio processing (Phase 2)

3. **Development Environment:**
   - Added VS Code debugging configuration with debugpy
   - Added Sphinx documentation generation workflow
   - Added documentation structure and auto-documentation setup

4. **Search Enhancement (Phase 2):**
   - Documented morfessor integration for Arabic morphological analysis
   - Added `ArabicMorphologyAnalyzer` class example
   - Root word search capability for advanced queries

5. **Library Usage Documentation:**
   - Added detailed usage notes for each new library
   - Clarified Phase 1 vs Phase 2 features
   - Updated Python libraries section with categories

**Decisions Preserved:**
- ✅ Django ORM + Django migrations (not SQLAlchemy)
- ✅ django-environ for settings management
- ✅ psycopg2-binary for synchronous PostgreSQL driver
- ✅ All original architectural decisions maintained

---

## Data Sources and Import Strategy

### Authoritative Data Sources

**Quran Text & Metadata:**
- **Quran Text:** `docs/Data/quran-uthmani.xml` (Tanzil Project - Uthmani v1.1)
  - Complete Quran text: 114 Surahs, 6,236 verses
  - Uthmani script with full diacritics
  - XML format with structured metadata
  - License: Creative Commons Attribution 3.0

- **Quran Metadata:** `docs/Data/quran-data.xml` (Tanzil Project - metadata v1.0)
  - **Comprehensive Surah Data:**
    - `index` - Surah number (1-114)
    - `ayas` - Number of verses per Surah
    - `start` - Starting verse position in full Quran
    - `name` - Arabic name (e.g., الفاتحة)
    - `tname` - Transliterated name (e.g., Al-Faatiha)
    - `ename` - English name (e.g., The Opening)
    - `type` - Revelation type (Meccan/Medinan)
    - `order` - Chronological revelation order (1-114)
    - `rukus` - Number of Ruku divisions per Surah
  - **Juz (Part) Boundaries:** All 30 Juz with Surah/Aya start positions
  - **Hizb Quarter Boundaries:** All 240 quarter divisions with Surah/Aya positions
  - **Additional Metadata:** Manzils, Pages, Sajdas (prostration positions)
  - License: Creative Commons Attribution 3.0
  - Source: https://tanzil.info

**Note:** The `quran-data.xml` replaces the previous `Suras-Order.csv` file, providing significantly richer metadata for all Surah attributes in a single authoritative source.

**Audio Files (Tanzil.net):**
- **Source:** https://tanzil.net/res/audio/
- **Format:** `https://tanzil.net/res/audio/{reciter_slug}/{surah:03d}{verse:03d}.mp3`
- **Total Files:** 156,590 files (25 reciters × 6,236 verses + 114 basmallahs)
- **File Naming:**
  - Surah 1, Verse 1 by AbdulBasit: `001001.mp3`
  - Surah 114, Verse 6 by Al-Afasy: `114006.mp3`

**Available Reciters (25 Total):**

| Slug | Reciter Name | Style | Notes |
|------|--------------|-------|-------|
| `abdulbasit` | AbdulBasit Abdul Samad | Murattal | Standard recitation |
| `abdulbasit-mjwd` | AbdulBasit Abdul Samad | Mujawwad | Melodic recitation |
| `afasy` | Mishary Rashid Al-Afasy | Hafs | Popular contemporary reciter |
| `ajamy` | Ahmed Al-Ajamy | Hafs | Egyptian reciter |
| `akhdar` | Ibrahim Al-Akhdar | Hafs | Moroccan reciter |
| `ghamadi` | Saad Al-Ghamadi | Hafs | Saudi reciter |
| `hudhaify` | Ali Al-Hudhaify | Hafs | Imam of Prophet's Mosque |
| `husary` | Mahmoud Khalil Al-Husary | Murattal | Legendary Egyptian reciter |
| `husary-mjwd` | Mahmoud Khalil Al-Husary | Mujawwad | Melodic style |
| `juhany` | Abdullah Al-Juhany | Hafs | Imam of Makkah |
| `matrood` | Abdullah Matrood | Hafs | Contemporary Saudi reciter |
| `minshawi` | Mohamed Siddiq Al-Minshawi | Murattal | Classic Egyptian reciter |
| `minshawi-mjwd` | Mohamed Siddiq Al-Minshawi | Mujawwad | Melodic style |
| `muaiqly` | Maher Al-Muaiqly | Hafs | Imam of Masjid al-Haram |
| `qasim` | Nasser Al-Qasim | Hafs | Saudi reciter |
| `hani` | Hani Ar-Rifai | Hafs | Contemporary reciter |
| `sudais` | Abdul Rahman Al-Sudais | Hafs | Imam of Masjid al-Haram |
| `shateri` | Abu Bakr Al-Shatri | Hafs | Kuwaiti reciter |
| `shuraim` | Saud Al-Shuraim | Hafs | Imam of Masjid al-Haram |
| `tablawi` | Mohammad At-Tablawi | Hafs | Egyptian reciter |
| `basfar` | Abdullah Basfar | Hafs | Saudi reciter |
| `basfar2` | Abdullah Basfar | Hafs | Alternative recording |
| `bukhatir` | Ali Bukhatir | Hafs | Contemporary reciter |
| `ayyub` | Muhammad Ayyub | Hafs | Former Imam of Prophet's Mosque |
| `jibreel` | Muhammad Jibreel | Hafs | Egyptian reciter |

**Recommended Priority Reciters (Phase 1 - Top 10):**
1. `abdulbasit` - AbdulBasit Abdul Samad (most famous)
2. `afasy` - Mishary Rashid Al-Afasy (very popular)
3. `ghamadi` - Saad Al-Ghamadi (widely used)
4. `sudais` - Abdul Rahman Al-Sudais (Imam of Makkah)
5. `husary` - Mahmoud Khalil Al-Husary (legendary)
6. `muaiqly` - Maher Al-Muaiqly (Imam of Makkah)
7. `ajamy` - Ahmed Al-Ajamy (popular)
8. `minshawi` - Mohamed Siddiq Al-Minshawi (classic)
9. `basfar` - Abdullah Basfar (contemporary)
10. `shateri` - Abu Bakr Al-Shatri (clear pronunciation)

**XML Format (quran-data.xml):**
```xml
<quran type="metadata" version="1.0" copyright="(C) 2008-2009 Tanzil.info" license="cc-by">
  <suras alias="chapters">
    <sura index="1" ayas="7" start="0" name="الفاتحة" tname="Al-Faatiha"
          ename="The Opening" type="Meccan" order="5" rukus="1" />
    <sura index="2" ayas="286" start="7" name="البقرة" tname="Al-Baqara"
          ename="The Cow" type="Medinan" order="87" rukus="40" />
    <!-- ... 114 total Surahs -->
  </suras>
  <juzs alias="parts">
    <juz index="1" sura="1" aya="1" />
    <juz index="2" sura="2" aya="142" />
    <!-- ... 30 total Juz boundaries -->
  </juzs>
  <hizbs alias="groups">
    <quarter index="1" sura="1" aya="1" />
    <!-- ... 240 total quarter boundaries -->
  </hizbs>
</quran>
```

**Import Implementation - Quran Metadata:**

```python
# apps/quran/management/commands/import_quran_metadata.py
import xml.etree.ElementTree as ET
from django.core.management.base import BaseCommand
from apps.quran.models import Surah, Juz, HizbQuarter

class Command(BaseCommand):
    help = 'Import Quran metadata from Tanzil quran-data.xml'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, required=True)

    def handle(self, *args, **options):
        tree = ET.parse(options['source'])
        root = tree.getroot()

        # Import Surah metadata
        suras_imported = 0
        for sura in root.find('suras'):
            Surah.objects.update_or_create(
                id=int(sura.get('index')),
                defaults={
                    'name_arabic': sura.get('name'),
                    'name_transliterated': sura.get('tname'),
                    'name_english': sura.get('ename'),
                    'total_verses': int(sura.get('ayas')),
                    'revelation_type': sura.get('type'),
                    'revelation_order': int(sura.get('order')),
                    'rukus': int(sura.get('rukus')),
                    'start_index': int(sura.get('start')),
                }
            )
            suras_imported += 1

        # Import Juz boundaries
        juzs_imported = 0
        for juz in root.find('juzs'):
            Juz.objects.update_or_create(
                number=int(juz.get('index')),
                defaults={
                    'start_surah_id': int(juz.get('sura')),
                    'start_aya': int(juz.get('aya')),
                }
            )
            juzs_imported += 1

        # Import Hizb quarter boundaries
        quarters_imported = 0
        for quarter in root.find('hizbs'):
            HizbQuarter.objects.update_or_create(
                index=int(quarter.get('index')),
                defaults={
                    'start_surah_id': int(quarter.get('sura')),
                    'start_aya': int(quarter.get('aya')),
                }
            )
            quarters_imported += 1

        self.stdout.write(self.style.SUCCESS(
            f'Successfully imported: {suras_imported} Surahs, '
            f'{juzs_imported} Juz boundaries, {quarters_imported} Hizb quarters'
        ))
```

**Import Implementation - Audio Files:**

```python
# apps/reciters/management/commands/import_reciter_audio.py
import requests
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from apps.reciters.models import Reciter, Audio
from apps.quran.models import Verse

class Command(BaseCommand):
    help = 'Download and import audio files from Tanzil.net for a specific reciter'

    def add_arguments(self, parser):
        parser.add_argument('--reciter-slug', type=str, required=True,
                          help='Reciter slug (e.g., abdulbasit, afasy)')
        parser.add_argument('--batch-size', type=int, default=100,
                          help='Number of files to process in each batch')
        parser.add_argument('--start-verse', type=int, default=1,
                          help='Start from verse ID (for resume capability)')

    def handle(self, *args, **options):
        reciter_slug = options['reciter_slug']
        batch_size = options['batch_size']
        start_verse = options['start_verse']

        try:
            reciter = Reciter.objects.get(slug=reciter_slug)
        except Reciter.DoesNotExist:
            self.stderr.write(f"Reciter '{reciter_slug}' not found. Create reciter first.")
            return

        verses = Verse.objects.filter(id__gte=start_verse).order_by('id')
        total_verses = verses.count()
        self.stdout.write(f"Importing {total_verses} audio files for {reciter.name_english}...")

        success_count = 0
        failed_count = 0

        for verse in verses:
            surah_num = verse.surah.id
            verse_num = verse.verse_number

            # Generate Tanzil.net URL
            url = f"https://tanzil.net/res/audio/{reciter_slug}/{surah_num:03d}{verse_num:03d}.mp3"

            try:
                # Download audio file
                response = requests.get(url, timeout=30)
                response.raise_for_status()

                # Generate S3 key
                s3_key = f"{reciter_slug}/{surah_num:03d}{verse_num:03d}.mp3"

                # Upload to S3 (using django-storages)
                from django.core.files.storage import default_storage
                file_path = default_storage.save(s3_key, ContentFile(response.content))

                # Create Audio record
                Audio.objects.update_or_create(
                    reciter=reciter,
                    verse=verse,
                    defaults={
                        's3_key': s3_key,
                        'file_size_bytes': len(response.content),
                        'duration_seconds': 0,  # Calculate later if needed
                        'quality': '64kbps',
                    }
                )

                success_count += 1

                if success_count % batch_size == 0:
                    self.stdout.write(f"Progress: {success_count}/{total_verses} files imported")

            except Exception as e:
                self.stderr.write(f"Failed to import {url}: {str(e)}")
                failed_count += 1
                continue

        self.stdout.write(self.style.SUCCESS(
            f"Import complete: {success_count} succeeded, {failed_count} failed"
        ))
```

**Import Implementation - Initialize Reciters:**

```python
# apps/reciters/management/commands/initialize_reciters.py
from django.core.management.base import BaseCommand
from apps.reciters.models import Reciter

class Command(BaseCommand):
    help = 'Initialize all 25 Tanzil.net reciters in the database'

    RECITERS = [
        {'slug': 'abdulbasit', 'name': 'AbdulBasit Abdul Samad', 'style': 'Murattal', 'country': 'EG'},
        {'slug': 'abdulbasit-mjwd', 'name': 'AbdulBasit Abdul Samad', 'style': 'Mujawwad', 'country': 'EG'},
        {'slug': 'afasy', 'name': 'Mishary Rashid Al-Afasy', 'style': 'Hafs', 'country': 'KW'},
        {'slug': 'ajamy', 'name': 'Ahmed Al-Ajamy', 'style': 'Hafs', 'country': 'EG'},
        {'slug': 'akhdar', 'name': 'Ibrahim Al-Akhdar', 'style': 'Hafs', 'country': 'MA'},
        {'slug': 'ghamadi', 'name': 'Saad Al-Ghamadi', 'style': 'Hafs', 'country': 'SA'},
        {'slug': 'hudhaify', 'name': 'Ali Al-Hudhaify', 'style': 'Hafs', 'country': 'SA'},
        {'slug': 'husary', 'name': 'Mahmoud Khalil Al-Husary', 'style': 'Murattal', 'country': 'EG'},
        {'slug': 'husary-mjwd', 'name': 'Mahmoud Khalil Al-Husary', 'style': 'Mujawwad', 'country': 'EG'},
        {'slug': 'juhany', 'name': 'Abdullah Al-Juhany', 'style': 'Hafs', 'country': 'SA'},
        {'slug': 'matrood', 'name': 'Abdullah Matrood', 'style': 'Hafs', 'country': 'SA'},
        {'slug': 'minshawi', 'name': 'Mohamed Siddiq Al-Minshawi', 'style': 'Murattal', 'country': 'EG'},
        {'slug': 'minshawi-mjwd', 'name': 'Mohamed Siddiq Al-Minshawi', 'style': 'Mujawwad', 'country': 'EG'},
        {'slug': 'muaiqly', 'name': 'Maher Al-Muaiqly', 'style': 'Hafs', 'country': 'SA'},
        {'slug': 'qasim', 'name': 'Nasser Al-Qasim', 'style': 'Hafs', 'country': 'SA'},
        {'slug': 'hani', 'name': 'Hani Ar-Rifai', 'style': 'Hafs', 'country': 'SA'},
        {'slug': 'sudais', 'name': 'Abdul Rahman Al-Sudais', 'style': 'Hafs', 'country': 'SA'},
        {'slug': 'shateri', 'name': 'Abu Bakr Al-Shatri', 'style': 'Hafs', 'country': 'KW'},
        {'slug': 'shuraim', 'name': 'Saud Al-Shuraim', 'style': 'Hafs', 'country': 'SA'},
        {'slug': 'tablawi', 'name': 'Mohammad At-Tablawi', 'style': 'Hafs', 'country': 'EG'},
        {'slug': 'basfar', 'name': 'Abdullah Basfar', 'style': 'Hafs', 'country': 'SA'},
        {'slug': 'basfar2', 'name': 'Abdullah Basfar II', 'style': 'Hafs', 'country': 'SA'},
        {'slug': 'bukhatir', 'name': 'Ali Bukhatir', 'style': 'Hafs', 'country': 'AE'},
        {'slug': 'ayyub', 'name': 'Muhammad Ayyub', 'style': 'Hafs', 'country': 'SA'},
        {'slug': 'jibreel', 'name': 'Muhammad Jibreel', 'style': 'Hafs', 'country': 'EG'},
    ]

    def handle(self, *args, **options):
        for reciter_data in self.RECITERS:
            reciter, created = Reciter.objects.update_or_create(
                slug=reciter_data['slug'],
                defaults={
                    'name_english': reciter_data['name'],
                    'name_arabic': reciter_data['name'],  # TODO: Add Arabic names
                    'recitation_style': reciter_data['style'],
                    'country_code': reciter_data['country'],
                    'is_active': True,
                }
            )
            status = "Created" if created else "Updated"
            self.stdout.write(f"{status}: {reciter.name_english} ({reciter.slug})")

        self.stdout.write(self.style.SUCCESS(
            f"Successfully initialized {len(self.RECITERS)} reciters"
        ))
```

**Key Insights from Data:**
- 86 Meccan Surahs (revealed 1-86 chronologically)
- 28 Medinan Surahs (revealed 87-114 chronologically)
- 31 Surahs have mixed verses (both Meccan and Medinan)
- Al-Alaq (96) was first revealed (revelation_order: 1)
- An-Nasr (110) was last revealed (revelation_order: 114)

**Data Quality Validation:**
- All 114 Surahs must have revelation_order between 1-114
- No duplicate revelation_order values
- revelation_type must be 'Meccan' or 'Medinan'
- revelation_note documents exceptions for mixed Surahs

---

## Conclusion

This architecture document provides a comprehensive blueprint for building the Muslim Companion API with consistency and quality. All architectural decisions are documented, implementation patterns are explicit, and integration points are validated.

**Key Strengths:**
- ✅ Production-ready foundation (Cookiecutter Django)
- ✅ Scalable infrastructure (AWS, PostgreSQL, Redis, Elasticsearch)
- ✅ Performance-optimized (aggressive caching, CDN, database indexes)
- ✅ Mobile-friendly (JWT auth, offline-first, manifest downloads)
- ✅ Developer-friendly (clear patterns, comprehensive documentation)
- ✅ AI agent consistency (explicit naming, structure, format conventions)

**Next Steps:**
1. Initialize project with Cookiecutter Django
2. Implement core infrastructure (Epic 1)
3. Import Quran text and index in Elasticsearch (Epic 2)
4. Configure S3/CloudFront for audio delivery (Epic 3)
5. Implement remaining epics (4-7)
6. Run solutioning gate check before implementation
7. Proceed to sprint planning

---

_Generated by BMAD Decision Architecture Workflow v1.3.2_
_Date: 2025-11-06_
_For: Osama_
_Project: muslim_companion_

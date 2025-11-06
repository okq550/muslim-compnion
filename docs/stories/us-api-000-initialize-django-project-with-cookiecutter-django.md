# Story US-API-000: Initialize Django Project with Cookiecutter Django

Status: ready-for-dev

## Story

As a **development team**,
I want to **initialize the Django project using Cookiecutter Django template**,
so that **we have a production-ready foundation with best practices and essential tooling configured**.

## Acceptance Criteria

1. ✅ Run `cookiecutter gh:cookiecutter/cookiecutter-django` with correct prompts specified in architecture document
2. ✅ Project structure created with project_slug=quran_backend
3. ✅ Docker configuration includes web, PostgreSQL, Redis, Celery services
4. ✅ `docker-compose up` builds all containers successfully
5. ✅ Database migrations apply without errors
6. ✅ Django admin interface accessible at localhost:8000/admin
7. ✅ DRF browsable API accessible at localhost:8000/api/
8. ✅ Environment variables configured in .env file
9. ✅ Git repository initialized with initial commit
10. ✅ Development documentation updated with setup instructions
11. ✅ Django internationalization (i18n) configured with Arabic (ar) and English (en) languages
12. ✅ LANGUAGE_CODE set to 'ar' (Arabic as default)
13. ✅ USE_I18N = True and USE_L10N = True in settings
14. ✅ LANGUAGES configured with both Arabic and English options
15. ✅ LocaleMiddleware included in MIDDLEWARE
16. ✅ Admin panel displays in Arabic by default with language switcher available

## Tasks / Subtasks

- [ ] **Task 1**: Initialize Cookiecutter Django Project (AC: #1, #2, #3)
  - [ ] Ensure Python 3.14 installed locally
  - [ ] Run `cookiecutter https://github.com/cookiecutter/cookiecutter-django` with specified prompts:
    - project_name: "django-muslim-companion"
    - project_slug: "quran_backend"
    - description: "Quran Backend API for Islamic Spiritual Companion App"
    - use_docker: y
    - use_drf: y
    - use_celery: y
    - cloud_provider: AWS
    - postgresql_version: 16
    - use_sentry: y
  - [ ] Verify project structure created successfully
  - [ ] Verify Docker Compose configuration includes all required services (web, db, redis, celery)

- [ ] **Task 2**: Configure Docker Environment (AC: #4, #5)
  - [ ] Create and configure .env file with development environment variables
  - [ ] Build Docker containers: `docker-compose build`
  - [ ] Start all containers: `docker-compose up`
  - [ ] Verify all services start successfully (web, PostgreSQL, Redis, Celery worker)
  - [ ] Run database migrations: `docker-compose exec web python manage.py migrate`
  - [ ] Verify migrations apply cleanly without errors

- [ ] **Task 3**: Verify Admin and API Access (AC: #6, #7)
  - [ ] Create superuser: `docker-compose exec web python manage.py createsuperuser`
  - [ ] Access Django admin at `http://localhost:8000/admin`
  - [ ] Verify admin interface loads and login works
  - [ ] Access DRF browsable API at `http://localhost:8000/api/`
  - [ ] Verify browsable API interface displays correctly

- [ ] **Task 4**: Configure Arabic Internationalization (AC: #11, #12, #13, #14, #15, #16)
  - [ ] Update `config/settings/base.py` (or equivalent settings file) with i18n configuration:
    ```python
    LANGUAGE_CODE = 'ar'  # Arabic as default language
    LANGUAGES = [
        ('ar', 'العربية'),
        ('en', 'English'),
    ]
    USE_I18N = True
    USE_L10N = True
    LOCALE_PATHS = [str(BASE_DIR / 'locale')]
    ```
  - [ ] Add 'django.middleware.locale.LocaleMiddleware' to MIDDLEWARE (after SessionMiddleware, before CommonMiddleware)
  - [ ] Create locale directory: `mkdir -p locale`
  - [ ] Generate Arabic translation files: `django-admin makemessages -l ar`
  - [ ] Compile translation files: `django-admin compilemessages`
  - [ ] Restart containers and verify admin panel displays in Arabic with RTL layout
  - [ ] Test language switcher functionality (if available)

- [ ] **Task 5**: Initialize Git Repository and Documentation (AC: #8, #9, #10)
  - [ ] Initialize git repository: `git init`
  - [ ] Add all files: `git add .`
  - [ ] Create initial commit: `git commit -m "Initial project setup with Cookiecutter Django"`
  - [ ] Update README.md with setup instructions:
    - Prerequisites (Python 3.14, Docker, Docker Compose)
    - Local development setup steps
    - Environment configuration guide
    - Running tests and migrations
    - Arabic localization setup
  - [ ] Document any environment-specific configurations in README or SETUP.md

- [ ] **Task 6**: Testing and Validation
  - [ ] Test: All Docker containers start without errors
  - [ ] Test: Database connection successful (verify via `docker-compose exec web python manage.py dbshell`)
  - [ ] Test: Redis connection successful (verify Celery worker connects)
  - [ ] Test: Admin panel accessible and displays in Arabic
  - [ ] Test: DRF browsable API accessible
  - [ ] Test: Environment variables loaded correctly
  - [ ] Test: Default pytest tests pass (if any included by Cookiecutter)
  - [ ] Verify: All acceptance criteria checked and passing

## Dev Notes

### Architecture Alignment

**Foundation Decision (ADR-001):**
This story implements the foundational architecture decision to use Cookiecutter Django as the project base. This provides ~40% setup time savings and production-ready configurations for Django 5.2.8 LTS, Docker containerization, DRF, Celery, and AWS integration.

**Technology Stack:**
- Django 5.2.8 LTS (support until April 2028)
- Python 3.14 (latest stable)
- Django REST Framework 3.16.1+ for API development
- PostgreSQL 16 for relational database
- Redis for caching and Celery message broker
- Celery + Celery Beat for background jobs
- Docker + Docker Compose for containerization
- AWS cloud provider integration (S3, CloudFront, OpenSearch, RDS, ECS)

**Arabic Localization (ADR-005):**
- Arabic set as default language (LANGUAGE_CODE='ar')
- Bilingual support for Arabic and English
- Django admin panel automatically displays in Arabic with RTL layout
- LocaleMiddleware enables language switching
- Translation files stored in `locale/` directory

**Security Configuration:**
- Sentry SDK integration for error tracking and performance monitoring
- Environment variables managed via .env file (django-environ)
- Secure defaults from Cookiecutter Django template

**Post-Initialization Customizations:**
Per Architecture Document, after Cookiecutter initialization:
1. Replace multi-file settings (config/settings/base.py, local.py, production.py) with single `config/settings.py`
2. Install django-environ for .env management
3. Configure Arabic i18n as specified above
4. Add Django apps per epic structure (done in subsequent stories)
5. Configure AWS S3, CloudFront, and OpenSearch integrations (done in subsequent stories)

### Project Structure Notes

**Expected Structure After Initialization:**
```
quran_backend/
├── config/
│   ├── settings/  (to be simplified to single settings.py later)
│   ├── urls.py
│   └── wsgi.py
├── compose/
│   ├── local/
│   └── production/
├── requirements/
│   ├── base.txt
│   ├── local.txt
│   └── production.txt
├── locale/  (to be created for i18n)
├── docker-compose.yml
├── Dockerfile
├── .env (to be created)
├── .gitignore
├── README.md
└── manage.py
```

**Notes:**
- This is a foundational story - all subsequent development depends on successful completion
- No custom Django apps created yet (handled in subsequent stories)
- No data models or API endpoints implemented yet
- Production deployment configuration deferred to deployment phase

### Testing Standards

**Testing Approach:**
- Integration testing: Verify all Docker containers start and communicate
- Manual verification: Access admin panel and DRF browsable API
- Smoke tests: Database migrations, Redis connection, Celery worker status

**Success Criteria:**
- All 16 acceptance criteria must pass
- Development team can run project locally without errors
- README documentation is clear and complete

**Estimated Effort:** 4-6 hours including setup and verification

### References

- [Source: docs/architecture.md#Project-Initialization]
- [Source: docs/tech-spec-epic-1.md#System-Architecture-Alignment]
- [Source: docs/epics.md#US-API-000]
- [Cookiecutter Django Template](https://github.com/cookiecutter/cookiecutter-django)
- [Django Internationalization Documentation](https://docs.djangoproject.com/en/5.2/topics/i18n/)

### Learnings from Previous Story

**First story in Epic 1 - no predecessor context**

This is the foundational story that establishes the project structure. All subsequent stories will build upon this base.

## Dev Agent Record

### Context Reference

- [Story Context XML](us-api-000-initialize-django-project-with-cookiecutter-django.context.xml)

### Agent Model Used

<!-- Will be filled during implementation -->

### Debug Log References

<!-- Will be filled during implementation -->

### Completion Notes List

<!-- Will be filled during implementation -->
- Files created, patterns established, architectural decisions
- Any deviations from plan
- Technical debt or future improvements noted

### File List

<!-- Will be filled during implementation -->
- NEW: [List of new files created]
- MODIFIED: [List of files modified]
- DELETED: [List of files deleted]

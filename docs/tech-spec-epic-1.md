# Epic Technical Specification: Cross-Cutting / Infrastructure Stories

Date: 2025-11-06
Author: Osama
Epic ID: epic-1
Status: Draft

---

## Overview

Epic 1 establishes the foundational infrastructure for the Muslim Companion API, providing essential cross-cutting concerns that all subsequent epics depend upon. This epic implements the production-ready foundation using Cookiecutter Django, along with critical infrastructure services including user authentication, error handling, caching, analytics, rate limiting, backup/recovery, and logging/monitoring.

The infrastructure is designed to support a global Muslim user base with zero tolerance for data errors, offline-first architecture, and respectful design principles that honor the sacred nature of Quran content. All infrastructure decisions align with the PRD's vision of becoming the world's most trusted Islamic app through uncompromising technical excellence.

## Objectives and Scope

**In Scope:**
- Initialize Django project with Cookiecutter Django template (Django 5.2.8 LTS, DRF, Celery, AWS)
- Configure Arabic internationalization (i18n) with Arabic as default language and RTL support
- Implement JWT-based user authentication and authorization
- Build comprehensive error handling with user-friendly feedback
- Establish Redis-based caching strategy for performance optimization
- Deploy analytics and usage tracking (privacy-first, anonymous data only)
- Configure rate limiting and throttling to prevent abuse
- Set up automated backup and recovery systems
- Implement structured logging and monitoring with Sentry integration

**Out of Scope:**
- Social media authentication (OAuth, SSO)
- Two-factor authentication (Phase 2)
- Real-time analytics dashboards
- Distributed caching or multi-region backups
- Custom app-specific business logic (handled in Epics 2-7)
- Production deployment and CI/CD pipelines (infrastructure setup only)

## System Architecture Alignment

This epic directly implements Architecture Decision Records (ADRs) 001-008:

**ADR-001: Cookiecutter Django Foundation**
- Provides ~40% setup time savings with production-ready Django 5.2.8 LTS foundation
- Includes Docker containerization (web, PostgreSQL 16, Redis, Celery worker)
- Pre-configured with DRF 3.16.1+ for REST API development
- AWS cloud provider integration (S3, CloudFront, OpenSearch)

**ADR-002: JWT Authentication (djangorestframework-simplejwt)**
- Stateless authentication suitable for mobile clients
- Access tokens: 30-minute lifetime
- Refresh tokens: 14-day lifetime
- Supports future multi-device sessions

**ADR-003: Redis Caching Layer**
- In-memory cache for frequently accessed static content (Quran text, reciter lists)
- Session caching for temporary user data
- Celery message broker for background tasks

**ADR-004: Error Tracking with Sentry**
- Real-time error monitoring and performance tracking
- Critical for zero-error tolerance requirement
- Release tracking and user context for debugging

**ADR-005: Arabic Internationalization (i18n)**
- Arabic (ar) as LANGUAGE_CODE default
- Bilingual support: Arabic and English
- Django admin panel in Arabic with RTL layout
- LocaleMiddleware for language switching

**Technology Stack Alignment:**
- Python 3.14 + Django 5.2.8 LTS
- PostgreSQL 16 for relational data
- Redis for caching and Celery broker
- Celery + Celery Beat for background jobs
- docker-compose for local development
- pytest for testing framework

## Detailed Design

### Services and Modules

| Service/Module | Responsibility | Inputs | Outputs | Owner |
|----------------|----------------|---------|---------|-------|
| **Authentication Service** | User registration, login, logout, password reset, JWT token management | Email, password, refresh token | Access token, refresh token, user profile | US-API-001 |
| **Authorization Middleware** | Verify JWT tokens, enforce user permissions, protect user-specific resources | JWT access token, request context | Authenticated user object or 401/403 error | US-API-001 |
| **Error Handler Middleware** | Catch exceptions, transform to user-friendly messages, log errors to Sentry | Exception objects, request context | Standardized error responses (JSON) | US-API-002 |
| **Cache Manager** | Store/retrieve cached data, invalidate on updates, manage TTL | Cache key, data object, TTL | Cached data or cache miss | US-API-003 |
| **Analytics Tracker** | Record anonymous usage events, aggregate metrics, respect opt-out preferences | Event name, metadata, user consent | Analytics data (aggregated) | US-API-004 |
| **Rate Limiter** | Track request counts per user/IP, enforce limits, provide retry-after headers | User ID/IP, endpoint, timestamp | Allow/deny decision, rate limit headers | US-API-005 |
| **Backup Service** | Automated database backups, verify integrity, manage retention policy | Database snapshots, schedule config | Backup files (encrypted), restoration capability | US-API-006 |
| **Logging Service** | Structured logging (JSON), correlation IDs, log rotation, secure storage | Log level, message, context | Searchable log entries | US-API-007 |
| **Monitoring Dashboard** | System health metrics, performance tracking, alerting on critical issues | Application metrics, logs, traces | Dashboard visualization, alerts | US-API-007 |

### Data Models and Contracts

**User Model (extends Django AbstractUser):**
```python
class User(AbstractUser):
    """Custom user model for authentication and authorization."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    is_analytics_enabled = models.BooleanField(default=False)  # User consent for analytics
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
```

**UserProfile Model:**
```python
class UserProfile(models.Model):
    """Extended user profile for preferences and settings."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    preferred_language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES, default='ar')
    timezone = models.CharField(max_length=50, default='UTC')

    # Preferences for future features
    preferred_reciter = models.ForeignKey('reciters.Reciter', null=True, blank=True, on_delete=models.SET_NULL)
    preferred_translation = models.ForeignKey('translations.Translation', null=True, blank=True, on_delete=models.SET_NULL)
```

**AnalyticsEvent Model:**
```python
class AnalyticsEvent(models.Model):
    """Anonymous usage analytics (privacy-first design)."""
    event_type = models.CharField(max_length=100)  # e.g., 'surah_viewed', 'reciter_played'
    event_data = models.JSONField()  # Flexible event metadata
    user_id_hash = models.CharField(max_length=64, null=True, blank=True)  # Hashed user ID for privacy
    session_id = models.UUIDField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['event_type', 'timestamp']),
        ]
```

**RateLimitTracker Model (Redis-backed, not Django ORM):**
```python
# Stored in Redis with TTL for automatic expiration
# Key pattern: "rate_limit:{user_id}:{endpoint}:{time_window}"
# Value: request_count (integer)
```

**Cache Schema (Redis):**
```python
# Static content cache (long TTL: 7 days)
# Key: "quran:surah:{surah_number}"
# Key: "reciters:list"
# Key: "translations:list"

# Dynamic content cache (short TTL: 1 hour)
# Key: "user:{user_id}:bookmarks"
```

### APIs and Interfaces

**Authentication Endpoints:**

```
POST /api/v1/auth/register/
Request: { "email": "user@example.com", "password": "SecurePass123!" }
Response: { "user": {...}, "tokens": { "access": "...", "refresh": "..." } }
Status: 201 Created

POST /api/v1/auth/login/
Request: { "email": "user@example.com", "password": "SecurePass123!" }
Response: { "tokens": { "access": "...", "refresh": "..." } }
Status: 200 OK

POST /api/v1/auth/logout/
Request: { "refresh": "..." }
Response: { "message": "Successfully logged out" }
Status: 200 OK

POST /api/v1/auth/token/refresh/
Request: { "refresh": "..." }
Response: { "access": "..." }
Status: 200 OK

POST /api/v1/auth/password-reset/
Request: { "email": "user@example.com" }
Response: { "message": "Password reset email sent" }
Status: 200 OK

POST /api/v1/auth/password-reset-confirm/
Request: { "token": "...", "new_password": "NewPass123!" }
Response: { "message": "Password reset successful" }
Status: 200 OK
```

**Error Response Format (standardized across all endpoints):**
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "User-friendly error message in Arabic or English",
    "details": {
      "field": "email",
      "reason": "This email is already registered"
    },
    "timestamp": "2025-11-06T12:34:56Z",
    "request_id": "correlation-id-123"
  }
}
```

**Rate Limit Headers (included in all API responses):**
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 87
X-RateLimit-Reset: 1699200000
Retry-After: 60 (only when rate limit exceeded)
```

**Analytics Event Tracking (internal API):**
```python
# Internal service call, not exposed as REST endpoint
analytics_service.track_event(
    event_type='surah_viewed',
    event_data={'surah_number': 1, 'duration_seconds': 120},
    user_id_hash=hash(user.id) if user.is_analytics_enabled else None,
    session_id=request.session.session_key
)
```

### Workflows and Sequencing

**User Registration Flow:**
1. Client submits email + password to `/api/v1/auth/register/`
2. Backend validates email format and password strength (min 8 chars, complexity requirements)
3. Check email uniqueness in database
4. Hash password using Django's PBKDF2 algorithm
5. Create User and UserProfile records
6. Generate JWT access + refresh tokens
7. Send welcome email (async via Celery)
8. Return tokens + user profile to client
9. Log registration event (anonymized)

**Authentication Flow (subsequent requests):**
1. Client includes `Authorization: Bearer {access_token}` header
2. JWT middleware extracts and validates token
3. Check token expiration (30 minutes)
4. Decode token to retrieve user_id
5. Fetch user from database (with caching)
6. Attach user object to request context
7. Proceed to view/endpoint logic
8. If token expired, return 401 with suggestion to refresh
9. Client uses refresh token to obtain new access token

**Error Handling Flow:**
1. Exception raised during request processing
2. Error Handler Middleware catches exception
3. Determine error type (validation, auth, server, network)
4. Log error to Sentry with full context (request, user, stack trace)
5. Transform exception to user-friendly message (localized to ar/en)
6. Remove sensitive technical details
7. Return standardized error response (see API format above)
8. Client displays error message appropriately

**Caching Flow (read request):**
1. Client requests resource (e.g., GET /api/v1/quran/surah/1/)
2. Check Redis cache for key "quran:surah:1"
3. **Cache HIT**: Return cached data immediately (latency < 10ms)
4. **Cache MISS**:
   - Fetch from PostgreSQL database
   - Transform to API response format
   - Store in Redis with TTL (7 days for static Quran content)
   - Return response to client
5. Monitor cache hit ratio (target > 80% for static content)

**Rate Limiting Flow:**
1. Client sends request to any public endpoint
2. Rate Limiter extracts user_id (if authenticated) or IP address
3. Construct Redis key: `rate_limit:{user_id}:{endpoint}:minute`
4. Increment counter in Redis (atomic INCR operation)
5. Set TTL to 60 seconds if key doesn't exist
6. Check if count exceeds limit (e.g., 100 req/min for authenticated users)
7. **Under Limit**: Include rate limit headers, proceed with request
8. **Over Limit**:
   - Return 429 Too Many Requests
   - Include Retry-After header
   - Log rate limit violation
   - Temporarily block if repeated violations (10+ in 1 hour)

**Backup and Recovery Flow:**
1. Celery Beat schedules daily backup task at 2:00 AM UTC
2. Backup task triggers PostgreSQL `pg_dump` command
3. Compress backup file with gzip
4. Encrypt backup with AES-256 (key from AWS KMS)
5. Upload to S3 bucket `quran-backend-backups/{date}/`
6. Verify upload integrity (checksum validation)
7. Tag backup with metadata (date, size, DB version)
8. Send success/failure notification to ops team
9. Enforce retention policy: Keep daily backups for 30 days, weekly for 90 days
10. **Recovery Process**:
    - Download backup from S3
    - Decrypt with KMS key
    - Decompress backup file
    - Restore to staging database first (validation)
    - If validation passes, restore to production
    - Verify data integrity post-restoration

## Non-Functional Requirements

### Performance

**Response Time Targets:**
- API authentication endpoints: < 500ms (p95)
- Cached data retrieval: < 100ms (p95)
- Database queries: < 200ms (p95)
- Background job execution: < 5 seconds for import tasks

**Throughput:**
- Handle 1,000 concurrent users initially
- Scale to 10,000 concurrent users by Phase 2
- Support 100,000 daily active users

**Caching Efficiency:**
- Cache hit ratio > 80% for static content (Quran text, reciter lists)
- Cache hit ratio > 60% for dynamic content (user bookmarks)

**Monitoring:**
- Track all performance metrics via Sentry Performance Monitoring
- Alert if p95 latency exceeds thresholds by 50%

### Security

**Authentication & Authorization:**
- JWT tokens with industry-standard expiration (30min access, 14d refresh)
- HTTPS-only communication (enforce in production)
- Password hashing: PBKDF2 with 320,000 iterations (Django default)
- Rate limiting on auth endpoints: 5 login attempts per 15 minutes per IP
- Account lockout after 10 failed login attempts in 1 hour

**Data Protection:**
- No plaintext passwords stored anywhere
- Backup encryption with AES-256 (AWS KMS key management)
- No sensitive user data in logs (passwords, tokens, PII)
- GDPR compliance for analytics (anonymous data, opt-out option)

**API Security:**
- CSRF protection disabled for API endpoints (token-based auth)
- CORS configured for approved frontend domains only
- SQL injection protection via Django ORM parameterized queries
- XSS protection via DRF serialization (no raw HTML rendering)

**Threat Mitigation:**
- Rate limiting prevents brute-force attacks
- Logging captures all authentication failures
- Sentry alerts on unusual error patterns

### Reliability/Availability

**Uptime Target:**
- 99.9% availability (43 minutes downtime per month maximum)

**Database:**
- PostgreSQL RDS with Multi-AZ deployment (automatic failover)
- Daily automated backups with 30-day retention
- Point-in-time recovery capability (5-minute granularity)

**Redis:**
- ElastiCache Redis cluster with replication
- Automatic failover to standby node
- Cache misses handled gracefully (fetch from DB)

**Error Recovery:**
- Automatic retry for transient errors (exponential backoff)
- Graceful degradation when cache unavailable (serve from DB)
- Celery task retries: 3 attempts with exponential backoff

**Monitoring & Alerting:**
- Sentry real-time error tracking with PagerDuty integration
- Alert on critical errors within 1 minute
- Health check endpoint: `/api/v1/health/` (monitors DB, Redis, Celery)

### Observability

**Structured Logging:**
- JSON format for all logs (parseable by log aggregation tools)
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Correlation IDs for request tracing across services
- No sensitive data logged (enforce via code review + automated scanning)

**Logging Scope:**
- Application errors and exceptions (all ERROR/CRITICAL logs → Sentry)
- Authentication events (login, logout, password reset, failures)
- Rate limit violations
- Cache performance (hit/miss ratio)
- Background job execution (start, success, failure)

**Monitoring Metrics (Sentry + CloudWatch):**
- Request rate per endpoint
- Response time distribution (p50, p95, p99)
- Error rate by error type
- Cache hit/miss ratio
- Database connection pool utilization
- Celery queue depth and processing time
- Memory and CPU utilization

**Alerts:**
- Error rate > 5% in 5-minute window → PagerDuty alert
- API response time p95 > 1 second → Warning
- Database connections > 80% capacity → Warning
- Backup failure → Critical alert
- Rate limit abuse (100+ violations in 1 hour) → Warning

**Dashboard:**
- Real-time system health overview (all metrics visible)
- Historical trends for capacity planning
- User activity metrics (DAU, session duration)

## Dependencies and Integrations

**External Services:**
- **AWS S3**: Audio file storage (configured in future epics, prepared in infrastructure)
- **AWS CloudFront**: CDN for audio delivery (configured in future epics)
- **AWS OpenSearch**: Quran text search (configured in future epics)
- **AWS SES**: Email delivery for password reset, notifications
- **Sentry**: Error tracking and performance monitoring (sentry-sdk==1.40.0)
- **AWS KMS**: Encryption key management for backups

**Python Libraries:**
```python
# Core Framework
Django==5.2.8
djangorestframework==3.16.1
djangorestframework-simplejwt==5.3.1

# Configuration
django-environ==0.11.2

# Database
psycopg2-binary==2.9.9

# Caching & Background Jobs
django-redis==5.4.0
celery==5.3.6

# AWS Integration
django-storages[s3]==1.14.2
boto3==1.34.0

# Monitoring
sentry-sdk==1.40.0

# Server
gunicorn==21.2.0

# Testing
pytest-django==4.7.0
pytest-cov==4.1.0
```

**Internal Dependencies:**
- This epic has no dependencies on other epics (foundational)
- All subsequent epics (2-7) depend on Epic 1 for authentication, error handling, logging

**Dependency Constraints:**
- Django 5.2.8 LTS (support until April 2028)
- Python 3.14 (latest stable)
- PostgreSQL 16 (maintained until 2028)
- DRF 3.16.1+ (compatible with Django 5.2)

## Acceptance Criteria (Authoritative)

**US-API-000: Initialize Django Project**
1. Cookiecutter Django project created with project_slug=muslim_companion
2. Docker containers (web, PostgreSQL, Redis, Celery) build and run successfully
3. Database migrations apply without errors
4. Django admin accessible at localhost:8000/admin with Arabic RTL layout
5. DRF browsable API accessible at localhost:8000/api/
6. Environment variables configured in .env file
7. Git repository initialized with initial commit
8. Arabic i18n configured (LANGUAGE_CODE='ar', LocaleMiddleware)

**US-API-001: User Authentication**
9. User can register with email and password via `/api/v1/auth/register/`
10. User can login and receive JWT access + refresh tokens
11. User can logout (invalidate refresh token)
12. User can reset forgotten password via email
13. Passwords meet security requirements (min 8 chars, complexity)
14. JWT access tokens expire after 30 minutes
15. JWT refresh tokens expire after 14 days
16. Users can only access their own data (authorization enforced)
17. Failed login attempts limited (5 per 15 minutes)

**US-API-002: Error Handling**
18. Network errors return user-friendly messages (not stack traces)
19. Server errors logged to Sentry but don't expose technical details to users
20. Validation errors explain what needs correction
21. All error responses follow standardized JSON format
22. Transient errors trigger automatic retry (exponential backoff)
23. User's data preserved during errors (no partial state updates)
24. Error messages localized to Arabic or English based on user preference

**US-API-003: Caching**
25. Frequently accessed static content cached (Quran text, reciter lists)
26. Cache hit ratio > 80% for static content after warmup
27. Cached data served in < 100ms (p95)
28. Cache automatically invalidated when content updates
29. Cache size doesn't exceed 500MB per instance
30. App works with stale cache during temporary Redis outage

**US-API-004: Analytics**
31. System tracks feature usage events anonymously
32. User can opt-out of analytics via profile setting
33. No personally identifiable information collected in analytics
34. Analytics consent requested on first app use
35. Privacy policy explains data collection clearly

**US-API-005: Rate Limiting**
36. Rate limits enforced on all public endpoints
37. Authenticated users: 100 requests per minute per endpoint
38. Anonymous users: 20 requests per minute per endpoint
39. Rate limit headers included in responses (X-RateLimit-*)
40. 429 status code returned when limit exceeded with Retry-After header
41. Legitimate users not unfairly blocked (no false positives)

**US-API-006: Backup and Recovery**
42. Automated daily backups run at 2:00 AM UTC
43. All critical data included (user data, content, config)
44. Backups encrypted with AES-256 and stored in S3
45. Backup integrity verified after each backup (checksum validation)
46. Recovery tested successfully (restore from backup to staging)
47. Backup failures trigger immediate alerts
48. Retention policy enforced (30 days daily, 90 days weekly)

**US-API-007: Logging and Monitoring**
49. All critical events logged (errors, auth events, rate limits)
50. Logs structured in JSON format with correlation IDs
51. No sensitive data in logs (passwords, tokens)
52. Logs rotated and retained for 90 days
53. System health monitored continuously (DB, Redis, Celery status)
54. Alerts triggered on critical issues (error rate, performance, backup failure)
55. Monitoring dashboard provides real-time visibility

## Traceability Mapping

| AC # | Spec Section | Component/API | Test Idea |
|------|--------------|---------------|-----------|
| 1-8 | Project Initialization | Cookiecutter Django setup, Docker Compose | Integration test: Verify all containers start, admin accessible, i18n configured |
| 9-17 | Authentication & Authorization | AuthenticationService, JWT middleware, `/api/v1/auth/*` endpoints | Unit tests: Registration, login, logout, token refresh. Integration: End-to-end auth flow |
| 18-24 | Error Handling | ErrorHandlerMiddleware, Sentry integration | Unit tests: Exception transformation. Integration: Trigger various errors, verify responses |
| 25-30 | Caching | CacheManager, Redis integration | Unit tests: Cache hit/miss logic. Load test: Measure cache performance under load |
| 31-35 | Analytics | AnalyticsTracker, AnalyticsEvent model | Unit tests: Event tracking, opt-out. Privacy audit: Verify no PII collected |
| 36-41 | Rate Limiting | RateLimiter, Redis counters | Unit tests: Limit enforcement. Load test: Exceed limits, verify 429 responses |
| 42-48 | Backup & Recovery | BackupService, Celery scheduled task | Integration test: Run backup, restore to staging, verify data integrity |
| 49-55 | Logging & Monitoring | LoggingService, Sentry SDK, CloudWatch | Unit tests: Log formatting. Integration: Trigger alerts, verify dashboard metrics |

## Risks, Assumptions, Open Questions

**Risks:**
1. **Risk**: Arabic RTL layout issues in Django admin
   - **Mitigation**: Django has built-in Arabic translations; test thoroughly with real Arabic data

2. **Risk**: JWT token security if refresh tokens compromised
   - **Mitigation**: Short-lived access tokens (30min), secure refresh token storage, monitor for unusual token usage patterns

3. **Risk**: Cache invalidation bugs causing stale data
   - **Mitigation**: Aggressive testing of cache invalidation logic, monitoring cache hit/miss ratios, manual cache clear option

4. **Risk**: Rate limiting false positives (blocking legitimate users)
   - **Mitigation**: Conservative initial limits (100 req/min), monitor violation logs, whitelist option for support escalation

5. **Risk**: Backup recovery not tested regularly
   - **Mitigation**: Quarterly disaster recovery drills, automated recovery testing in staging environment

6. **Risk**: Sentry costs exceed budget with high error volume
   - **Mitigation**: Error sampling configuration, alert thresholds to catch runaway errors early

**Assumptions:**
1. Users have stable internet connectivity for initial registration (offline mode after setup)
2. Email delivery via AWS SES is reliable (99.9% delivery rate)
3. Redis availability is high (ElastiCache SLA: 99.9%)
4. Cookiecutter Django template remains stable and maintained
5. Arabic language support in Django admin is production-ready

**Open Questions:**
1. **Question**: Should we support phone number authentication in addition to email?
   - **Resolution Needed By**: Before Phase 2 planning
   - **Assigned To**: Product team for user research

2. **Question**: What's the retention policy for analytics data?
   - **Resolution Needed By**: Before analytics implementation
   - **Assigned To**: Legal/compliance team for GDPR review

3. **Question**: Should rate limits differ by endpoint type (read vs write)?
   - **Resolution Needed By**: Before final rate limit configuration
   - **Assigned To**: Architecture team based on load testing results

4. **Question**: Do we need multi-region backups for disaster recovery?
   - **Resolution Needed By**: Before production deployment
   - **Assigned To**: Infrastructure team for RTO/RPO analysis

## Test Strategy Summary

**Testing Approach:**
- **Unit Tests**: All services, middleware, utilities tested in isolation (pytest)
- **Integration Tests**: End-to-end flows for authentication, caching, error handling
- **Load Tests**: Rate limiting, caching performance, database connection pooling (Locust)
- **Security Tests**: Authentication bypass attempts, injection attacks, rate limit evasion
- **Disaster Recovery Tests**: Backup restoration, failover scenarios (quarterly drills)

**Test Coverage Goals:**
- Unit test coverage: > 90% for all Epic 1 code
- Integration test coverage: All critical user flows (auth, error handling)
- Load testing: Sustained 1,000 concurrent users without degradation

**Test Environments:**
- **Local Development**: Docker Compose with all services
- **CI/CD Pipeline**: Automated test suite on every commit (GitHub Actions)
- **Staging**: Production-like environment for integration and load testing
- **Production**: Monitored with Sentry, canary deployments for risk mitigation

**Key Test Scenarios:**
1. **Happy Path**: User registration → login → authenticated request → logout
2. **Error Scenarios**: Invalid credentials, expired tokens, network failures, server errors
3. **Rate Limiting**: Gradual increase to limit, exceeding limit, retry after cooldown
4. **Caching**: Cache hit, cache miss, cache invalidation, cache unavailability
5. **Backup & Recovery**: Full backup, selective restore, corruption recovery
6. **Security**: SQL injection attempts, XSS attacks, brute-force login attempts

**Acceptance Testing:**
- Product Owner review of error messages (user-friendliness, localization)
- Security audit of authentication flow
- Performance benchmarking against NFR targets
- Disaster recovery drill with stakeholder observation

**Test Data:**
- Synthetic user accounts (valid and invalid credentials)
- Arabic and English text for i18n validation
- Large dataset for cache performance testing
- Corrupted data for error handling validation

**Test Automation:**
- Pytest for unit and integration tests (pytest-django)
- Coverage reporting via pytest-cov
- Pre-commit hooks for code quality (black, flake8, mypy)
- CI/CD pipeline runs full test suite on pull requests

---

**Document Status**: Ready for Review
**Next Steps**:
1. Product Owner approval of acceptance criteria
2. Security team review of authentication and error handling design
3. Infrastructure team confirmation of AWS service configuration
4. Development team to begin US-API-000 (project initialization)

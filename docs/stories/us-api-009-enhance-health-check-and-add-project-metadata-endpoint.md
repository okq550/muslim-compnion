# Story 1.9: Implement Granular Health Checks and Project Metadata Endpoint

Status: backlog

## Story

As a **DevOps engineer and monitoring system**,
I want **granular health check endpoints (liveness, readiness, resource-specific) and project metadata API**,
so that **I can efficiently monitor application health for Kubernetes orchestration and retrieve project information programmatically**.

## Background

This story implements a granular health check architecture following Kubernetes liveness/readiness probe best practices, and adds a project metadata endpoint for API discovery. Instead of a single monolithic health check, we create 5 specialized endpoints:

1. **`/health/check`** - Liveness probe (server alive, no resource checks)
2. **`/health/ready`** - Readiness probe (all resources checked, production traffic ready)
3. **`/health/db`** - Database-specific health check
4. **`/health/cache`** - Redis cache-specific health check
5. **`/health/disk`** - Disk space-specific health check

This granular approach enables:
- **Faster liveness checks** (< 10ms) for container orchestration
- **Comprehensive readiness checks** (< 1s) for production traffic routing
- **Targeted troubleshooting** with resource-specific endpoints
- **Independent monitoring** of each infrastructure component

The metadata endpoint (`/api/meta/`) enables programmatic API discovery, returning project name, version, environment, and build timestamp. This supports versioning strategies, environment awareness, and automated integration testing.

**Parent Epic**: EPIC 1 - Cross-Cutting / Infrastructure Stories
**Priority**: P1 (Medium - Infrastructure Enhancement)
**Functional Requirement**: FR-041 (Monitoring & Operations)
**Dependencies**:
- US-API-007 (Logging and Monitoring - health check foundation)
- US-API-008 (API Documentation - for documenting new endpoints)
**Effort**: Small-Medium (3-4 hours)

## Acceptance Criteria

### Health Check Endpoints - Kubernetes Liveness/Readiness Pattern (AC #1-6)

1. **`/health/check` - Liveness Probe (Simple Availability Check)**
   - **Purpose**: Kubernetes liveness probe - checks if server is alive and accepting requests
   - **Behavior**: Minimal check with no resource dependencies
   - **Response**: Immediate return with no external calls
   - **Format**:
     ```json
     {
       "status": "ok",
       "timestamp": "2025-11-16T10:30:00Z"
     }
     ```
   - **Status Codes**:
     - 200 OK: Server is alive and accepting requests
     - 500 Internal Server Error: Only if server process is critically failing
   - **Response Time**: < 10ms (no I/O operations)
   - **Use Case**: Kubernetes liveness probe, load balancer health check

2. **`/health/ready` - Readiness Probe (Full Resource Check)**
   - **Purpose**: Kubernetes readiness probe - checks if server is ready to handle traffic
   - **Behavior**: Checks ALL critical resources (database, cache, Celery)
   - **Response**: Returns detailed status of all components
   - **Format**:
     ```json
     {
       "status": "ready",
       "timestamp": "2025-11-16T10:30:00Z",
       "version": "1.0.0",
       "environment": "production",
       "components": {
         "database": {
           "status": "up",
           "response_time_ms": 15,
           "connection_pool": "8/20 active"
         },
         "cache": {
           "status": "up",
           "response_time_ms": 2,
           "memory_used_mb": 45,
           "keys": 1250
         },
         "celery": {
           "status": "up",
           "workers": 2,
           "active_tasks": 3,
           "queue_depth": 12
         },
         "disk": {
           "status": "ok",
           "free_percent": 45,
           "free_gb": 120
         }
       }
     }
     ```
   - **Status Codes**:
     - 200 OK: All components healthy, ready to serve traffic
     - 503 Service Unavailable: One or more critical components unhealthy
   - **Response Time**: < 1000ms (includes all resource checks)
   - **Use Case**: Kubernetes readiness probe, detailed monitoring

3. **`/health/db` - Database-Specific Health Check**
   - **Purpose**: Isolated database connectivity and performance check
   - **Behavior**: Checks PostgreSQL connection, query execution, connection pool
   - **Format**:
     ```json
     {
       "status": "ok",
       "timestamp": "2025-11-16T10:30:00Z",
       "resource": "database",
       "details": {
         "connection": "active",
         "response_time_ms": 15,
         "connection_pool": {
           "active": 8,
           "total": 20,
           "idle": 12
         },
         "last_query_ms": 12
       }
     }
     ```
   - **Status Codes**:
     - 200 OK: Database accessible and responsive
     - 503 Service Unavailable: Database down or query timeout
   - **Response Time**: < 200ms
   - **Use Case**: Database-specific monitoring, troubleshooting

4. **`/health/cache` - Redis Cache Health Check**
   - **Purpose**: Isolated Redis cache connectivity and performance check
   - **Behavior**: Checks Redis connection, memory usage, key operations
   - **Format**:
     ```json
     {
       "status": "ok",
       "timestamp": "2025-11-16T10:30:00Z",
       "resource": "cache",
       "details": {
         "connection": "active",
         "response_time_ms": 2,
         "memory_used_mb": 45,
         "memory_max_mb": 500,
         "keys": 1250,
         "eviction_policy": "allkeys-lru"
       }
     }
     ```
   - **Status Codes**:
     - 200 OK: Redis accessible and responsive
     - 503 Service Unavailable: Redis down or timeout
   - **Response Time**: < 50ms
   - **Use Case**: Cache-specific monitoring, cache performance tracking

5. **`/health/disk` - Disk Space Health Check**
   - **Purpose**: Isolated disk space availability check
   - **Behavior**: Checks available disk space and warns on low space
   - **Format**:
     ```json
     {
       "status": "ok",
       "timestamp": "2025-11-16T10:30:00Z",
       "resource": "disk",
       "details": {
         "free_percent": 45,
         "free_gb": 120,
         "total_gb": 267,
         "mount_point": "/",
         "warning_threshold": 20,
         "critical_threshold": 10
       }
     }
     ```
   - **Status Codes**:
     - 200 OK: Sufficient disk space available (> 20%)
     - 503 Service Unavailable: Critical low disk space (< 10%)
   - **Response Time**: < 50ms
   - **Use Case**: Disk monitoring, capacity planning alerts

6. **Response Time and Performance Requirements**
   - `/health/check`: < 10ms (no external calls)
   - `/health/ready`: < 1000ms (aggregates all checks)
   - `/health/db`: < 200ms
   - `/health/cache`: < 50ms
   - `/health/disk`: < 50ms
   - All endpoints measure and report response times
   - Log slow checks (> 500ms) as warnings
   - Timeout protection on all external resource checks

### Project Metadata Endpoint (AC #7-8)

7. **New `/api/meta/` Endpoint Returns Project Metadata**
   - Create new public endpoint at `/api/meta/`
   - No authentication required (publicly accessible)
   - Return project metadata in JSON format:
     ```json
     {
       "project": {
         "name": "Muslim Companion API",
         "version": "1.0.0",
         "api_version": "v1",
         "environment": "production",
         "build_timestamp": "2025-11-16T08:00:00Z",
         "documentation_url": "/api/docs/"
       }
     }
     ```
   - Version read from `pyproject.toml` or environment variable `APP_VERSION`
   - Environment from Django settings (`ENVIRONMENT` setting)
   - Build timestamp from deployment or environment variable

8. **Metadata Endpoint Cached for 24 Hours**
   - Use Redis cache for metadata response
   - Cache key: `api:metadata:v1`
   - TTL: 24 hours (86400 seconds)
   - Cache warming on application startup
   - Graceful degradation if Redis unavailable (compute on each request)

### Documentation and Testing (AC #9-11)

9. **All Health Endpoints Documented in OpenAPI Spec**
   - Add schema for all 5 health endpoints:
     - `/health/check` - Liveness probe
     - `/health/ready` - Readiness probe
     - `/health/db` - Database check
     - `/health/cache` - Redis check
     - `/health/disk` - Disk space check
   - Add `/api/meta/` schema to OpenAPI specification
   - Include example responses for all endpoints (success and failure)
   - Document response fields, status codes, and use cases
   - Update Swagger UI and ReDoc documentation

10. **Integration Tests Cover All Endpoints**
    - Liveness probe tests:
      - Test `/health/check` returns 200 OK instantly
      - Test response time < 10ms
    - Readiness probe tests:
      - Test `/health/ready` with all components healthy (200)
      - Test `/health/ready` with database down (503)
      - Test `/health/ready` with Redis down (503)
      - Test response time < 1s
    - Resource-specific tests:
      - Test `/health/db` success and failure scenarios
      - Test `/health/cache` success and failure scenarios
      - Test `/health/disk` with sufficient and low space scenarios
    - Metadata tests:
      - Test `/api/meta/` response structure
      - Test metadata caching behavior
      - Test metadata with Redis down (no cache)

11. **Monitoring Alerts Configured**
    - Alert when `/health/ready` returns 503 (critical component down)
    - Alert when any health endpoint response time exceeds threshold
    - Alert when disk space < 10% (critical)
    - Integrate with existing Sentry alerting from US-API-007
    - Log all health check failures with structured logging

## Tasks / Subtasks

### Task 1: Implement Liveness Probe - `/health/check` (AC #1)

- [ ] Create `muslim_companion/core/views/health.py` module
- [ ] Implement `LivenessCheckView(APIView)`:
  - [ ] No authentication required (`permission_classes = [AllowAny]`)
  - [ ] GET method returns minimal response
  - [ ] No external resource checks (database, Redis, etc.)
  - [ ] Response format: `{"status": "ok", "timestamp": "..."}`
  - [ ] Always returns 200 OK unless server critically failing
  - [ ] Response time < 10ms
- [ ] Add route to `config/urls.py`: `/health/check`
- [ ] Exclude from rate limiting
- [ ] Test response time < 10ms (no I/O operations)

### Task 2: Implement Readiness Probe - `/health/ready` (AC #2, #6)

- [ ] Implement `ReadinessCheckView(APIView)` in `core/views/health.py`:
  - [ ] No authentication required
  - [ ] Check ALL critical resources (database, cache, Celery, disk)
  - [ ] Aggregate component statuses
  - [ ] Return detailed status for each component
- [ ] Implement component check functions with timing:
  - [ ] `check_database()` - PostgreSQL connectivity, connection pool
  - [ ] `check_cache()` - Redis connectivity, memory, keys
  - [ ] `check_celery()` - Worker count, queue depth
  - [ ] `check_disk()` - Disk space percentage
- [ ] Measure response time for each component check
- [ ] Add version and environment to response
- [ ] Status logic:
  - [ ] 200 OK if all components healthy
  - [ ] 503 Service Unavailable if any critical component unhealthy
- [ ] Total response time < 1000ms
- [ ] Add timeout protection (800ms max per component)
- [ ] Log slow component checks (> 500ms)
- [ ] Add route to `config/urls.py`: `/health/ready`

### Task 3: Implement Resource-Specific Health Checks (AC #3, #4, #5)

- [ ] Implement `DatabaseHealthView(APIView)`:
  - [ ] Check PostgreSQL connection
  - [ ] Execute test query: `SELECT 1`
  - [ ] Return connection pool details (active, total, idle)
  - [ ] Measure query response time
  - [ ] 200 OK if accessible, 503 if down/timeout
  - [ ] Response time < 200ms
  - [ ] Add route: `/health/db`
- [ ] Implement `CacheHealthView(APIView)`:
  - [ ] Check Redis connection
  - [ ] Test SET and GET operations
  - [ ] Return memory usage, key count, eviction policy
  - [ ] Measure operation response time
  - [ ] 200 OK if accessible, 503 if down/timeout
  - [ ] Response time < 50ms
  - [ ] Add route: `/health/cache`
- [ ] Implement `DiskHealthView(APIView)`:
  - [ ] Check disk space using `shutil.disk_usage()`
  - [ ] Calculate free percentage and GB
  - [ ] Warning threshold: 20%, critical threshold: 10%
  - [ ] Return mount point, total, free, thresholds
  - [ ] 200 OK if > 20%, 503 if < 10%
  - [ ] Response time < 50ms
  - [ ] Add route: `/health/disk`

### Task 4: Create Project Metadata Endpoint (AC #7, #8)

- [ ] Implement `ProjectMetadataView(APIView)` in `core/views.py`:
  - [ ] No authentication required (`permission_classes = [AllowAny]`)
  - [ ] GET method returns project metadata
  - [ ] Read version from `pyproject.toml` using `importlib.metadata`
  - [ ] Fallback to environment variable `APP_VERSION`
  - [ ] Read environment from `settings.ENVIRONMENT`
  - [ ] Read build timestamp from env var `BUILD_TIMESTAMP`
- [ ] Implement Redis caching:
  - [ ] Cache key: `api:metadata:v1`
  - [ ] TTL: 86400 seconds (24 hours)
  - [ ] Try cache first, compute on miss
  - [ ] Cache warming in `CoreConfig.ready()` method
  - [ ] Graceful degradation if Redis down
- [ ] Add route to `config/urls.py`: `/api/meta/`
- [ ] Exclude from rate limiting

### Task 5: Update OpenAPI Documentation (AC #9)

- [ ] Add schemas for all 5 health endpoints in OpenAPI spec:
  - [ ] `/health/check` - Liveness probe schema
  - [ ] `/health/ready` - Readiness probe schema
  - [ ] `/health/db` - Database check schema
  - [ ] `/health/cache` - Cache check schema
  - [ ] `/health/disk` - Disk check schema
  - [ ] Include example responses (200 success, 503 failure) for each
  - [ ] Document response fields and use cases
- [ ] Add schema for `/api/meta/` endpoint:
  - [ ] Document metadata response structure
  - [ ] Add example response
  - [ ] Mark as public endpoint (no auth required)
- [ ] Update Swagger UI and ReDoc documentation
- [ ] Verify documentation accuracy with manual testing

### Task 6: Write Integration Tests (AC #10)

- [ ] Create `muslim_companion/core/tests/test_health_liveness.py`:
  - [ ] Test `/health/check` returns 200 OK
  - [ ] Test response time < 10ms
  - [ ] Test response format (status, timestamp)
- [ ] Create `muslim_companion/core/tests/test_health_readiness.py`:
  - [ ] Test `/health/ready` with all components healthy (200)
  - [ ] Test `/health/ready` with database down (503)
  - [ ] Test `/health/ready` with Redis down (503)
  - [ ] Test `/health/ready` response time < 1s
  - [ ] Test component details in response
- [ ] Create `muslim_companion/core/tests/test_health_resources.py`:
  - [ ] Test `/health/db` success and failure scenarios
  - [ ] Test `/health/cache` success and failure scenarios
  - [ ] Test `/health/disk` with sufficient space (200)
  - [ ] Test `/health/disk` with low space (503)
  - [ ] Test response time requirements for each endpoint
- [ ] Create `muslim_companion/core/tests/test_metadata.py`:
  - [ ] Test `/api/meta/` response structure
  - [ ] Test version field populated correctly
  - [ ] Test environment field populated correctly
  - [ ] Test metadata caching behavior (Redis)
  - [ ] Test metadata endpoint with Redis down (no cache)
  - [ ] Test metadata endpoint is publicly accessible (no auth)

### Task 7: Configure Monitoring and Alerts (AC #11)

- [ ] Add Sentry monitoring for health check failures:
  - [ ] Alert when `/health/ready` returns 503 (component down)
  - [ ] Alert when any health endpoint exceeds response time threshold
  - [ ] Alert when disk space < 10% (critical)
- [ ] Add structured logging for all health checks:
  - [ ] Log component status changes (healthy → unhealthy)
  - [ ] Log slow component checks (> 500ms)
  - [ ] Include correlation IDs for debugging
  - [ ] Log resource-specific failures with details
- [ ] Update monitoring documentation
- [ ] Test alert delivery (Sentry integration)

## Out of Scope

- Detailed performance metrics dashboard (beyond Sentry)
- Historical health data storage and trending
- Component-level restart/recovery automation
- Multi-region health aggregation
- Prometheus metrics export format
- Custom metrics beyond component health

## Definition of Done

- [ ] All acceptance criteria tested and passing
- [ ] Health check endpoint enhanced with component details and response times
- [ ] Project metadata endpoint implemented at `/api/meta/`
- [ ] Metadata response cached in Redis (24-hour TTL)
- [ ] OpenAPI documentation updated for both endpoints
- [ ] Integration tests written and passing (100% coverage)
- [ ] Health check response time < 1s verified under load
- [ ] Monitoring alerts configured and tested
- [ ] Code reviewed and approved
- [ ] Merged to main branch
- [ ] Deployed to staging and verified
- [ ] Ready for production deployment

## Dev Notes

### Architecture Alignment

**Source**: `docs/architecture.md` - Infrastructure & Operations

This story extends the health monitoring infrastructure (Section 6.5) and adds operational visibility through the metadata endpoint.

### Technical Context

**From US-API-007** (Logging and Monitoring):
- Health check foundation at `muslim_companion/core/health.py`
- Existing component checks: database, Redis, Celery, disk
- Sentry integration for alerts and monitoring
- Structured logging with correlation IDs

**From US-API-002** (Error Handling):
- Standard error response format
- Exception handling patterns
- Graceful degradation strategies

### Key Implementation Details

1. **Endpoint Architecture**:
   - **Liveness (`/health/check`)**: No external calls, instant response
   - **Readiness (`/health/ready`)**: Aggregates all component checks
   - **Resource-specific**: Isolated checks for targeted monitoring
   - All endpoints return JSON with consistent structure

2. **Component Check Functions**:
   - Create reusable check functions in `core/health.py`:
     - `check_database()` - Returns status, response_time, connection_pool
     - `check_cache()` - Returns status, response_time, memory, keys
     - `check_celery()` - Returns status, workers, queue_depth
     - `check_disk()` - Returns status, free_percent, free_gb
   - Each function returns standardized dict with status and details
   - Readiness endpoint aggregates these functions

3. **Response Time Measurement**:
   - Use `time.perf_counter()` for high-precision timing
   - Measure start/end of each component check
   - Convert to milliseconds (ms) for reporting
   - Example:
     ```python
     start = time.perf_counter()
     result = check_database()
     response_time_ms = (time.perf_counter() - start) * 1000
     ```

4. **Version Reading (Metadata Endpoint)**:
   - Primary: `importlib.metadata.version('muslim-companion')`
   - Fallback: Environment variable `APP_VERSION`
   - Last resort: "unknown"

5. **Caching Strategy (Metadata Endpoint)**:
   - Use existing Redis cache from US-API-003
   - Cache key: `api:metadata:v1` (versioned for cache busting)
   - Cache warming in `CoreConfig.ready()` method
   - Graceful degradation if Redis unavailable

6. **Status Code Strategy**:
   - Liveness: Always 200 OK (unless server critically failing)
   - Readiness: 200 if all healthy, 503 if any component down
   - Resource-specific: 200 if resource healthy, 503 if down/degraded
   - Disk: 503 only if < 10% free (critical threshold)

### File Modifications Expected

**New Files**:
- `muslim_companion/core/views/health.py` - All 5 health check view classes
- `muslim_companion/core/tests/test_health_liveness.py` - Liveness probe tests
- `muslim_companion/core/tests/test_health_readiness.py` - Readiness probe tests
- `muslim_companion/core/tests/test_health_resources.py` - Resource-specific tests

**Modified Files**:
- `muslim_companion/core/health.py` - Add reusable component check functions
- `muslim_companion/core/views.py` - Add metadata view
- `muslim_companion/core/apps.py` - Cache warming in ready()
- `config/urls.py` - Add 6 new routes (5 health + 1 metadata)
- `config/settings/base.py` - Add `ENVIRONMENT` setting if not exists
- OpenAPI schema files - Document all 6 new endpoints
- `muslim_companion/core/tests/test_metadata.py` - Metadata endpoint tests

### Testing Strategy

**Unit Tests**:
- Component check response time measurement
- Metadata version reading logic
- Cache key generation and TTL

**Integration Tests**:
- Full health check with all components
- Health check with individual components down
- Metadata endpoint caching behavior
- Response format validation

**Performance Tests**:
- Health check response time < 1s
- Component check timeout protection
- Load testing (100 req/s sustained)

### Dependencies

**Existing**:
- Django REST Framework (views, serializers)
- Redis (metadata caching)
- Sentry (monitoring and alerts)
- python-json-logger (structured logging)

**New**:
- `importlib.metadata` (standard library, Python 3.8+)
- No additional packages required

## Change Log

- 2025-11-16: Initial story created by Scrum Master (Bob)
- 2025-11-16: Architecture updated to granular health checks (liveness/readiness/resource-specific pattern) per user feedback
  - Changed from single `/health/` endpoint to 5 specialized endpoints
  - Added `/health/check` (liveness), `/health/ready` (readiness), `/health/db`, `/health/cache`, `/health/disk`
  - Follows Kubernetes probe best practices
- 2025-11-16: Updated directory references from `quran_backend` to `muslim_companion` (project renamed)
- Status: drafted → ready for review and development

## Dev Agent Record

### Completion Notes

<!-- Developer will fill this in during/after implementation -->

### Debug Log References

<!-- Links to specific log entries, errors encountered, solutions applied -->

### File List

**New Files**:
<!-- List files created (NEW) -->

**Modified Files**:
<!-- List files changed (MODIFIED) -->

**Deleted Files**:
<!-- List files removed (DELETED) -->

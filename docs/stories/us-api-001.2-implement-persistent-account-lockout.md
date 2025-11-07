# Story 1.1.2: Implement Persistent Account Lockout

Status: done

## Story

As a **Quran app user**,
I want **my account to be temporarily locked after multiple failed login attempts**,
so that **my account is protected from brute force attacks even across different IPs or sessions**.

## Background

This story addresses Acceptance Criterion #12 from US-API-001 which was partially implemented. The current implementation provides basic rate limiting (5 requests/min per IP), but lacks persistent account-level lockout tracking:

**Current Gap**: AC #12 requires "Account lockout after 10 failed login attempts in 1 hour"
**Current Implementation**: IP-based throttling (5 requests/min)
**Missing**: Persistent, account-level lockout that tracks failed attempts in Redis

**Parent Story**: US-API-001 - Implement User Authentication and Authorization
**Priority**: P1 - High (security requirement)
**Effort**: Medium (4-6 hours)

## Acceptance Criteria

1. **Failed Login Tracking**
   - Track failed login attempts per user email (not per IP)
   - Store attempt count and timestamp in Redis with TTL of 1 hour
   - Increment counter on each failed login attempt
   - Reset counter to 0 on successful login

2. **Account Lockout Mechanism**
   - Lock account after 10 failed attempts within 1 hour window
   - Lockout duration: 1 hour from last failed attempt
   - Store lockout status in Redis with expiration
   - Return 423 Locked status code when account is locked

3. **Lockout Response**
   - HTTP 423 Locked status for locked accounts
   - Error message: "Account temporarily locked due to multiple failed login attempts. Try again in X minutes."
   - Include `retry_after` field with seconds until unlock
   - Standardized error format (matches existing error handler)

4. **Lockout Bypass for Admins**
   - Superusers/staff can reset lockout via Django admin
   - Django admin action: "Clear failed login attempts"
   - Command: `python manage.py clear_lockouts --email user@example.com`

5. **Security Logging**
   - Log failed login attempts with email and IP
   - Log account lockouts with email, IP, and attempt count
   - Use Django's logging framework (integrates with Sentry)
   - Log level: WARNING for lockouts, INFO for failed attempts

6. **Testing**
   - Test: 9 failed attempts → no lockout (can still login)
   - Test: 10 failed attempts → account locked (423 status)
   - Test: Locked account cannot login even with correct password
   - Test: Successful login resets attempt counter
   - Test: Lockout expires after 1 hour
   - Test: Different users tracked independently
   - Test: Attempt counter resets on successful login

7. **Redis Integration**
   - Use existing Redis connection from django-redis
   - Key format: `auth:lockout:{email}` for lockout status
   - Key format: `auth:attempts:{email}` for attempt counter
   - TTL: 3600 seconds (1 hour) for both keys

8. **Performance**
   - Redis operations should add < 10ms to login request
   - Use pipelining for multi-key operations
   - Graceful degradation if Redis unavailable (log warning, allow login)

## Tasks / Subtasks

- [ ] **Task 1**: Create Lockout Service Class (AC #1, #2, #7)
  - [ ] Create `quran_backend/users/services/account_lockout.py`
  - [ ] Implement `AccountLockoutService` class:
    - `record_failed_attempt(email: str, ip_address: str) -> bool`
    - `is_locked(email: str) -> tuple[bool, int]`  # (locked, seconds_remaining)
    - `reset_attempts(email: str) -> None`
    - `get_attempt_count(email: str) -> int`
  - [ ] Use Redis for storage with django-redis cache
  - [ ] Implement TTL of 1 hour (3600 seconds) for all keys
  - [ ] Constants: `MAX_ATTEMPTS = 10`, `LOCKOUT_DURATION = 3600`

- [ ] **Task 2**: Integrate Lockout Check in Login View (AC #2, #3)
  - [ ] Modify `UserLoginView.post()` in `quran_backend/users/api/views.py`
  - [ ] Check `AccountLockoutService.is_locked()` before authentication
  - [ ] Return 423 Locked if account is locked with retry_after
  - [ ] Record failed attempt on authentication failure
  - [ ] Reset attempts on successful authentication
  - [ ] Get client IP from `request.META['REMOTE_ADDR']` or `X-Forwarded-For`

- [ ] **Task 3**: Add Custom 423 Locked Response (AC #3)
  - [ ] Create custom exception `AccountLockedException` in `quran_backend/users/api/exceptions.py`
  - [ ] Include `retry_after` attribute (seconds until unlock)
  - [ ] Update `custom_exception_handler` to handle 423 status
  - [ ] Format error message: "Account temporarily locked. Try again in {minutes} minutes."
  - [ ] Include `retry_after` in response headers (RFC 7231)

- [ ] **Task 4**: Add Django Admin Integration (AC #4)
  - [ ] Create `quran_backend/users/admin/actions.py`
  - [ ] Add admin action: `clear_failed_login_attempts`
  - [ ] Register action in `UserAdmin` class
  - [ ] Display success message: "Cleared failed attempts for X users"
  - [ ] Add to `quran_backend/users/admin.py`

- [ ] **Task 5**: Create Management Command (AC #4)
  - [ ] Create `quran_backend/users/management/commands/clear_lockouts.py`
  - [ ] Command: `python manage.py clear_lockouts --email user@example.com`
  - [ ] Optional flag: `--all` to clear all lockouts
  - [ ] Use `AccountLockoutService.reset_attempts()`
  - [ ] Output: Number of lockouts cleared

- [ ] **Task 6**: Add Security Logging (AC #5)
  - [ ] Configure logger in `AccountLockoutService`
  - [ ] Log failed attempt: `logger.info(f"Failed login attempt for {email} from {ip}")`
  - [ ] Log lockout: `logger.warning(f"Account locked: {email} after {attempts} failed attempts from {ip}")`
  - [ ] Log lockout reset: `logger.info(f"Lockout cleared for {email}")`
  - [ ] Ensure logs integrate with Sentry (already configured in project)

- [ ] **Task 7**: Comprehensive Testing (AC #6)
  - [ ] Test: 9 failed attempts, 10th attempt locks account
  - [ ] Test: Locked account returns 423 with retry_after
  - [ ] Test: Cannot login with correct password when locked
  - [ ] Test: Successful login resets attempt counter
  - [ ] Test: Lockout expires after 1 hour (simulate with Redis TTL)
  - [ ] Test: Different users tracked independently
  - [ ] Test: Failed attempts from different IPs for same user
  - [ ] Test: Redis unavailable (graceful degradation)
  - [ ] Add tests to `quran_backend/users/tests/api/test_lockout.py` (new file)

- [ ] **Task 8**: Performance Testing (AC #8)
  - [ ] Measure login request time with lockout check
  - [ ] Verify Redis operations complete in < 10ms
  - [ ] Test Redis connection pooling
  - [ ] Document performance in code comments

- [ ] **Task 9**: Update Documentation
  - [ ] Update `UserLoginView` docstring with lockout behavior
  - [ ] Document lockout service in `services/account_lockout.py`
  - [ ] Update API documentation with 423 status code
  - [ ] Add developer notes about Redis dependency

## Dev Notes

### Architecture Alignment

**Lockout Strategy**:
- Redis-backed persistent storage (not in-memory)
- Account-level tracking (by email, not IP)
- 1-hour sliding window for attempt counting
- Automatic expiration via Redis TTL

**Redis Key Structure**:
```
auth:attempts:{email}  → Integer counter (TTL: 1 hour)
auth:lockout:{email}   → Timestamp of lockout (TTL: 1 hour)
```

**Lockout Flow**:
1. User attempts login
2. Check if `auth:lockout:{email}` exists → 423 Locked
3. Authenticate user
4. If auth fails → increment `auth:attempts:{email}`
5. If attempts >= 10 → set `auth:lockout:{email}` = now + 1 hour
6. If auth succeeds → delete `auth:attempts:{email}` and `auth:lockout:{email}`

**HTTP Status Codes**:
- `423 Locked`: Account temporarily locked
- `400 Bad Request`: Invalid credentials (when not locked)
- `200 OK`: Successful login

### Security Considerations

**Why Account-Level (Not IP-Level)**:
- IP-based throttling already exists (5/min from US-API-001)
- Account-level prevents distributed brute force (botnet attacks)
- Protects against attacks from multiple IPs targeting single account
- Better user experience (no false positives from shared IPs)

**Lockout Duration**:
- 1 hour: Balance between security and user convenience
- Sliding window: Each failed attempt extends the window
- Auto-expiration: No manual unlock needed after 1 hour

**Redis Failure Handling**:
- Graceful degradation: Allow login if Redis unavailable
- Log warning if Redis connection fails
- Fallback to IP-based throttling only

### Integration Points

- **Redis**: Primary storage for lockout state (django-redis)
- **Django Logging**: Integration with existing logging config
- **Sentry**: Security events logged for monitoring
- **Django Admin**: Manual lockout clearing for support
- **Existing Throttling**: IP-based throttling (5/min) still applies

### Testing Standards

**Test Coverage**:
- Lockout threshold (9 attempts OK, 10 locks)
- Lockout expiration (TTL test with time mocking)
- Successful login resets counter
- Locked account behavior (423 status, retry_after)
- Different users independent tracking
- Redis unavailable fallback
- Admin actions and management commands

**Test Data**:
- Test users: `locked@example.com`, `unlocked@example.com`
- IP addresses: `192.168.1.1`, `192.168.1.2` (different IPs same user)
- Time mocking: Use `freezegun` or `unittest.mock` for TTL tests

**Test Execution**:
```bash
# Run lockout tests only
docker-compose exec django pytest quran_backend/users/tests/api/test_lockout.py -v

# Run with Redis
docker-compose exec django pytest quran_backend/users/tests/api/test_lockout.py -v --redis
```

### Performance Considerations

**Redis Operations**:
- Lockout check: 1 GET operation (`auth:lockout:{email}`)
- Failed attempt: 2 operations (GET + INCR for `auth:attempts:{email}`)
- Lockout trigger: 1 SETEX operation (`auth:lockout:{email}`)
- Successful login: 2 DEL operations (clear attempts and lockout)

**Optimization**:
- Use Redis pipelining for multiple operations
- Connection pooling via django-redis (already configured)
- Estimated overhead: 5-10ms per login request

**Redis Memory**:
- ~100 bytes per locked account
- TTL ensures automatic cleanup
- No manual cleanup job needed

### Learnings from US-API-001

**Reuse Patterns**:
- Existing Redis configuration in `config/settings/base.py`
- Error response format from `custom_exception_handler`
- Test patterns from `test_views.py`
- Security logging patterns (Sentry integration)

**Related Code**:
- `UserLoginView` at `quran_backend/users/api/views.py:59-82`
- `AuthEndpointThrottle` at `quran_backend/users/api/throttling.py:6-14`
- Custom exception handler at `quran_backend/users/api/exceptions.py:6-34`
- Redis settings at `config/settings/base.py` (CACHES configuration)

### References

- [RFC 7231 - 423 Locked Status](https://tools.ietf.org/html/rfc7231#section-6.5.13)
- [django-redis Documentation](https://github.com/jazzband/django-redis)
- [Parent Story: US-API-001](us-api-001-implement-user-authentication-and-authorization.md)
- [Code Review Recommendation](us-api-001-implement-user-authentication-and-authorization.md#recommendations--action-items)

## Dev Agent Record

### Context Reference

- Story Context: (will be created when story is drafted)

### Agent Model Used

(To be filled when implementation begins)

### Completion Notes

**Completed:** 2025-11-07
**Definition of Done:** All acceptance criteria met, code reviewed, tests passing (100%)

### File List

(To be filled during implementation)

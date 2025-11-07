# Story 1.1.1: Implement JWT Token Blacklisting

Status: done

## Story

As a **Quran app user**,
I want **my JWT tokens to be immediately invalidated when I logout**,
so that **my account remains secure even if someone gains access to my old tokens**.

## Background

This story addresses a gap identified in the US-API-001 code review. Currently, when users logout, their JWT tokens remain valid until expiration (30 minutes for access tokens, 14 days for refresh tokens). This creates a security risk where:
- Stolen tokens can continue to be used after logout
- Users cannot immediately revoke access from compromised devices
- Session management lacks fine-grained control

**Parent Story**: US-API-001 - Implement User Authentication and Authorization
**Priority**: P1 - High (security enhancement)
**Effort**: Small (1-2 hours)

## Acceptance Criteria

1. **Enable Token Blacklisting App**
   - Add `rest_framework_simplejwt.token_blacklist` to INSTALLED_APPS
   - Run migrations to create blacklist tables (`BlacklistedToken`, `OutstandingToken`)

2. **Configure Token Rotation**
   - Set `ROTATE_REFRESH_TOKENS = True` in SIMPLE_JWT settings
   - Set `BLACKLIST_AFTER_ROTATION = True` to blacklist old tokens

3. **Update Logout Endpoint**
   - Modify `UserLogoutView` to blacklist the refresh token
   - Import and use `RefreshToken` from simplejwt
   - Add token to blacklist using `token.blacklist()` method
   - Return appropriate error if token is already blacklisted or invalid

4. **Token Validation**
   - Blacklisted tokens must return 401 Unauthorized
   - Error message: "Token is blacklisted" or similar
   - Ensure access tokens associated with blacklisted refresh tokens also fail

5. **Outstanding Token Tracking**
   - Verify OutstandingToken records are created on login
   - Ensure proper cleanup of expired outstanding tokens (via cron/celery)

6. **Testing**
   - Test: User logs out → refresh token is blacklisted
   - Test: Using blacklisted refresh token returns 401
   - Test: Access token from blacklisted session returns 401
   - Test: Logout with invalid token returns appropriate error
   - Test: Logout with already-blacklisted token returns appropriate error
   - Test: Multiple device logout (blacklist all user tokens)

7. **Performance**
   - Blacklist queries should be efficient (indexed lookups)
   - Consider adding database index on token jti field if needed

8. **Documentation**
   - Update API documentation to reflect token blacklisting behavior
   - Document token lifecycle: login → use → logout → blacklisted

## Tasks / Subtasks

- [ ] **Task 1**: Enable Token Blacklisting App (AC #1)
  - [ ] Add `'rest_framework_simplejwt.token_blacklist'` to INSTALLED_APPS in `config/settings/base.py`
  - [ ] Run migrations: `docker-compose exec django python manage.py makemigrations`
  - [ ] Run migrations: `docker-compose exec django python manage.py migrate`
  - [ ] Verify tables created: `BlacklistedToken`, `OutstandingToken`

- [ ] **Task 2**: Configure Token Rotation (AC #2)
  - [ ] Update `SIMPLE_JWT` settings in `config/settings/base.py`:
    - Set `ROTATE_REFRESH_TOKENS = True`
    - Set `BLACKLIST_AFTER_ROTATION = True`
  - [ ] Test token refresh generates new token and blacklists old one
  - [ ] Restart Django container: `docker-compose restart django`

- [ ] **Task 3**: Update Logout Endpoint (AC #3, #4)
  - [ ] Modify `UserLogoutView` in `quran_backend/users/api/views.py`
  - [ ] Import `RefreshToken` from `rest_framework_simplejwt.tokens`
  - [ ] Validate and decode refresh token from request
  - [ ] Call `token.blacklist()` to add to blacklist
  - [ ] Handle exceptions: `TokenError` for invalid tokens
  - [ ] Return 200 OK on success with message
  - [ ] Return 400 Bad Request if token invalid or already blacklisted
  - [ ] Update docstring to reflect new behavior

- [ ] **Task 4**: Add Outstanding Token Tracking Test (AC #5)
  - [ ] Write test to verify OutstandingToken created on login
  - [ ] Write test to verify OutstandingToken references correct user
  - [ ] Test file: `quran_backend/users/tests/api/test_views.py`

- [ ] **Task 5**: Comprehensive Logout Testing (AC #6)
  - [ ] Test: Successful logout blacklists token
  - [ ] Test: Using blacklisted refresh token returns 401
  - [ ] Test: Token refresh with blacklisted token returns 401
  - [ ] Test: Logout with invalid token format returns 400
  - [ ] Test: Logout with already-blacklisted token returns 400
  - [ ] Test: Verify BlacklistedToken record exists in database
  - [ ] Add tests to `quran_backend/users/tests/api/test_views.py::TestUserLogoutView`

- [ ] **Task 6**: Performance Verification (AC #7)
  - [ ] Check database indexes on BlacklistedToken table
  - [ ] Run Django shell query to verify blacklist lookup performance
  - [ ] Document any performance considerations in code comments

- [ ] **Task 7**: Update Documentation (AC #8)
  - [ ] Update `UserLogoutView` docstring with token blacklisting behavior
  - [ ] Update story US-API-001 with note about token blacklisting implementation
  - [ ] Add comment in settings explaining token rotation and blacklisting

- [ ] **Task 8**: Optional - Add Admin Interface for Token Management
  - [ ] Register `OutstandingToken` and `BlacklistedToken` in Django admin
  - [ ] Add list display fields: token, user, created_at, blacklisted_at
  - [ ] Add search fields: user email
  - [ ] Add filters: blacklisted status, created date

## Dev Notes

### Architecture Alignment

**Token Blacklisting Strategy**:
- Uses simplejwt's built-in blacklisting mechanism
- Stores blacklisted tokens in database (PostgreSQL)
- Outstanding tokens tracked for all issued refresh tokens
- Automatic cleanup via Django management command (can be scheduled)

**Database Tables**:
- `token_blacklist_outstandingtoken`: Tracks all issued refresh tokens
  - Fields: `id`, `user_id`, `jti` (unique token ID), `token`, `created_at`, `expires_at`
- `token_blacklist_blacklistedtoken`: Tracks blacklisted tokens
  - Fields: `id`, `token_id` (FK to OutstandingToken), `blacklisted_at`

**Token Rotation**:
- On refresh: new refresh token issued, old one blacklisted
- On logout: current refresh token blacklisted immediately
- Access tokens remain valid until expiration (stateless)

**Security Considerations**:
- Blacklist check adds small database query on each request
- Recommended: Add Redis caching for blacklist lookups (future enhancement)
- Outstanding token cleanup job needed for production (Celery task)

### Integration Points

- **Redis (Optional)**: Cache blacklist lookups for performance
- **Celery**: Schedule periodic cleanup of expired outstanding tokens
- **Django Admin**: Manage tokens for support/debugging

### Testing Standards

**Test Coverage**:
- Logout endpoint blacklist behavior (success and error cases)
- Token refresh with blacklisted tokens
- Outstanding token creation on login
- Database queries for blacklist validation
- Performance test for blacklist lookup time

**Edge Cases**:
- Logout with expired token (should still blacklist)
- Logout with malformed token (400 error)
- Logout with already blacklisted token (400 error)
- Multiple logout attempts with same token

### Performance Considerations

**Database Queries**:
- Blacklist check: 1 query per authenticated request using refresh token
- Outstanding token creation: 1 insert on login
- Blacklist insertion: 1 insert on logout

**Optimization**:
- Consider Redis caching for blacklist (check cache before DB)
- Periodic cleanup job to remove expired outstanding tokens
- Database index on `jti` field (usually created by migration)

**Estimated Impact**:
- Adds ~5-10ms per request (database blacklist check)
- Negligible storage: ~500 bytes per outstanding token
- Cleanup job recommended: run daily to remove expired tokens (>14 days old)

### Learnings from US-API-001

**Reuse Patterns**:
- Existing JWT configuration in `config/settings/base.py`
- Existing test patterns in `test_views.py`
- Error response format from `api/exceptions.py`

**Related Code**:
- `UserLogoutView` at `quran_backend/users/api/views.py:84-113`
- JWT settings at `config/settings/base.py:345-357`
- Login tests at `quran_backend/users/tests/api/test_views.py:181-226`

### References

- [django-rest-framework-simplejwt Token Blacklisting Docs](https://django-rest-framework-simplejwt.readthedocs.io/en/latest/blacklist_app.html)
- [Parent Story: US-API-001](us-api-001-implement-user-authentication-and-authorization.md)
- [Code Review Recommendation](us-api-001-implement-user-authentication-and-authorization.md#sign-off)

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

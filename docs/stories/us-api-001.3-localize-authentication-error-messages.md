# Story 1.1.3: Localize Authentication Error Messages (Arabic/English)

Status: done

## Story

As a **Quran app user**,
I want **authentication error messages to be displayed in my preferred language (Arabic or English)**,
so that **I can understand errors and take appropriate action in my native language**.

## Background

This story addresses Acceptance Criterion #16 from US-API-001 which was partially implemented. The current implementation provides standardized error format but lacks localization:

**Current Gap**: AC #16 requires "error responses in Arabic/English"
**Current Implementation**: Standardized error format (English only)
**Missing**: i18n support with Arabic translations and Accept-Language header processing

**Parent Story**: US-API-001 - Implement User Authentication and Authorization
**Priority**: P1 - High (user experience for Arabic-speaking users)
**Effort**: Small (2-3 hours)

## Acceptance Criteria

1. **Enable Django i18n**
   - Verify LANGUAGE_CODE = 'ar' in settings (already configured)
   - Verify LocaleMiddleware is active (already configured)
   - Add 'en' and 'ar' to LANGUAGES setting
   - Configure locale paths for translation files

2. **Wrap Error Messages in gettext**
   - Import `gettext_lazy as _` in all serializer and view files
   - Wrap all user-facing error strings: `_("Error message")`
   - Update validation error messages in serializers
   - Update view response messages (login, logout, password reset)

3. **Create Arabic Translation Files**
   - Run `django-admin makemessages -l ar` to generate .po files
   - Translate all authentication error messages to Arabic
   - Run `django-admin compilemessages` to generate .mo files
   - Store translations in `locale/ar/LC_MESSAGES/django.po`

4. **Accept-Language Header Processing**
   - Read `Accept-Language` header from requests
   - Set active language using `django.utils.translation.activate()`
   - Support language codes: 'ar', 'en', 'ar-SA', 'en-US'
   - Default to 'ar' if no Accept-Language header

5. **Localized Error Responses**
   - Password validation errors in selected language
   - Authentication failure messages in selected language
   - Rate limiting messages in selected language
   - Token-related errors in selected language
   - Field validation errors in selected language

6. **Testing**
   - Test: Request with `Accept-Language: ar` returns Arabic errors
   - Test: Request with `Accept-Language: en` returns English errors
   - Test: Request with no Accept-Language header defaults to Arabic
   - Test: Invalid credentials error in both languages
   - Test: Password validation error in both languages
   - Test: Rate limit exceeded error in both languages

7. **Error Message Coverage**
   - Registration errors (email exists, weak password, password mismatch)
   - Login errors (invalid credentials, account disabled)
   - Password reset errors (invalid token, expired link)
   - Token errors (invalid token, expired token, blacklisted token)
   - Rate limiting errors (too many requests)

8. **Consistency**
   - All error messages follow same tone/style in both languages
   - Technical terms consistently translated (e.g., "token" → "رمز")
   - Formal Arabic (Modern Standard Arabic, not dialectal)

## Tasks / Subtasks

- [ ] **Task 1**: Configure Django i18n Settings (AC #1)
  - [ ] Verify `LANGUAGE_CODE = 'ar'` in `config/settings/base.py`
  - [ ] Verify `USE_I18N = True` and `USE_L10N = True`
  - [ ] Add LANGUAGES setting: `[('ar', 'Arabic'), ('en', 'English')]`
  - [ ] Configure LOCALE_PATHS: `[BASE_DIR / 'locale']`
  - [ ] Verify LocaleMiddleware in MIDDLEWARE (should be after SessionMiddleware)

- [ ] **Task 2**: Wrap Serializer Error Messages (AC #2, #5)
  - [ ] Update `backend/users/api/serializers.py`
  - [ ] Import: `from django.utils.translation import gettext_lazy as _`
  - [ ] Wrap all error strings in UserRegistrationSerializer:
    - "A user with this email already exists." → `_("A user with this email already exists.")`
    - "Password must be at least 8 characters long." → `_("Password must be at least 8 characters long.")`
    - "Password must contain at least one uppercase letter." → etc.
  - [ ] Wrap all error strings in UserLoginSerializer
  - [ ] Wrap all error strings in PasswordResetRequestSerializer
  - [ ] Wrap all error strings in PasswordResetConfirmSerializer

- [ ] **Task 3**: Wrap View Response Messages (AC #2, #5)
  - [ ] Update `backend/users/api/views.py`
  - [ ] Import: `from django.utils.translation import gettext_lazy as _`
  - [ ] Wrap all response messages:
    - "Successfully logged out" → `_("Successfully logged out")`
    - "Refresh token is required." → `_("Refresh token is required.")`
    - "Password reset email sent if account exists" → `_("Password reset email sent if account exists")`
    - "Password has been reset successfully" → `_("Password has been reset successfully")`

- [ ] **Task 4**: Update Custom Exception Handler (AC #2, #5)
  - [ ] Update `backend/users/api/exceptions.py`
  - [ ] Ensure exception messages are translated
  - [ ] DRF's built-in messages are already i18n-ready
  - [ ] Test that error "code" and "message" fields are localized

- [ ] **Task 5**: Generate Translation Files (AC #3)
  - [ ] Create `locale/` directory at project root
  - [ ] Run: `docker-compose exec django python manage.py makemessages -l ar`
  - [ ] Verify `locale/ar/LC_MESSAGES/django.po` is created
  - [ ] Check all marked strings are extracted

- [ ] **Task 6**: Translate Messages to Arabic (AC #3, #7, #8)
  - [ ] Edit `locale/ar/LC_MESSAGES/django.po`
  - [ ] Translate all authentication error messages:
    ```
    msgid "A user with this email already exists."
    msgstr "يوجد مستخدم بالفعل بهذا البريد الإلكتروني."

    msgid "Password must be at least 8 characters long."
    msgstr "يجب أن تكون كلمة المرور 8 أحرف على الأقل."

    msgid "Password must contain at least one uppercase letter."
    msgstr "يجب أن تحتوي كلمة المرور على حرف كبير واحد على الأقل."

    msgid "Invalid email or password."
    msgstr "البريد الإلكتروني أو كلمة المرور غير صحيحة."

    msgid "Successfully logged out"
    msgstr "تم تسجيل الخروج بنجاح"
    ```
  - [ ] Use Modern Standard Arabic (MSA)
  - [ ] Maintain formal, professional tone
  - [ ] Run: `docker-compose exec django python manage.py compilemessages`

- [ ] **Task 7**: Add Language Detection Middleware (AC #4)
  - [ ] Option 1: Use Django's built-in LocaleMiddleware (already active)
  - [ ] Option 2: Create custom middleware for more control:
    - Create `backend/users/middleware/language.py`
    - Read `Accept-Language` header
    - Call `django.utils.translation.activate(language_code)`
    - Add to MIDDLEWARE after LocaleMiddleware
  - [ ] Test with curl: `curl -H "Accept-Language: ar" http://localhost:8000/api/v1/auth/login/`

- [ ] **Task 8**: Comprehensive i18n Testing (AC #6, #7)
  - [ ] Create `backend/users/tests/api/test_i18n.py`
  - [ ] Test: Registration errors in Arabic (`Accept-Language: ar`)
  - [ ] Test: Registration errors in English (`Accept-Language: en`)
  - [ ] Test: Login errors in Arabic
  - [ ] Test: Login errors in English
  - [ ] Test: Password reset errors in both languages
  - [ ] Test: Default to Arabic when no Accept-Language header
  - [ ] Test: Rate limit errors in both languages
  - [ ] Helper function: `def get_with_language(url, lang='ar')`

- [ ] **Task 9**: Update Documentation
  - [ ] Document Accept-Language header in API docs
  - [ ] Add example requests with language headers
  - [ ] Document supported languages: ar, en
  - [ ] Update OpenAPI/Swagger schema with language parameter

- [ ] **Task 10**: Optional - Add User Language Preference
  - [ ] Add `preferred_language` field to UserProfile (already exists!)
  - [ ] Use user's language preference if authenticated
  - [ ] Fallback to Accept-Language header if not authenticated
  - [ ] Update user language preference on registration

## Dev Notes

### Architecture Alignment

**i18n Strategy**:
- Django's built-in internationalization framework
- Message files (.po) for translation storage
- Compiled message files (.mo) for runtime
- Accept-Language header for per-request language selection

**Language Priority**:
1. User's `preferred_language` (if authenticated and set in UserProfile)
2. `Accept-Language` header (per-request)
3. Default: Arabic (`LANGUAGE_CODE = 'ar'`)

**Translation Files**:
```
locale/
  ar/
    LC_MESSAGES/
      django.po   # Source translations
      django.mo   # Compiled translations
```

**Supported Languages**:
- Arabic (ar): Modern Standard Arabic
- English (en): US English

### Translation Guidelines

**Arabic Translation Standards**:
- Use Modern Standard Arabic (MSA), not colloquial dialects
- Right-to-left (RTL) text direction handled by frontend
- Formal tone appropriate for Islamic app context
- Technical terms:
  - "token" → "رمز" (ramz)
  - "password" → "كلمة المرور" (kalimat al-muroor)
  - "email" → "البريد الإلكتروني" (al-bareed al-electroni)
  - "account" → "الحساب" (al-hisab)
  - "authentication" → "المصادقة" (al-musadaqah)

**Consistency Rules**:
- Always use same translation for recurring terms
- Maintain verb tense consistency
- Keep message length similar to English (for UI constraints)
- Test translations with native Arabic speakers if possible

### Integration Points

- **Django i18n**: Core internationalization framework
- **LocaleMiddleware**: Automatic language detection from headers
- **UserProfile**: User's preferred language preference
- **Frontend**: Sends Accept-Language header based on user settings

### Testing Standards

**Test Coverage**:
- All authentication endpoints with Arabic/English
- Error responses in both languages
- Default language behavior
- Accept-Language header parsing
- Invalid language codes (fallback to default)

**Test Pattern**:
```python
def test_registration_error_in_arabic(self):
    """Test registration error message in Arabic."""
    url = reverse("api:auth-register")
    data = {"email": "invalid-email", "password": "Test123", "password_confirm": "Test123"}
    response = self.client.post(url, data, HTTP_ACCEPT_LANGUAGE='ar')

    assert response.status_code == 400
    assert "البريد الإلكتروني" in str(response.content)  # Arabic text
```

**Test Data**:
- Valid requests with Arabic/English headers
- Invalid credentials in both languages
- Validation errors in both languages
- Mixed language scenarios

### Performance Considerations

**Translation Lookup**:
- `.mo` files cached in memory by Django
- Negligible performance impact (< 1ms)
- No database queries for translation lookup
- Compiled messages loaded on server start

**File Size**:
- `.po` file: ~10KB for authentication messages
- `.mo` file: ~5KB (compiled binary)
- No impact on request size or response time

### Learnings from US-API-001

**Reuse Patterns**:
- Error response format from `custom_exception_handler`
- Serializer validation patterns
- Test patterns from `test_views.py`
- Existing LANGUAGE_CODE = 'ar' configuration

**Related Code**:
- Settings: `config/settings/base.py` (LANGUAGE_CODE, MIDDLEWARE)
- Serializers: `backend/users/api/serializers.py` (all error messages)
- Views: `backend/users/api/views.py` (response messages)
- Exception handler: `backend/users/api/exceptions.py`

**UserProfile Integration**:
- `preferred_language` field already exists in UserProfile model!
- Can be used for authenticated user language preference
- Extends beyond just Accept-Language header

### References

- [Django Internationalization Docs](https://docs.djangoproject.com/en/5.2/topics/i18n/)
- [Django Translation Docs](https://docs.djangoproject.com/en/5.2/topics/i18n/translation/)
- [RFC 7231 - Accept-Language](https://tools.ietf.org/html/rfc7231#section-5.3.5)
- [Parent Story: US-API-001](us-api-001-implement-user-authentication-and-authorization.md)
- [Code Review Recommendation](us-api-001-implement-user-authentication-and-authorization.md#exception-handling)

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

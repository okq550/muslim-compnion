# Coding Standards - Muslim Companion API

**Version:** 1.0
**Last Updated:** 2025-11-13
**Project:** Django Muslim Companion - Muslim Companion API

This document defines the coding standards, conventions, and quality rules enforced in this project. All code must comply with these standards before being committed.

---

## Table of Contents

1. [Pre-Commit Quality Gates](#pre-commit-quality-gates)
2. [Naming Conventions](#naming-conventions)
3. [Code Organization](#code-organization)
4. [Import Standards](#import-standards)
5. [API Response Formats](#api-response-formats)
6. [Consistency Rules](#consistency-rules)
7. [Error Handling](#error-handling)
8. [Security Standards](#security-standards)
9. [Testing Standards](#testing-standards)
10. [Documentation Standards](#documentation-standards)

---

## Pre-Commit Quality Gates

### Overview

This project uses **pre-commit hooks** to enforce code quality. All code is automatically checked before each commit. If any check fails, the commit will be blocked until issues are resolved.

**Pre-commit configuration location:** `backend/.pre-commit-config.yaml`

### Installed Hooks

#### 1. Pre-Commit Standard Hooks

| Hook | Purpose | Failure Example |
|------|---------|-----------------|
| `trailing-whitespace` | Removes trailing whitespace | `def foo():    ` (spaces at end) |
| `end-of-file-fixer` | Ensures files end with newline | File missing final newline |
| `check-json` | Validates JSON syntax | Invalid JSON in fixtures |
| `check-toml` | Validates TOML syntax | Invalid `pyproject.toml` |
| `check-xml` | Validates XML syntax | Malformed XML files |
| `check-yaml` | Validates YAML syntax | Invalid `.yaml` config files |
| `debug-statements` | Detects debug statements | `import pdb; pdb.set_trace()` |
| `check-builtin-literals` | Enforces literal syntax | `dict()` instead of `{}` |
| `check-case-conflict` | Detects case conflicts | `File.py` and `file.py` |
| `check-docstring-first` | Ensures docstring placement | Code before docstring |
| `detect-private-key` | Prevents private key commits | Accidentally committed SSH keys |

#### 2. Django-Upgrade

- **Purpose:** Automatically upgrades Django code to Django 5.2 patterns
- **Target Version:** Django 5.2
- **Examples:**
  - Converts `on_delete=models.CASCADE` to modern syntax
  - Updates deprecated Django APIs
  - Modernizes class-based view patterns

#### 3. Ruff Linter & Formatter

**Ruff** is our primary linter and formatter. It combines the functionality of multiple tools (Flake8, isort, pyupgrade, etc.) with extreme performance.

##### Ruff Linter (`ruff-check`)

**Enabled rule categories:**

- `F` - Pyflakes (undefined names, unused imports)
- `E`, `W` - pycodestyle errors and warnings
- `C90` - McCabe complexity
- `I` - isort (import sorting)
- `N` - pep8-naming conventions
- `UP` - pyupgrade (modernize Python code)
- `YTT` - flake8-2020 (sys.version checks)
- `ASYNC` - flake8-async
- `S` - flake8-bandit (security issues)
- `BLE` - flake8-blind-except
- `FBT` - flake8-boolean-trap
- `B` - flake8-bugbear (common bugs)
- `A` - flake8-builtins (shadowing built-ins)
- `COM` - flake8-commas
- `C4` - flake8-comprehensions
- `DTZ` - flake8-datetimez (timezone awareness)
- `T10` - flake8-debugger
- `DJ` - flake8-django (Django-specific)
- `EM` - flake8-errmsg
- `EXE` - flake8-executable
- `FA` - flake8-future-annotations
- `ISC` - flake8-implicit-str-concat
- `ICN` - flake8-import-conventions
- `G` - flake8-logging-format
- `INP` - flake8-no-pep420
- `PIE` - flake8-pie
- `T20` - flake8-print (no print statements)
- `PYI` - flake8-pyi
- `PT` - flake8-pytest-style
- `Q` - flake8-quotes
- `RSE` - flake8-raise
- `RET` - flake8-return
- `SLF` - flake8-self
- `SLOT` - flake8-slots
- `SIM` - flake8-simplify
- `TID` - flake8-tidy-imports
- `TC` - flake8-type-checking
- `INT` - flake8-gettext
- `PTH` - flake8-use-pathlib
- `ERA` - eradicate (commented code) - **ALLOWED with exceptions**
- `PD` - pandas-vet
- `PGH` - pygrep-hooks
- `PL` - pylint
- `TRY` - tryceratops
- `FLY` - flynt
- `PERF` - perflint
- `RUF` - Ruff-specific rules

**Ignored rules (with reasons):**

- `S101` - Assert statements allowed (needed for tests)
- `RUF012` - Mutable class attributes without ClassVar annotation
- `SIM102` - Nested conditionals allowed when clearer
- `ERA001` - Commented code allowed (strategic technical debt)
- `COM812` - Trailing comma missing (conflicts with ruff-format)

**Test-specific ignores:**

Tests have relaxed rules for pragmatic testing:
- `B007` - Loop control variable not used
- `E501` - Line too long
- `F841` - Local variable assigned but never used
- `PLC0415` - Import should be at top-level
- `PLR2004` - Magic value in comparison
- `S105` - Possible hardcoded password
- `SLF001` - Private member accessed

##### Ruff Formatter (`ruff-format`)

- Automatically formats code to match project style
- **Line length:** 88 characters (PEP 8 default)
- **Indentation:** 4 spaces (never tabs)
- **Quote style:** Double quotes preferred
- **Import sorting:** Force single-line imports (see [Import Standards](#import-standards))

#### 4. djLint (Django Template Linter)

**Purpose:** Lints and formats Django HTML templates

**Configuration:**

- `indent: 2` - Use 2 spaces for template indentation
- `max_line_length: 119`
- `format_css: true` - Format embedded CSS
- `format_js: true` - Format embedded JavaScript
- `blank_line_after_tag: "load,extends"` - Add blank line after these tags
- `close_void_tags: true` - Close void tags like `<br />`

**Ignored rules:**
- `H006` - IMG tag should have height/width/loading attributes
- `H030` - Meta tags
- `H031` - Consider adding meta description
- `T002` - Double quotes should be used in tags

**Enforced rules:**
- `H017` - Avoid replacing Django template tags with static HTML
- `H035` - Meta viewport tag required

### How to Run Pre-Commit Manually

```bash
# Run all hooks on all files
cd muslim_companion
pre-commit run --all-files

# Run all hooks on staged files only
pre-commit run

# Run specific hook
pre-commit run ruff-check --all-files
pre-commit run ruff-format --all-files

# Skip specific hooks (ONLY when explicitly needed)
SKIP=ruff-format git commit -m "message"
SKIP=ruff-check,ruff-format git commit -m "message"
```

### Common Pre-Commit Failures and Fixes

#### Trailing Whitespace

```python
# ❌ FAIL
def my_function():
    pass

# ✅ PASS
def my_function():
    pass
```

#### Import Sorting

```python
# ❌ FAIL - Wrong order
from rest_framework import serializers
import os
from django.db import models

# ✅ PASS - Correct order with blank lines
import os

from django.db import models
from rest_framework import serializers
```

#### Debug Statements

```python
# ❌ FAIL - Debug statement detected
def my_view(request):
    import pdb; pdb.set_trace()
    return Response(data)

# ✅ PASS - Use logging instead
def my_view(request):
    logger.debug("Processing request", extra={"user_id": request.user.id})
    return Response(data)
```

#### Line Too Long

```python
# ❌ FAIL - Line exceeds 88 characters
very_long_variable_name = some_function_with_many_parameters(param1, param2, param3, param4, param5)

# ✅ PASS - Properly formatted
very_long_variable_name = some_function_with_many_parameters(
    param1,
    param2,
    param3,
    param4,
    param5,
)
```

#### Django Template Formatting

```django
{# ❌ FAIL - Missing blank line after load #}
{% load static %}
<html>

{# ✅ PASS - Blank line after load #}
{% load static %}

<html>
```

---

## Naming Conventions

### Database Tables

**Convention:** Singular, lowercase with underscores

```python
# Table names (automatically generated by Django)
quran_surah
quran_verse
reciters_reciter
reciters_audio
users_user
```

### Database Columns

**Convention:** snake_case

```python
# Column names
surah_id
verse_number
name_arabic
created_at
updated_at
is_active
```

### Django Models

**Convention:** PascalCase, singular

```python
# ✅ CORRECT
class Surah(BaseModel):
    pass

class Verse(BaseModel):
    pass

class Reciter(BaseModel):
    pass

# ❌ INCORRECT
class Surahs(BaseModel):  # Don't use plural
    pass

class quran_verse(BaseModel):  # Don't use snake_case
    pass
```

### API Endpoints

**Convention:** Plural nouns, kebab-case for multi-word resources

```python
# ✅ CORRECT
/api/v1/surahs/
/api/v1/verses/
/api/v1/reciters/
/api/v1/audio-files/
/api/v1/reading-history/
/api/v1/user-bookmarks/

# ❌ INCORRECT
/api/v1/surah/           # Use plural
/api/v1/audio_files/     # Use kebab-case, not snake_case
/api/v1/readingHistory/  # Use kebab-case, not camelCase
```

### Python Files

**Convention:** snake_case

```python
# ✅ CORRECT
models.py
serializers.py
test_models.py
import_quran_text.py
account_lockout.py

# ❌ INCORRECT
Models.py              # Don't capitalize
testModels.py          # Use snake_case
importQuranText.py     # Use snake_case
```

### Python Variables and Functions

**Convention:** snake_case

```python
# ✅ CORRECT
def get_verse_by_id(verse_id):
    surah_number = 1
    verse_text = "..."
    return verse_text

# ❌ INCORRECT
def GetVerseById(verseId):    # Don't use PascalCase or camelCase
    SurahNumber = 1            # Don't capitalize variables
    return verseText
```

### Python Constants

**Convention:** UPPER_CASE with underscores

```python
# ✅ CORRECT
MAX_VERSES_PER_REQUEST = 100
DEFAULT_PAGE_SIZE = 20
CACHE_TTL_SECONDS = 86400

# ❌ INCORRECT
maxVersesPerRequest = 100    # Don't use camelCase
Max_Verses_Per_Request = 100 # Don't use mixed case
```

### Environment Variables

**Convention:** UPPER_CASE with underscores

```bash
# ✅ CORRECT
DEBUG=True
SECRET_KEY=xxx
DATABASE_URL=postgresql://...
AWS_ACCESS_KEY_ID=xxx
REDIS_URL=redis://localhost:6379/0

# ❌ INCORRECT
debug=True              # Use uppercase
secretKey=xxx           # Use uppercase and underscores
```

### Class Names

**Convention:** PascalCase

```python
# ✅ CORRECT
class UserSerializer(serializers.ModelSerializer):
    pass

class QuranViewSet(viewsets.ReadOnlyModelViewSet):
    pass

class CacheManager:
    pass

# ❌ INCORRECT
class user_serializer:     # Use PascalCase
    pass

class quranViewSet:        # Use PascalCase
    pass
```

---

## Code Organization

### Django App Structure

Every Django app must follow this structure:

```
apps/quran/
├── __init__.py
├── models.py              # All models for this app
├── serializers.py         # All DRF serializers
├── views.py               # All API views
├── urls.py                # URL routing
├── tasks.py               # Celery tasks
├── validators.py          # Custom validators
├── admin.py               # Django admin configuration
├── apps.py                # App configuration
├── management/
│   └── commands/          # Management commands
│       ├── __init__.py
│       └── import_quran_text.py
├── tests/
│   ├── __init__.py
│   ├── test_models.py     # Model tests
│   ├── test_views.py      # View tests
│   ├── test_serializers.py # Serializer tests
│   ├── test_tasks.py      # Celery task tests
│   └── factories.py       # Test data factories
└── migrations/            # Database migrations
    └── __init__.py
```

### File Size Guidelines

- **Maximum file size:** 500 lines per file
- If a file exceeds 500 lines, split it into smaller modules:
  - `models/` directory with multiple model files
  - `views/` directory with multiple view files
  - `serializers/` directory with multiple serializer files

**Example for large models.py:**

```
apps/quran/
├── models/
│   ├── __init__.py        # Import all models
│   ├── surah.py
│   ├── verse.py
│   ├── translation.py
│   └── reciter.py
```

### Module-Level Organization

Within each Python file:

```python
"""Module docstring explaining purpose."""

# 1. Standard library imports
import os
from datetime import datetime
from typing import Optional

# 2. Third-party imports
from django.db import models
from rest_framework import serializers

# 3. Local imports
from apps.quran.models import Verse
from apps.core.exceptions import ValidationError

# 4. Constants
MAX_VERSES = 6236
DEFAULT_TRANSLATION = "en.sahih"

# 5. Classes
class MyClass:
    pass

# 6. Functions
def my_function():
    pass
```

---

## Import Standards

### Import Order

Imports must be organized in three sections with blank lines between:

```python
# 1. Standard library imports
import json
import logging
import os
from datetime import datetime
from typing import Optional

# 2. Third-party imports
import redis
from celery import shared_task
from django.conf import settings
from django.db import models
from rest_framework import serializers
from rest_framework import status
from rest_framework.response import Response

# 3. Local imports
from backend.core.exceptions import ValidationError
from backend.quran.models import Surah
from backend.quran.models import Verse
from backend.users.models import User
```

### Import Style

**Force single-line imports (enforced by Ruff):**

```python
# ✅ CORRECT - One import per line
from django.db import models
from django.conf import settings
from rest_framework import serializers
from rest_framework import status

# ❌ INCORRECT - Multiple imports on one line
from django.db import models, transaction
from rest_framework import serializers, status
```

### Import Aliases

Use standard aliases consistently:

```python
# ✅ CORRECT - Standard aliases
import pandas as pd
import numpy as np
from django.utils import timezone as tz

# ❌ INCORRECT - Non-standard aliases
import pandas as p
import numpy as n
from django.utils import timezone as t
```

### Avoid Wildcard Imports

```python
# ❌ INCORRECT - Wildcard import
from django.db.models import *

# ✅ CORRECT - Explicit imports
from django.db.models import Model
from django.db.models import CharField
from django.db.models import ForeignKey
```

---

## API Response Formats

### Success Response - Single Resource

```json
{
  "data": {
    "id": 1,
    "surah_number": 1,
    "name_arabic": "الفاتحة",
    "name_transliteration": "Al-Fatihah",
    "verses_count": 7
  }
}
```

### Success Response - List with Pagination

```json
{
  "data": [
    {"id": 1, "surah_number": 1, "name_arabic": "الفاتحة"},
    {"id": 2, "surah_number": 2, "name_arabic": "البقرة"}
  ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_pages": 6,
    "total_count": 114
  }
}
```

### Error Response

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

### Response Field Naming

**Always use snake_case for JSON fields:**

```json
{
  "surah_number": 1,
  "verse_count": 7,
  "created_at": "2025-11-06T14:30:00Z",
  "is_active": true
}
```

**Never use camelCase or PascalCase in JSON:**

```json
// ❌ INCORRECT
{
  "surahNumber": 1,
  "verseCount": 7,
  "createdAt": "2025-11-06T14:30:00Z",
  "IsActive": true
}
```

---

## Consistency Rules

### Date/Time Format

**Convention:** ISO 8601 UTC format

```python
# ✅ CORRECT
"2025-11-06T14:30:00Z"

# Format in Python
from django.utils import timezone
timestamp = timezone.now().isoformat()

# Parse in Python
from datetime import datetime
dt = datetime.fromisoformat("2025-11-06T14:30:00Z")
```

**Storage rules:**
- All timestamps stored in UTC in database
- Client responsible for timezone conversion
- Never store local times without timezone

### JSON Field Naming

**Convention:** snake_case (consistent with Python)

```python
# ✅ CORRECT
{
    "surah_number": 1,
    "created_at": "2025-11-06T14:30:00Z",
    "is_active": true
}

# ❌ INCORRECT
{
    "surahNumber": 1,      # Don't use camelCase
    "CreatedAt": "...",    # Don't use PascalCase
    "is-active": true      # Don't use kebab-case
}
```

### Boolean Values

```python
# ✅ CORRECT - Use True/False in Python
is_active = True
has_permission = False

# ✅ CORRECT - Use true/false in JSON
{"is_active": true, "has_permission": false}

# ❌ INCORRECT
is_active = 1           # Don't use integers
has_permission = "yes"  # Don't use strings
```

### Null vs Empty String

```python
# Use null for missing/unknown values
{
    "email": null,  # Email not provided
    "bio": ""       # Bio provided but empty
}

# In Python
email = None           # Not provided
bio = ""               # Provided but empty
```

### Model Timestamps

All models must inherit from BaseModel with timestamps:

```python
from django.db import models

class BaseModel(models.Model):
    """Base model with automatic timestamps for all models."""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

# All models inherit from BaseModel
class Verse(BaseModel):
    surah = models.ForeignKey(Surah, on_delete=models.CASCADE)
    verse_number = models.IntegerField()
    text_uthmani = models.TextField()
    # created_at and updated_at automatically included
```

---

## Error Handling

### Error Response Format

All errors must use this consistent format:

```json
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

#### Authentication Errors (AUTH_*)

- `AUTH_INVALID_TOKEN` - JWT token is invalid or malformed
- `AUTH_EXPIRED_TOKEN` - JWT token has expired
- `AUTH_INVALID_CREDENTIALS` - Email/password combination is incorrect
- `AUTH_USER_NOT_FOUND` - User account does not exist
- `AUTH_ACCOUNT_LOCKED` - Account locked due to failed login attempts

#### Validation Errors (VALIDATION_*)

- `VALIDATION_INVALID_SURAH` - Surah ID out of range (must be 1-114)
- `VALIDATION_INVALID_VERSE` - Verse number exceeds Surah's total verses
- `VALIDATION_INVALID_JUZ` - Juz number out of range (must be 1-30)
- `VALIDATION_INVALID_PAGE` - Page number out of range (must be 1-604)
- `VALIDATION_REQUIRED_FIELD` - Required field is missing
- `VALIDATION_INVALID_FORMAT` - Field format is invalid

#### Resource Errors (RESOURCE_*)

- `RESOURCE_NOT_FOUND` - Requested resource does not exist
- `RESOURCE_ALREADY_EXISTS` - Resource already exists (duplicate)
- `RESOURCE_CONFLICT` - Operation conflicts with existing data

#### Server Errors (SERVER_*)

- `SERVER_ERROR` - Internal server error (500)
- `SERVER_UNAVAILABLE` - Service temporarily unavailable (503)
- `SERVER_TIMEOUT` - Request timed out

#### Rate Limiting (RATE_LIMIT_*)

- `RATE_LIMIT_EXCEEDED` - Too many requests, rate limit exceeded

### HTTP Status Codes

```python
# Success
200 OK              # Successful GET, PUT, PATCH
201 Created         # Successful POST (resource created)
204 No Content      # Successful DELETE

# Client Errors
400 Bad Request     # Validation errors, malformed request
401 Unauthorized    # Authentication required
403 Forbidden       # Insufficient permissions
404 Not Found       # Resource not found
409 Conflict        # Resource conflict (duplicate)
429 Too Many Requests  # Rate limit exceeded

# Server Errors
500 Internal Server Error  # Unhandled server error
503 Service Unavailable    # Service temporarily down
```

### User-Facing Error Messages

**Rules:**
- Clear and actionable
- No technical jargon
- Include what went wrong and how to fix it
- Never expose internal details or stack traces

```python
# ✅ GOOD
"The requested verse does not exist. Please check the Surah and verse numbers."
"Your account has been locked due to too many failed login attempts. Please try again in 30 minutes."

# ❌ BAD
"DoesNotExist: Verse matching query does not exist."
"500 Internal Server Error: NoneType object has no attribute 'text'"
```

### Exception Handling in Code

```python
# ✅ CORRECT - Specific exception with context
from backend.core.exceptions import ValidationError

def get_verse(surah_id: int, verse_number: int):
    try:
        verse = Verse.objects.get(
            surah_id=surah_id,
            verse_number=verse_number
        )
        return verse
    except Verse.DoesNotExist:
        logger.error(
            "Verse not found",
            extra={"surah_id": surah_id, "verse_number": verse_number}
        )
        raise ValidationError(
            code="RESOURCE_NOT_FOUND",
            message=f"Verse {verse_number} in Surah {surah_id} does not exist.",
            details={"surah_id": surah_id, "verse_number": verse_number}
        )

# ❌ INCORRECT - Bare except
def get_verse(surah_id, verse_number):
    try:
        verse = Verse.objects.get(surah_id=surah_id, verse_number=verse_number)
        return verse
    except:  # Never use bare except
        return None
```

---

## Security Standards

### Password Storage

```python
# ✅ CORRECT - Use Django's password hasher (Argon2)
from django.contrib.auth.hashers import make_password

user.password = make_password(raw_password)
user.save()

# ❌ INCORRECT - Never store plain text passwords
user.password = raw_password  # NEVER DO THIS
```

### JWT Token Configuration

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

### Logging Security

**What to log:**
- All API requests (endpoint, user, timestamp)
- Authentication events (login, logout, failed attempts)
- All errors with context
- Performance metrics

**What NOT to log (CRITICAL):**
- Passwords or password hashes
- JWT tokens or API keys
- Personal Identifiable Information (PII) unless necessary
- Full request/response bodies with sensitive data

```python
# ✅ CORRECT - No sensitive data
logger.info(
    "User logged in",
    extra={
        "user_id": request.user.id,
        "ip_address": request.META.get('REMOTE_ADDR'),
        "user_agent": request.META.get('HTTP_USER_AGENT')
    }
)

# ❌ INCORRECT - Contains password
logger.info(
    "Login attempt",
    extra={
        "email": email,
        "password": password  # NEVER LOG PASSWORDS
    }
)
```

### SQL Injection Prevention

```python
# ✅ CORRECT - Use Django ORM or parameterized queries
verses = Verse.objects.filter(surah_id=surah_id)

# ✅ CORRECT - Parameterized raw SQL (if needed)
verses = Verse.objects.raw(
    "SELECT * FROM verses WHERE surah_id = %s",
    [surah_id]
)

# ❌ INCORRECT - String interpolation (SQL injection risk)
verses = Verse.objects.raw(
    f"SELECT * FROM verses WHERE surah_id = {surah_id}"
)
```

### XSS Prevention

```python
# ✅ CORRECT - Django templates auto-escape
{{ verse.text_uthmani }}  # Automatically escaped

# ✅ CORRECT - Explicitly escape in code
from django.utils.html import escape
safe_text = escape(user_input)

# ❌ INCORRECT - Mark unsafe content as safe
{{ verse.text_uthmani|safe }}  # Only if you're 100% sure it's safe
```

---

## Testing Standards

### Test File Naming

```python
# ✅ CORRECT
test_models.py
test_views.py
test_serializers.py
test_tasks.py

# ❌ INCORRECT
models_test.py       # Use test_ prefix
testModels.py        # Use snake_case
```

### Test Class Naming

```python
# ✅ CORRECT
class TestVerseModel:
    pass

class TestSurahViewSet:
    pass

# ❌ INCORRECT
class VerseTest:        # Use Test prefix
    pass

class test_verse:       # Use PascalCase
    pass
```

### Test Method Naming

```python
# ✅ CORRECT
def test_create_verse_with_valid_data():
    pass

def test_get_verse_returns_404_when_not_found():
    pass

# ❌ INCORRECT
def testCreateVerse():              # Use snake_case
    pass

def test_verse():                   # Be specific
    pass
```

### Test Structure (AAA Pattern)

```python
def test_create_verse_with_valid_data():
    # Arrange - Set up test data
    surah = SurahFactory()
    verse_data = {
        "surah": surah,
        "verse_number": 1,
        "text_uthmani": "بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ"
    }

    # Act - Perform the action
    verse = Verse.objects.create(**verse_data)

    # Assert - Check the result
    assert verse.surah == surah
    assert verse.verse_number == 1
    assert verse.text_uthmani == verse_data["text_uthmani"]
```

### Test Coverage Requirements

- **Minimum coverage:** 80% overall
- **Critical paths:** 100% coverage (authentication, payment, data integrity)
- Run coverage report: `coverage run -m pytest && coverage report`

---

## Documentation Standards

### Module Docstrings

```python
"""
Module for Quran verse management.

This module provides models, serializers, and views for managing
Quranic verses including retrieval by Surah, Juz, and page number.
"""
```

### Class Docstrings

```python
class Verse(BaseModel):
    """
    Model representing a single verse from the Quran.

    Attributes:
        surah (ForeignKey): Reference to the parent Surah
        verse_number (int): Verse number within the Surah (1-286)
        text_uthmani (str): Arabic text in Uthmani script
        text_simple (str): Arabic text in simplified script
    """
```

### Function/Method Docstrings

```python
def get_verse_by_location(surah_id: int, verse_number: int) -> Verse:
    """
    Retrieve a verse by Surah ID and verse number.

    Args:
        surah_id: The Surah ID (1-114)
        verse_number: The verse number within the Surah

    Returns:
        Verse: The requested verse object

    Raises:
        ValidationError: If surah_id or verse_number is invalid
        Verse.DoesNotExist: If the verse is not found

    Example:
        >>> verse = get_verse_by_location(1, 1)
        >>> print(verse.text_uthmani)
        بِسْمِ ٱللَّهِ ٱلرَّحْمَـٰنِ ٱلرَّحِيمِ
    """
```

### Inline Comments

```python
# Use comments to explain WHY, not WHAT

# ✅ GOOD - Explains reasoning
# Using LRU cache here because Surah data rarely changes
# and is frequently accessed across multiple requests
@lru_cache(maxsize=114)
def get_surah(surah_id: int) -> Surah:
    return Surah.objects.get(id=surah_id)

# ❌ BAD - Explains obvious code
# Get the surah by ID
surah = Surah.objects.get(id=surah_id)
```

---

## Logging Standards

### Logger Initialization

```python
import logging
logger = logging.getLogger(__name__)
```

### Log Levels

- `DEBUG` - Detailed debugging information (development only)
- `INFO` - General informational messages
- `WARNING` - Warning messages (deprecated usage, etc.)
- `ERROR` - Error messages (recoverable)
- `CRITICAL` - Critical errors (system crash)

### Structured Logging

```python
# ✅ CORRECT - Structured logging with context
logger.info(
    "Verse retrieved",
    extra={
        "surah_id": 1,
        "verse_number": 1,
        "user_id": request.user.id,
        "endpoint": "/api/v1/verses/",
        "response_time_ms": 45
    }
)

# ❌ INCORRECT - String interpolation
logger.info(f"User {user_id} retrieved verse {verse_id}")
```

### Error Logging

```python
# ✅ CORRECT - Include exception info
try:
    verse = get_verse(surah_id, verse_number)
except Exception as e:
    logger.error(
        "Failed to retrieve verse",
        extra={
            "surah_id": surah_id,
            "verse_number": verse_number,
            "error": str(e)
        },
        exc_info=True  # Include stack trace
    )
    raise
```

---

## Additional Resources

### Configuration Files

- **Pre-commit config:** `backend/.pre-commit-config.yaml`
- **Ruff config:** `backend/pyproject.toml` (tool.ruff section)
- **Django settings:** `backend/config/settings/`
- **Architecture document:** `docs/architecture.md`

### Running Quality Checks

```bash
# Install pre-commit hooks
cd muslim_companion
pre-commit install

# Run all checks
pre-commit run --all-files

# Run specific checks
ruff check .
ruff format .
python manage.py test

# Run with coverage
coverage run -m pytest
coverage report
coverage html
```

### Common Commands

```bash
# Format code automatically
ruff format .

# Check and auto-fix linting issues
ruff check --fix .

# Run Django checks
python manage.py check

# Run tests
pytest

# Create migration
python manage.py makemigrations

# Apply migrations
python manage.py migrate
```

---

## Version History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | 2025-11-13 | Initial coding standards document created from architecture.md and pre-commit configuration |

---

**This is a living document. When coding standards change, this document must be updated accordingly.**

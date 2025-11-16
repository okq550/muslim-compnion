# muslim-companion

Muslim Companion API for Islamic Spiritual Companion App

[![Built with Cookiecutter Django](https://img.shields.io/badge/built%20with-Cookiecutter%20Django-ff69b4.svg?logo=cookiecutter)](https://github.com/cookiecutter/cookiecutter-django/)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

License: MIT

## Getting Started

### Prerequisites

- **Python 3.14** (latest stable)
- **Docker** and **Docker Compose**
- **Git**

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd muslim-companion/muslim_companion
   ```

2. **Build Docker containers:**
   ```bash
   docker compose -f docker-compose.local.yml build
   ```

3. **Start all services:**
   ```bash
   docker compose -f docker-compose.local.yml up -d
   ```

   This starts:
   - Django web server (localhost:8000)
   - PostgreSQL 16 database
   - Redis (caching and Celery broker)
   - Celery worker
   - Celery beat scheduler
   - Flower (Celery monitoring at localhost:5555)

4. **Run database migrations:**
   ```bash
   docker compose -f docker-compose.local.yml exec django python manage.py migrate
   ```

5. **Create a superuser:**
   ```bash
   docker compose -f docker-compose.local.yml exec django python manage.py createsuperuser
   ```

6. **Access the application:**
   - Django Admin: http://localhost:8000/admin
   - DRF Browsable API: http://localhost:8000/api/
   - API Documentation (Swagger UI): http://localhost:8000/api/docs/
   - API Documentation (ReDoc): http://localhost:8000/api/redoc/
   - OpenAPI Schema: http://localhost:8000/api/schema/
   - Health Check: http://localhost:8000/api/v1/health/
   - Flower (Celery monitoring): http://localhost:5555

### Environment Configuration

Environment variables are configured in `.envs/.local/`:
- `.django` - Django and Celery settings
- `.postgres` - PostgreSQL database credentials

The `DATABASE_URL` is automatically configured for Docker Compose services.

### Arabic Localization

This project is configured with **Arabic as the default language** with bilingual support (Arabic/English).

**i18n Configuration:**
- Default language: Arabic (`ar`)
- Supported languages: Arabic, English
- Django admin displays in Arabic by default
- Language switching available via middleware

**Managing translations:**
```bash
# Generate translation files
docker compose -f docker-compose.local.yml exec django python manage.py makemessages -l ar

# Compile translations
docker compose -f docker-compose.local.yml exec django python manage.py compilemessages
```

### Running Tests

```bash
docker compose -f docker-compose.local.yml exec django pytest
```

### Stopping Services

```bash
docker compose -f docker-compose.local.yml down
```

## API Documentation

The Muslim Companion API provides comprehensive, interactive documentation powered by OpenAPI 3.0 and drf-spectacular.

### Accessing API Documentation

- **Swagger UI**: http://localhost:8000/api/docs/
  - Interactive "try it out" interface
  - Test endpoints directly from your browser
  - Authentication support with JWT tokens

- **ReDoc**: http://localhost:8000/api/redoc/
  - Clean, readable documentation
  - Easy navigation and search
  - Mobile-friendly interface

- **OpenAPI Schema**: http://localhost:8000/api/schema/
  - Raw OpenAPI 3.0 JSON specification
  - Can be imported into Postman, Insomnia, etc.

### Authentication

The API uses JWT (JSON Web Token) authentication:

1. **Register**: `POST /api/v1/auth/register/`
2. **Login**: `POST /api/v1/auth/login/` → Returns `access_token` and `refresh_token`
3. **Use Token**: Include `Authorization: Bearer <access_token>` in request headers
4. **Refresh Token**: `POST /api/v1/auth/token/refresh/` with `refresh_token`

**Token Expiration:**
- Access Token: 30 minutes
- Refresh Token: 14 days

**Rate Limits:**
- Authenticated users: 100 requests/minute
- Anonymous users: 20 requests/minute
- Documentation endpoints: No rate limit

### Error Responses

All API errors follow a standard format:
```json
{
  "error": "ERROR_CODE",
  "message": "Human-readable error message",
  "request_id": "correlation-id-for-troubleshooting",
  "details": [
    {"field": "field_name", "message": "Field-specific error"}
  ]
}
```

### Health Monitoring

Check system health: `GET /api/v1/health/`
- Returns 200 OK if all services are healthy
- Returns 503 Service Unavailable if any service is down
- Monitors: PostgreSQL, Redis, Celery, Disk Space

## Settings

Moved to [settings](https://cookiecutter-django.readthedocs.io/en/latest/1-getting-started/settings.html).

## Basic Commands

### Setting Up Your Users

- To create a **normal user account**, just go to Sign Up and fill out the form. Once you submit it, you'll see a "Verify Your E-mail Address" page. Go to your console to see a simulated email verification message. Copy the link into your browser. Now the user's email should be verified and ready to go.

- To create a **superuser account**, use this command:

      uv run python manage.py createsuperuser

For convenience, you can keep your normal user logged in on Chrome and your superuser logged in on Firefox (or similar), so that you can see how the site behaves for both kinds of users.

### Type checks

Running type checks with mypy:

    uv run mypy muslim_companion

### Test coverage

To run the tests, check your test coverage, and generate an HTML coverage report:

    uv run coverage run -m pytest
    uv run coverage html
    uv run open htmlcov/index.html

#### Running tests with pytest

    uv run pytest

### Live reloading and Sass CSS compilation

Moved to [Live reloading and SASS compilation](https://cookiecutter-django.readthedocs.io/en/latest/2-local-development/developing-locally.html#using-webpack-or-gulp).

### Celery

This app comes with Celery.

To run a celery worker:

```bash
cd muslim_companion
uv run celery -A config.celery_app worker -l info
```

Please note: For Celery's import magic to work, it is important _where_ the celery commands are run. If you are in the same folder with _manage.py_, you should be right.

To run [periodic tasks](https://docs.celeryq.dev/en/stable/userguide/periodic-tasks.html), you'll need to start the celery beat scheduler service. You can start it as a standalone process:

```bash
cd muslim_companion
uv run celery -A config.celery_app beat
```

or you can embed the beat service inside a worker with the `-B` option (not recommended for production use):

```bash
cd muslim_companion
uv run celery -A config.celery_app worker -B -l info
```

### Sentry

Sentry is an error logging aggregator service. You can sign up for a free account at <https://sentry.io/signup/?code=cookiecutter> or download and host it yourself.
The system is set up with reasonable defaults, including 404 logging and integration with the WSGI application.

You must set the DSN url in production.

## Deployment

The following details how to deploy this application.

### Docker

See detailed [cookiecutter-django Docker documentation](https://cookiecutter-django.readthedocs.io/en/latest/3-deployment/deployment-with-docker.html).

from .base import *  # noqa: F403
from .base import INSTALLED_APPS
from .base import MIDDLEWARE
from .base import env

# GENERAL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#debug
DEBUG = True
# https://docs.djangoproject.com/en/dev/ref/settings/#secret-key
SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="axrKSAtHhM9odAE40GhYZMdPATeXC6kHk4zrHdh4eSUwEcuxh9PR4Ta8uYQHvHcw",
)
# https://docs.djangoproject.com/en/dev/ref/settings/#allowed-hosts
ALLOWED_HOSTS = ["localhost", "0.0.0.0", "127.0.0.1"]  # noqa: S104

# ENVIRONMENT
# ------------------------------------------------------------------------------
ENVIRONMENT_NAME = env("ENVIRONMENT_NAME", default="local")

# CACHES
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#caches
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            # Graceful degradation - don't break app if Redis is unavailable
            "IGNORE_EXCEPTIONS": True,
            # Connection pool settings
            "CONNECTION_POOL_KWARGS": {
                "max_connections": 50,
                "retry_on_timeout": True,
            },
            # Socket timeout
            "SOCKET_CONNECT_TIMEOUT": 5,
            "SOCKET_TIMEOUT": 5,
            # Max entries in memory before eviction
            "MAX_ENTRIES": 10000,
        },
        # Cache key prefix to avoid collisions
        "KEY_PREFIX": "muslim_companion",
        # Default TTL: 7 days (604800 seconds) for static content
        "TIMEOUT": 604800,
    },
}

# EMAIL
# ------------------------------------------------------------------------------
# https://docs.djangoproject.com/en/dev/ref/settings/#email-backend
EMAIL_BACKEND = env(
    "DJANGO_EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

# Anymail (Mailgun)
# ------------------------------------------------------------------------------
# Only configure Anymail if Mailgun credentials are provided
if env("X", default=None):
    # https://anymail.readthedocs.io/en/stable/installation/#installing-anymail
    INSTALLED_APPS += ["anymail"]
    # https://anymail.readthedocs.io/en/stable/installation/#anymail-settings-reference
    # https://anymail.readthedocs.io/en/stable/esps/mailgun/
    ANYMAIL = {
        "X": env("X"),
        "MAILGUN_SENDER_DOMAIN": env("MAILGUN_SENDER_DOMAIN"),
        "MAILGUN_API_URL": env("MAILGUN_API_URL", default="https://api.mailgun.net/v3"),
    }

# Email configuration
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="noreply@quranbackend.com")
FRONTEND_PASSWORD_RESET_URL = env(
    "FRONTEND_PASSWORD_RESET_URL",
    default="http://localhost:3000/reset-password",
)

# django-debug-toolbar
# ------------------------------------------------------------------------------
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#prerequisites
INSTALLED_APPS += ["debug_toolbar"]
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#middleware
MIDDLEWARE += ["debug_toolbar.middleware.DebugToolbarMiddleware"]
# https://django-debug-toolbar.readthedocs.io/en/latest/configuration.html#debug-toolbar-config
DEBUG_TOOLBAR_CONFIG = {
    "DISABLE_PANELS": [
        "debug_toolbar.panels.redirects.RedirectsPanel",
        # Disable profiling panel due to an issue with Python 3.12+:
        # https://github.com/jazzband/django-debug-toolbar/issues/1875
        "debug_toolbar.panels.profiling.ProfilingPanel",
    ],
    "SHOW_TEMPLATE_CONTEXT": True,
}
# https://django-debug-toolbar.readthedocs.io/en/latest/installation.html#internal-ips
INTERNAL_IPS = ["127.0.0.1", "10.0.2.2"]
if env("USE_DOCKER") == "yes":
    import socket

    hostname, _, ips = socket.gethostbyname_ex(socket.gethostname())
    INTERNAL_IPS += [".".join([*ip.split(".")[:-1], "1"]) for ip in ips]

# django-extensions
# ------------------------------------------------------------------------------
# https://django-extensions.readthedocs.io/en/latest/installation_instructions.html#configuration
INSTALLED_APPS += ["django_extensions"]

# Middleware - Force Arabic
# ------------------------------------------------------------------------------
MIDDLEWARE += ["backend.middleware.ForceArabicMiddleware"]

# Celery
# ------------------------------------------------------------------------------

# https://docs.celeryq.dev/en/stable/userguide/configuration.html#task-eager-propagates
CELERY_TASK_EAGER_PROPAGATES = True

# Internationalization - Force Arabic
# ------------------------------------------------------------------------------
# Override to ensure Arabic is always used in local development
LANGUAGE_CODE = "ar"

# Your stuff...
# ------------------------------------------------------------------------------

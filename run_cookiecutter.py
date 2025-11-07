#!/usr/bin/env python3.14
"""
Script to run cookiecutter-django with specified configuration
"""

from cookiecutter.main import cookiecutter

# Configuration matching the architecture document specifications
extra_context = {
    "project_name": "django-muslim-companion",
    "project_slug": "quran_backend",
    "description": "Quran Backend API for Islamic Spiritual Companion App",
    "author_name": "Development Team",
    "domain_name": "example.com",
    "email": "dev@example.com",
    "version": "0.1.0",
    "open_source_license": "MIT",
    "timezone": "UTC",
    "windows": "n",
    "use_pycharm": "n",
    "use_docker": "y",
    "postgresql_version": "16",
    "cloud_provider": "AWS",
    "mail_service": "Mailgun",
    "use_async": "n",
    "use_drf": "y",
    "frontend_pipeline": "None",
    "use_celery": "y",
    "use_mailhog": "n",
    "use_sentry": "y",
    "use_whitenoise": "n",
    "use_heroku": "n",
    "ci_tool": "None",
    "keep_local_envs_in_vcs": "y",
    "debug": "n",
}

# Run cookiecutter with the configuration
print("Running cookiecutter-django with configuration:")
for key, value in extra_context.items():
    print(f"  {key}: {value}")
print()

cookiecutter(
    "https://github.com/cookiecutter/cookiecutter-django",
    no_input=True,
    extra_context=extra_context,
    output_dir=".",
)

print("\n✅ Cookiecutter project created successfully!")

"""Quran app configuration."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class QuranConfig(AppConfig):
    """Configuration for the Quran app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "backend.quran"
    verbose_name = _("Quran")

    def ready(self):
        """Import signals when app is ready."""
        # Add signal imports here when needed

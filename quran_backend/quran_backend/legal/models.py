from django.db import models
from django.utils.translation import gettext_lazy as _


class PrivacyPolicy(models.Model):
    """
    Privacy policy content for the application.

    Tracks versions and effective dates for GDPR compliance.
    """

    content = models.TextField(
        _("Content"),
        help_text=_("Privacy policy content in Markdown format"),
    )
    version = models.CharField(
        _("Version"),
        max_length=20,
        unique=True,
        help_text=_("Version identifier (e.g., '1.0', '2.0')"),
    )
    effective_date = models.DateField(
        _("Effective Date"),
        help_text=_("Date when this policy version becomes effective"),
    )
    last_updated = models.DateTimeField(
        _("Last Updated"),
        auto_now=True,
    )
    is_active = models.BooleanField(
        _("Is Active"),
        default=True,
        help_text=_("Whether this is the current active policy"),
    )

    class Meta:
        verbose_name = _("Privacy Policy")
        verbose_name_plural = _("Privacy Policies")
        ordering = ["-effective_date"]

    def __str__(self):
        return f"Privacy Policy v{self.version}"

    def save(self, *args, **kwargs):
        """Ensure only one active policy at a time."""
        if self.is_active:
            # Deactivate all other policies
            PrivacyPolicy.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)

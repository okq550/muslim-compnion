import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import BooleanField
from django.db.models import CharField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Custom user model for muslim_companion with email authentication.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # Use UUID as primary key for globally unique user identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Override email to make it unique and required
    email = models.EmailField(
        _("Email Address"),
        unique=True,
        blank=False,
        help_text=_("User's email address for authentication."),
    )

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    # Analytics consent field
    is_analytics_enabled = BooleanField(
        _("Analytics Enabled"),
        default=False,
        help_text=_("User has consented to usage analytics tracking."),
    )

    # Use email for authentication instead of username
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})


class UserProfile(models.Model):
    """
    User profile model for storing user preferences.
    One-to-one relationship with User model.
    """

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="profile",
        primary_key=True,
    )

    preferred_language = CharField(
        _("Preferred Language"),
        max_length=10,
        default="ar",
        help_text=_("User's preferred language for app interface (e.g., 'ar', 'en')."),
    )

    timezone = CharField(
        _("Timezone"),
        max_length=50,
        default="UTC",
        help_text=_("User's timezone for prayer times and date formatting."),
    )

    def __str__(self) -> str:
        """String representation of UserProfile.

        Returns:
            str: User's email with profile indicator.

        """
        return f"Profile for {self.user.email}"

import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from quran_backend.users.models import User
from quran_backend.users.models import UserProfile


class UserSerializer(serializers.ModelSerializer[User]):
    """
    Serializer for user data.

    Provides basic user information including username, name, and profile URL.
    Used for user profile retrieval and updates.
    """

    class Meta:
        model = User
        fields = ["username", "name", "url"]

        extra_kwargs = {
            "url": {
                "view_name": "api:user-detail",
                "lookup_field": "username",
                "help_text": _("API endpoint URL for this user's profile"),
            },
        }


class UserRegistrationSerializer(serializers.Serializer):
    """
    Serializer for user registration with email and password.

    Validates email uniqueness and password strength requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit

    Returns JWT access and refresh tokens upon successful registration.
    """

    email = serializers.EmailField(
        required=True,
        help_text=_("User's email address (used for authentication and notifications)"),
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={"input_type": "password"},
        help_text=_(
            "User password (min 8 characters, must include uppercase, lowercase, and digit)",
        ),
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text=_("Password confirmation (must match password)"),
    )

    def validate_email(self, value):
        """Validate that email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError(
                _("A user with this email already exists."),
            )
        return value.lower()

    def validate_password(self, value):
        """Validate password strength requirements (AC #6)."""
        # Minimum 8 characters
        if len(value) < 8:
            raise serializers.ValidationError(
                _("Password must be at least 8 characters long."),
            )

        # Complexity validation: uppercase, lowercase, digit
        if not re.search(r"[A-Z]", value):
            raise serializers.ValidationError(
                _("Password must contain at least one uppercase letter."),
            )
        if not re.search(r"[a-z]", value):
            raise serializers.ValidationError(
                _("Password must contain at least one lowercase letter."),
            )
        if not re.search(r"\d", value):
            raise serializers.ValidationError(
                _("Password must contain at least one digit."),
            )

        # Use Django's password validators (AC #13)
        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))

        return value

    def validate(self, attrs):
        """Validate that passwords match."""
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": _("Passwords do not match.")},
            )
        return attrs

    def create(self, validated_data):
        """Create user and user profile in a single transaction (AC #1, #14, #15)."""
        validated_data.pop("password_confirm")

        with transaction.atomic():
            # Generate unique username from email
            username = validated_data["email"].split("@")[0]
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{base_username}{counter}"
                counter += 1

            # Create user with hashed password (AC #13)
            user = User.objects.create_user(
                username=username,
                email=validated_data["email"],
                password=validated_data["password"],
            )

            # Create UserProfile (AC #15)
            UserProfile.objects.create(user=user)

        return user

    def to_representation(self, instance):
        """Return user data with JWT tokens (AC #2)."""
        refresh = RefreshToken.for_user(instance)

        return {
            "user": {
                "id": str(instance.id),
                "email": instance.email,
                "username": instance.username,
            },
            "tokens": {
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
            },
        }


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login with email and password.

    Authenticates user credentials and returns JWT access and refresh tokens.
    Account lockout policy: 10 failed attempts result in a 30-minute lockout.

    Returns:
    - access_token: JWT access token (valid for 30 minutes)
    - refresh_token: JWT refresh token (valid for 14 days)
    """

    email = serializers.EmailField(
        required=True,
        help_text=_("User's email address (used for authentication)"),
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text=_("User's password"),
    )

    def validate(self, attrs):
        """Authenticate user and return user object (AC #2)."""
        from django.contrib.auth import authenticate

        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(username=email, password=password)

        if user is None:
            raise serializers.ValidationError(
                {"detail": _("Invalid email or password.")},
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": _("User account is disabled.")},
            )

        attrs["user"] = user
        return attrs

    def to_representation(self, instance):
        """Return JWT tokens (AC #2, #7, #8)."""
        user = self.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        return {
            "tokens": {
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
            },
        }


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializer for password reset request.

    Initiates password reset flow by sending reset email to the user.
    For security, the response does not reveal whether the email exists in the system.
    """

    email = serializers.EmailField(
        required=True,
        help_text=_(
            "Email address associated with the account (reset instructions will be sent here)",
        ),
    )

    def validate_email(self, value):
        """Validate that email exists."""
        if not User.objects.filter(email=value).exists():
            # Don't reveal whether email exists for security
            pass
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializer for password reset confirmation.

    Validates the password reset token and sets the new password.
    Requires the same password strength requirements as registration.
    """

    token = serializers.CharField(
        required=True,
        help_text=_("Password reset token received via email"),
    )
    uid = serializers.CharField(
        required=True,
        help_text=_("User identifier (base64-encoded) received via email"),
    )
    new_password = serializers.CharField(
        write_only=True,
        required=True,
        min_length=8,
        style={"input_type": "password"},
        help_text=_(
            "New password (min 8 characters, must include uppercase, lowercase, and digit)",
        ),
    )
    new_password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={"input_type": "password"},
        help_text=_("New password confirmation (must match new_password)"),
    )

    def validate_new_password(self, value):
        """Validate password strength (AC #6)."""
        if len(value) < 8:
            raise serializers.ValidationError(
                _("Password must be at least 8 characters long."),
            )
        if not re.search(r"[A-Z]", value):
            raise serializers.ValidationError(
                _("Password must contain at least one uppercase letter."),
            )
        if not re.search(r"[a-z]", value):
            raise serializers.ValidationError(
                _("Password must contain at least one lowercase letter."),
            )
        if not re.search(r"\d", value):
            raise serializers.ValidationError(
                _("Password must contain at least one digit."),
            )

        try:
            validate_password(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))

        return value

    def validate(self, attrs):
        """Validate passwords match and token is valid."""
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": _("Passwords do not match.")},
            )

        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode

        try:
            uid = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"detail": _("Invalid reset link.")})

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError(
                {"detail": _("Invalid or expired reset link.")},
            )

        attrs["user"] = user
        return attrs


class TokenRefreshRequestSerializer(serializers.Serializer):
    """
    Serializer for token refresh request (OAuth 2.0 compliant).

    Accepts refresh token and returns a new access token.
    Supports both 'refresh_token' (OAuth 2.0 standard) and 'refresh' (SimpleJWT default).
    """

    refresh_token = serializers.CharField(
        required=True,
        write_only=True,
        help_text=_("JWT refresh token (valid for 14 days)"),
    )


class TokenRefreshResponseSerializer(serializers.Serializer):
    """
    Serializer for token refresh response (OAuth 2.0 compliant).

    Returns new access token and optionally a new refresh token.
    """

    access_token = serializers.CharField(
        read_only=True,
        help_text=_("New JWT access token (valid for 30 minutes)"),
    )
    refresh_token = serializers.CharField(
        read_only=True,
        required=False,
        help_text=_("New JWT refresh token (only if rotation is enabled)"),
    )


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile including analytics preferences.

    Allows users to manage their profile settings including:
    - Preferred language (Arabic or English)
    - Timezone for localized date/time display
    - Analytics consent (opt-in/opt-out for usage tracking)
    """

    is_analytics_enabled = serializers.BooleanField(
        source="user.is_analytics_enabled",
        required=False,
        help_text=_(
            "User consent for usage analytics tracking "
            "(true to opt-in, false to opt-out)",
        ),
    )

    class Meta:
        model = UserProfile
        fields = ["preferred_language", "timezone", "is_analytics_enabled"]
        read_only_fields = []
        extra_kwargs = {
            "preferred_language": {
                "help_text": _(
                    "Preferred language for API responses "
                    "(ar for Arabic, en for English)",
                ),
            },
            "timezone": {
                "help_text": _(
                    "User's timezone for localized date/time display "
                    "(e.g., 'UTC', 'Asia/Riyadh')",
                ),
            },
        }

    def update(self, instance, validated_data):
        """Update profile and handle analytics preference if provided."""
        # Extract user-related data
        user_data = validated_data.pop("user", {})

        # Update UserProfile fields
        instance = super().update(instance, validated_data)

        # Update User.is_analytics_enabled if provided using queryset update
        if "is_analytics_enabled" in user_data:
            User.objects.filter(pk=instance.user.pk).update(
                is_analytics_enabled=user_data["is_analytics_enabled"],
            )

        return instance

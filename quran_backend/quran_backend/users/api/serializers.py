import re

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from quran_backend.users.models import User
from quran_backend.users.models import UserProfile


class UserSerializer(serializers.ModelSerializer[User]):
    class Meta:
        model = User
        fields = ["username", "name", "url"]

        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "username"},
        }


class UserRegistrationSerializer(serializers.Serializer):
    """Serializer for user registration with email and password."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, required=True)

    def validate_email(self, value):
        """Validate that email is unique."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value.lower()

    def validate_password(self, value):
        """Validate password strength requirements (AC #6)."""
        # Minimum 8 characters
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long.",
            )

        # Complexity validation: uppercase, lowercase, digit
        if not re.search(r"[A-Z]", value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter.",
            )
        if not re.search(r"[a-z]", value):
            raise serializers.ValidationError(
                "Password must contain at least one lowercase letter.",
            )
        if not re.search(r"\d", value):
            raise serializers.ValidationError(
                "Password must contain at least one digit.",
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
                {"password_confirm": "Passwords do not match."},
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
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        }


class UserLoginSerializer(serializers.Serializer):
    """Serializer for user login with email and password."""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(write_only=True, required=True)

    def validate(self, attrs):
        """Authenticate user and return user object (AC #2)."""
        from django.contrib.auth import authenticate

        email = attrs.get("email")
        password = attrs.get("password")

        user = authenticate(username=email, password=password)

        if user is None:
            raise serializers.ValidationError(
                {"detail": "Invalid email or password."},
            )

        if not user.is_active:
            raise serializers.ValidationError(
                {"detail": "User account is disabled."},
            )

        attrs["user"] = user
        return attrs

    def to_representation(self, instance):
        """Return JWT tokens (AC #2, #7, #8)."""
        user = self.validated_data["user"]
        refresh = RefreshToken.for_user(user)

        return {
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        }


class PasswordResetRequestSerializer(serializers.Serializer):
    """Serializer for password reset request (AC #4)."""

    email = serializers.EmailField(required=True)

    def validate_email(self, value):
        """Validate that email exists."""
        if not User.objects.filter(email=value).exists():
            # Don't reveal whether email exists for security
            pass
        return value.lower()


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Serializer for password reset confirmation (AC #5)."""

    token = serializers.CharField(required=True)
    uid = serializers.CharField(required=True)
    new_password = serializers.CharField(write_only=True, required=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, required=True)

    def validate_new_password(self, value):
        """Validate password strength (AC #6)."""
        if len(value) < 8:
            raise serializers.ValidationError(
                "Password must be at least 8 characters long.",
            )
        if not re.search(r"[A-Z]", value):
            raise serializers.ValidationError(
                "Password must contain at least one uppercase letter.",
            )
        if not re.search(r"[a-z]", value):
            raise serializers.ValidationError(
                "Password must contain at least one lowercase letter.",
            )
        if not re.search(r"\d", value):
            raise serializers.ValidationError(
                "Password must contain at least one digit.",
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
                {"new_password_confirm": "Passwords do not match."},
            )

        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_str
        from django.utils.http import urlsafe_base64_decode

        try:
            uid = force_str(urlsafe_base64_decode(attrs["uid"]))
            user = User.objects.get(pk=uid)
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError({"detail": "Invalid reset link."})

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError(
                {"detail": "Invalid or expired reset link."},
            )

        attrs["user"] = user
        return attrs

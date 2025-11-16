import uuid

import pytest

from backend.users.models import User
from backend.users.models import UserProfile


def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == f"/users/{user.username}/"


@pytest.mark.django_db
class TestUserModel:
    """Test cases for custom User model."""

    def test_user_has_uuid_primary_key(self):
        """Test that User model uses UUID as primary key (AC #14)."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        assert isinstance(user.id, uuid.UUID)
        assert user.pk == user.id

    def test_user_email_is_unique(self):
        """Test that email field is unique (AC #1)."""
        User.objects.create_user(
            username="user1",
            email="test@example.com",
            password="TestPass123!",
        )
        with pytest.raises(Exception):  # IntegrityError
            User.objects.create_user(
                username="user2",
                email="test@example.com",
                password="TestPass123!",
            )

    def test_user_email_is_username_field(self):
        """Test that email is used as USERNAME_FIELD for authentication."""
        assert User.USERNAME_FIELD == "email"

    def test_user_is_analytics_enabled_default_false(self):
        """Test that is_analytics_enabled defaults to False."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        assert user.is_analytics_enabled is False

    def test_user_password_is_hashed(self):
        """Test that passwords are hashed using Django's password hashers (AC #13)."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        # Password should be hashed (not plaintext)
        # In production it uses PBKDF2, but tests may use faster hashers like MD5
        assert user.password != "TestPass123!"
        assert "$" in user.password  # All Django hashers use $ as separator
        # Verify password authentication works correctly
        assert user.check_password("TestPass123!")


@pytest.mark.django_db
class TestUserProfileModel:
    """Test cases for UserProfile model."""

    def test_userprofile_created_with_user(self):
        """Test that UserProfile can be created with one-to-one relationship (AC #15)."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        profile = UserProfile.objects.create(user=user)
        assert profile.user == user
        assert user.profile == profile

    def test_userprofile_default_language_is_arabic(self):
        """Test that preferred_language defaults to 'ar'."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        profile = UserProfile.objects.create(user=user)
        assert profile.preferred_language == "ar"

    def test_userprofile_default_timezone_is_utc(self):
        """Test that timezone defaults to 'UTC'."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        profile = UserProfile.objects.create(user=user)
        assert profile.timezone == "UTC"

    def test_userprofile_str_method(self):
        """Test UserProfile string representation."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        profile = UserProfile.objects.create(user=user)
        assert str(profile) == "Profile for test@example.com"

    def test_userprofile_cascade_delete(self):
        """Test that UserProfile is deleted when User is deleted."""
        user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="TestPass123!",
        )
        profile = UserProfile.objects.create(user=user)
        profile_id = profile.user_id

        user.delete()
        assert not UserProfile.objects.filter(user_id=profile_id).exists()

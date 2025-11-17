import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework.test import APIRequestFactory

from backend.users.api.views import UserViewSet
from backend.users.models import User
from backend.users.models import UserProfile


class TestUserViewSet:
    @pytest.fixture
    def api_rf(self) -> APIRequestFactory:
        return APIRequestFactory()

    def test_get_queryset(self, user: User, api_rf: APIRequestFactory):
        view = UserViewSet()
        request = api_rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert user in view.get_queryset()

    def test_me(self, user: User, api_rf: APIRequestFactory):
        view = UserViewSet()
        request = api_rf.get("/fake-url/")
        request.user = user

        view.request = request

        response = view.me(request)  # type: ignore[call-arg, arg-type, misc]

        assert response.data == {
            "username": user.username,
            "url": f"http://testserver/api/users/{user.username}/",
            "name": user.name,
        }


@pytest.mark.django_db
class TestUserRegistrationView:
    """Test cases for user registration endpoint (AC #1, #6, #13, #14, #15)."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    def test_register_with_valid_data_returns_201_and_tokens(self, api_client):
        """Test successful registration returns 201 with user data and JWT tokens (AC #1, #2)."""
        url = reverse("api:auth-register")
        data = {
            "email": "newuser@example.com",
            "password": "TestPass123",
            "password_confirm": "TestPass123",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert "user" in response.data
        assert "tokens" in response.data
        assert response.data["user"]["email"] == "newuser@example.com"
        assert "access_token" in response.data["tokens"]
        assert "refresh_token" in response.data["tokens"]

        # Verify user was created
        user = User.objects.get(email="newuser@example.com")
        assert user.check_password("TestPass123")

        # Verify UserProfile was created (AC #15)
        assert hasattr(user, "profile")
        assert user.profile.preferred_language == "ar"
        assert user.profile.timezone == "UTC"

    def test_register_with_invalid_email_returns_400(self, api_client):
        """Test registration with invalid email format returns 400 (AC #1)."""
        url = reverse("api:auth-register")
        data = {
            "email": "invalid-email",
            "password": "TestPass123",
            "password_confirm": "TestPass123",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_register_with_duplicate_email_returns_400(self, api_client, user):
        """Test registration with existing email returns 400 (AC #1)."""
        url = reverse("api:auth-register")
        data = {
            "email": user.email,
            "password": "TestPass123",
            "password_confirm": "TestPass123",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "email" in response.data

    def test_register_with_weak_password_returns_400(self, api_client):
        """Test registration with weak password returns 400 (AC #6)."""
        url = reverse("api:auth-register")

        # Test password too short
        response = api_client.post(
            url,
            {
                "email": "test@example.com",
                "password": "Short1",
                "password_confirm": "Short1",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data

        # Test password without uppercase
        response = api_client.post(
            url,
            {
                "email": "test@example.com",
                "password": "testpass123",
                "password_confirm": "testpass123",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data

        # Test password without digit
        response = api_client.post(
            url,
            {
                "email": "test@example.com",
                "password": "TestPassword",
                "password_confirm": "TestPassword",
            },
            format="json",
        )
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password" in response.data

    def test_register_with_mismatched_passwords_returns_400(self, api_client):
        """Test registration with mismatched passwords returns 400."""
        url = reverse("api:auth-register")
        data = {
            "email": "test@example.com",
            "password": "TestPass123",
            "password_confirm": "DifferentPass123",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "password_confirm" in response.data

    def test_register_creates_user_with_uuid_primary_key(self, api_client):
        """Test that registered user has UUID primary key (AC #14)."""
        url = reverse("api:auth-register")
        data = {
            "email": "uuid@example.com",
            "password": "TestPass123",
            "password_confirm": "TestPass123",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        user = User.objects.get(email="uuid@example.com")
        assert str(user.id) == response.data["user"]["id"]
        # UUID will be in the format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
        assert len(str(user.id)) == 36


@pytest.mark.django_db
class TestUserLoginView:
    """Test cases for user login endpoint (AC #2, #7, #8)."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def test_user(self):
        """Create a test user for login tests."""
        user = User.objects.create_user(
            username="testlogin",
            email="login@example.com",
            password="TestPass123",
        )
        UserProfile.objects.create(user=user)
        return user

    def test_login_with_valid_credentials_returns_200_and_tokens(
        self,
        api_client,
        test_user,
    ):
        """Test successful login returns 200 with JWT tokens (AC #2, #7, #8)."""
        url = reverse("api:auth-login")
        data = {
            "email": "login@example.com",
            "password": "TestPass123",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "tokens" in response.data
        assert "access_token" in response.data["tokens"]
        assert "refresh_token" in response.data["tokens"]

    def test_login_with_invalid_credentials_returns_400(self, api_client, test_user):
        """Test login with wrong password returns 400."""
        url = reverse("api:auth-login")
        data = {
            "email": "login@example.com",
            "password": "WrongPassword123",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "detail" in response.data


@pytest.mark.django_db
class TestTokenRefreshView:
    """Test cases for token refresh endpoint (AC #9)."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    def test_token_refresh_with_valid_token_returns_new_access_token(
        self,
        api_client,
        user,
    ):
        """Test token refresh returns new access token (AC #9)."""
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)
        url = reverse("api:auth-token-refresh")
        data = {"refresh_token": str(refresh)}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "access_token" in response.data


@pytest.mark.django_db
class TestPasswordResetViews:
    """Test cases for password reset endpoints (AC #4, #5, #6)."""

    @pytest.fixture
    def api_client(self):
        return APIClient()

    @pytest.fixture
    def test_user(self):
        """Create test user for password reset."""
        user = User.objects.create_user(
            username="resetuser",
            email="reset@example.com",
            password="OldPass123",
        )
        UserProfile.objects.create(user=user)
        return user

    def test_password_reset_request_returns_200(self, api_client, test_user):
        """Test password reset request returns 200 (AC #4)."""
        url = reverse("api:auth-password-reset")
        data = {"email": "reset@example.com"}

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

    def test_password_reset_confirm_with_valid_token_returns_200(
        self,
        api_client,
        test_user,
    ):
        """Test password reset confirmation with valid token (AC #5, #6)."""
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        # Generate reset token
        token = default_token_generator.make_token(test_user)
        uid = urlsafe_base64_encode(force_bytes(test_user.pk))

        url = reverse("api:auth-password-reset-confirm")
        data = {
            "uid": uid,
            "token": token,
            "new_password": "NewPass123",
            "new_password_confirm": "NewPass123",
        }

        response = api_client.post(url, data, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert "message" in response.data

        # Verify password was changed
        test_user.refresh_from_db()
        assert test_user.check_password("NewPass123")

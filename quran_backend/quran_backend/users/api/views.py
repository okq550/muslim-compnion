import logging

from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import ListModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.mixins import UpdateModelMixin
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView

from quran_backend.users.models import User
from quran_backend.users.models import UserProfile
from quran_backend.users.services.account_lockout import AccountLockoutService

from .serializers import PasswordResetConfirmSerializer
from .serializers import PasswordResetRequestSerializer
from .serializers import UserLoginSerializer
from .serializers import UserProfileSerializer
from .serializers import UserRegistrationSerializer
from .serializers import UserSerializer
from .throttling import AuthEndpointThrottle

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract client IP address from request."""
    x_forwarded_for = request.headers.get("x-forwarded-for")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


class UserViewSet(RetrieveModelMixin, ListModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = UserSerializer
    queryset = User.objects.all()
    lookup_field = "username"

    def get_queryset(self, *args, **kwargs):
        # User.id is now UUID (changed in Task 1)
        return self.queryset.filter(id=self.request.user.id)

    @action(detail=False)
    def me(self, request):
        serializer = UserSerializer(request.user, context={"request": request})
        return Response(status=status.HTTP_200_OK, data=serializer.data)


class UserRegistrationView(APIView):
    """
    API endpoint for user registration (AC #1, #6, #13, #14, #15).

    POST /api/v1/auth/register/
    - Creates new user with email and password
    - Returns user data with JWT tokens
    - Requires: email, password, password_confirm
    - Returns: 201 Created with user and tokens
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Handle user registration request."""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(
                serializer.to_representation(user),
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """
    API endpoint for user login (AC #2, #7, #8, #12).

    POST /api/v1/auth/login/
    - Authenticates user with email and password
    - Returns JWT access and refresh tokens
    - Requires: email, password
    - Returns: 200 OK with tokens
    - Returns: 423 Locked if account is locked due to failed attempts
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]  # Rate limit: 5/min (AC #10, #11)

    def post(self, request):
        """Handle user login request with account lockout protection."""
        email = request.data.get("email", "").lower()
        ip_address = get_client_ip(request)

        # Check if account is locked (AC #12)
        is_locked, seconds_remaining = AccountLockoutService.is_locked(email)
        if is_locked:
            minutes_remaining = (seconds_remaining + 59) // 60  # Round up
            return Response(
                {
                    "detail": _(
                        "Account temporarily locked due to multiple failed "
                        "login attempts. Try again in %s minutes.",
                    )
                    % minutes_remaining,
                    "retry_after": seconds_remaining,
                },
                status=status.HTTP_423_LOCKED,
            )

        # Attempt authentication
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            # Successful login - reset attempt counter
            AccountLockoutService.reset_attempts(email)
            return Response(
                serializer.to_representation(serializer.validated_data),
                status=status.HTTP_200_OK,
            )

        # Failed login - record attempt
        AccountLockoutService.record_failed_attempt(email, ip_address)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLogoutView(APIView):
    """
    API endpoint for user logout (AC #3).

    POST /api/v1/auth/logout/
    - Blacklists refresh token immediately
    - Requires: refresh token in body
    - Returns: 200 OK with success message
    """

    permission_classes = [AllowAny]  # Allow any since we're just accepting token

    def post(self, request):
        """Handle user logout request and blacklist token."""
        refresh_token = request.data.get("refresh_token")

        if not refresh_token:
            return Response(
                {"detail": _("Refresh token is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            # Decode and blacklist the refresh token
            token = RefreshToken(refresh_token)
            token.blacklist()
        except TokenError:
            # Token is invalid or already blacklisted
            return Response(
                {"detail": _("Invalid or expired token.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {"message": _("Successfully logged out")},
            status=status.HTTP_200_OK,
        )


class PasswordResetRequestView(APIView):
    """
    API endpoint for password reset request (AC #4).

    POST /api/v1/auth/password/reset/
    - Sends reset email with token link
    - Requires: email
    - Returns: 200 OK (always, for security)
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]  # Rate limit: 5/min (AC #10, #12)

    def post(self, request):
        """Handle password reset request."""
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]

            try:
                user = User.objects.get(email=email)
                # Generate reset token and uid
                _token = default_token_generator.make_token(user)
                _uid = urlsafe_base64_encode(force_bytes(user.pk))

                # TODO: In production, send email here with reset link
                # Email should contain:
                # {FRONTEND_URL}/reset-password?uid={uid}&token={token}

                # Log the reset attempt for security monitoring
                logger.info("Password reset requested for user: %s", user.id)

                return Response(
                    {"message": _("Password reset email sent if account exists")},
                    status=status.HTTP_200_OK,
                )
            except User.DoesNotExist:
                pass

            # Always return success for security (don't reveal if email exists)
            return Response(
                {"message": _("Password reset email sent if account exists")},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ThrottledTokenRefreshView(TokenRefreshView):
    """
    Token refresh endpoint with rate limiting.

    POST /api/v1/auth/token/refresh/
    - Refreshes JWT access token using refresh token
    - Rate limited to 5 requests per minute per user
    - Returns: 200 OK with new access token
    """

    throttle_classes = [AuthEndpointThrottle]

    def post(self, request, *args, **kwargs):
        """Override to use OAuth 2.0 standard parameter names (ADR-012)."""
        # Accept both 'refresh_token' (OAuth 2.0) and 'refresh' (SimpleJWT default)
        if "refresh_token" in request.data and "refresh" not in request.data:
            request.data["refresh"] = request.data["refresh_token"]

        response = super().post(request, *args, **kwargs)

        # Rename response keys for OAuth 2.0 compliance (ADR-012)
        if response.status_code == 200:
            if "access" in response.data:
                response.data["access_token"] = response.data.pop("access")
            if "refresh" in response.data:
                response.data["refresh_token"] = response.data.pop("refresh")

        return response


class PasswordResetConfirmView(APIView):
    """
    API endpoint for password reset confirmation (AC #5).

    POST /api/v1/auth/password/reset/confirm/
    - Validates token and resets password
    - Requires: uid, token, new_password, new_password_confirm
    - Returns: 200 OK with success message
    """

    permission_classes = [AllowAny]

    @transaction.atomic
    def post(self, request):
        """Handle password reset confirmation with transaction protection (AC #6)."""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            user.set_password(serializer.validated_data["new_password"])
            user.save()

            return Response(
                {"message": _("Password has been reset successfully")},
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserProfileViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    """
    API endpoint for user profile management including analytics preferences.

    GET /api/v1/users/profile/ - Retrieve current user's profile
    PATCH /api/v1/users/profile/ - Update current user's profile (including is_analytics_enabled)
    """

    serializer_class = UserProfileSerializer
    queryset = UserProfile.objects.all()

    def get_object(self):
        """Return the current user's profile."""
        return self.request.user.profile

    def retrieve(self, request, *args, **kwargs):
        """Retrieve current user's profile."""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def partial_update(self, request, *args, **kwargs):
        """Update current user's profile (PATCH)."""
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

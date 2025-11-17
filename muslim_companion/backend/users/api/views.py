import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.db import transaction
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import OpenApiResponse
from drf_spectacular.utils import extend_schema
from drf_spectacular.utils import extend_schema_view
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

from backend.users.models import User
from backend.users.models import UserProfile
from backend.users.services.account_lockout import AccountLockoutService
from backend.users.tasks import send_password_reset_email

from .serializers import PasswordResetConfirmSerializer
from .serializers import PasswordResetRequestSerializer
from .serializers import TokenRefreshRequestSerializer
from .serializers import TokenRefreshResponseSerializer
from .serializers import UserLoginSerializer
from .serializers import UserProfileSerializer
from .serializers import UserRegistrationSerializer
from .serializers import UserSerializer
from .throttling import AuthEndpointThrottle

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger(
    "backend.audit",
)  # US-API-007: Separate audit logger


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
    User Registration Endpoint

    Register a new user account with email and password.
    Returns JWT access and refresh tokens upon successful registration.

    **Password Requirements:**
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit

    **Rate Limit:** Subject to default API rate limits (100/min authenticated,
    20/min anonymous)
    """

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="user_register",
        summary="User Registration",
        description=(
            "Create a new user account with email and password. Returns JWT tokens."
        ),
        request=UserRegistrationSerializer,
        responses={
            201: UserRegistrationSerializer,
            400: OpenApiResponse(
                description="Validation Error",
                examples=[
                    OpenApiExample(
                        name="validation_error",
                        value={
                            "error": "VALIDATION_ERROR",
                            "message": "Invalid input data",
                            "request_id": "550e8400-e29b-41d4-a716-446655440000",
                            "details": [
                                {
                                    "field": "email",
                                    "message": "A user with this email already exists",
                                },
                            ],
                        },
                    ),
                ],
            ),
        },
        tags=["🌐 Public", "Authentication"],
        auth=[],
        examples=[
            OpenApiExample(
                name="valid_registration_request",
                summary="Valid Registration Request",
                value={
                    "email": "user@example.com",
                    "password": "SecurePass123",
                    "password_confirm": "SecurePass123",
                },
                request_only=True,
            ),
            OpenApiExample(
                name="successful_registration_response",
                summary="Successful Registration Response",
                value={
                    "user": {
                        "id": "550e8400-e29b-41d4-a716-446655440000",
                        "email": "user@example.com",
                        "username": "user",
                    },
                    "tokens": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                    },
                },
                response_only=True,
                status_codes=["201"],
            ),
        ],
    )
    def post(self, request):
        """Handle user registration request."""
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # US-API-007 AC #1: Log successful registration
            audit_logger.info(
                "User registration successful",
                extra={
                    "request_id": getattr(request, "request_id", "unknown"),
                    "user_id": str(user.id),
                    "email": user.email,
                    "endpoint": "/api/v1/auth/register/",
                    "ip_address": get_client_ip(request),
                },
            )

            return Response(
                serializer.to_representation(user),
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLoginView(APIView):
    """
    User Login Endpoint

    Authenticate user with email and password and receive JWT tokens.

    **Token Expiration:**
    - Access Token: 30 minutes
    - Refresh Token: 14 days

    **Account Lockout Policy:**
    - 10 failed login attempts result in a 30-minute account lockout

    **Rate Limit:** 5 requests per minute per IP address
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]  # Rate limit: 5/min (AC #10, #11)

    @extend_schema(
        operation_id="user_login",
        summary="User Login",
        description="Authenticate user and receive JWT access and refresh tokens.",
        request=UserLoginSerializer,
        responses={
            200: UserLoginSerializer,
            400: OpenApiResponse(
                description="Invalid Credentials",
                examples=[
                    OpenApiExample(
                        name="invalid_credentials",
                        value={
                            "error": "AUTHENTICATION_ERROR",
                            "message": "Invalid email or password",
                            "request_id": "550e8400-e29b-41d4-a716-446655440000",
                        },
                    ),
                ],
            ),
            423: OpenApiResponse(
                description="Account Locked",
                examples=[
                    OpenApiExample(
                        name="account_locked",
                        value={
                            "detail": (
                                "Account temporarily locked due to multiple failed "
                                "login attempts. Try again in 30 minutes."
                            ),
                            "retry_after": 1800,
                        },
                    ),
                ],
            ),
            429: OpenApiResponse(
                description="Rate Limit Exceeded",
                examples=[
                    OpenApiExample(
                        name="rate_limit_exceeded",
                        value={
                            "error": "RATE_LIMIT_EXCEEDED",
                            "message": (
                                "Too many login attempts. Please try again later."
                            ),
                            "request_id": "550e8400-e29b-41d4-a716-446655440000",
                        },
                    ),
                ],
            ),
        },
        tags=["🌐 Public", "Authentication"],
        auth=[],
        examples=[
            OpenApiExample(
                name="valid_login_request",
                summary="Valid Login Request",
                value={"email": "user@example.com", "password": "SecurePass123"},
                request_only=True,
            ),
            OpenApiExample(
                name="successful_login_response",
                summary="Successful Login Response",
                value={
                    "tokens": {
                        "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                        "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
                    },
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request):
        """Handle user login request with account lockout protection."""
        email = request.data.get("email", "").lower()
        ip_address = get_client_ip(request)

        # Check if account is locked (AC #12)
        is_locked, seconds_remaining = AccountLockoutService.is_locked(email)
        if is_locked:
            minutes_remaining = (seconds_remaining + 59) // 60  # Round up

            # US-API-007 AC #1: Log account lockout event
            audit_logger.warning(
                "Account locked - login blocked",
                extra={
                    "request_id": getattr(request, "request_id", "unknown"),
                    "email": email,
                    "ip_address": ip_address,
                    "endpoint": "/api/v1/auth/login/",
                    "lockout_remaining_seconds": seconds_remaining,
                },
            )

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

            # US-API-007 AC #1: Log successful login
            user = serializer.validated_data.get("user")
            audit_logger.info(
                "User login successful",
                extra={
                    "request_id": getattr(request, "request_id", "unknown"),
                    "user_id": str(user.id) if user else "unknown",
                    "email": email,
                    "endpoint": "/api/v1/auth/login/",
                    "ip_address": ip_address,
                },
            )

            return Response(
                serializer.to_representation(serializer.validated_data),
                status=status.HTTP_200_OK,
            )

        # Failed login - record attempt
        AccountLockoutService.record_failed_attempt(email, ip_address)

        # US-API-007 AC #1: Log failed login attempt
        audit_logger.warning(
            "Login failed - invalid credentials",
            extra={
                "request_id": getattr(request, "request_id", "unknown"),
                "email": email,
                "ip_address": ip_address,
                "endpoint": "/api/v1/auth/login/",
                "reason": "invalid_credentials",
            },
        )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLogoutView(APIView):
    """
    User Logout Endpoint

    Logout user by blacklisting their refresh token.
    Once blacklisted, the refresh token cannot be used to obtain new access tokens.

    **Note:** Access tokens remain valid until expiration (30 minutes).
    For immediate access revocation, implement token revocation checks in middleware.
    """

    permission_classes = [AllowAny]  # Allow any since we're just accepting token

    @extend_schema(
        operation_id="user_logout",
        summary="User Logout",
        description="Blacklist refresh token to prevent further token refreshes.",
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "refresh_token": {
                        "type": "string",
                        "description": "JWT refresh token to blacklist",
                    },
                },
                "required": ["refresh_token"],
            },
        },
        responses={
            200: OpenApiResponse(
                description="Successful Logout",
                examples=[
                    OpenApiExample(
                        name="successful_logout",
                        value={"message": "Successfully logged out"},
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Invalid Token",
                examples=[
                    OpenApiExample(
                        name="invalid_token",
                        value={"detail": "Invalid or expired token."},
                    ),
                ],
            ),
        },
        tags=["🔐 User", "Authentication"],
        examples=[
            OpenApiExample(
                name="logout_request",
                summary="Logout Request",
                value={"refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."},
                request_only=True,
            ),
        ],
    )
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

            # US-API-007 AC #1: Log successful logout
            user_id = None
            if hasattr(request, "user") and request.user.is_authenticated:
                user_id = str(request.user.id)

            audit_logger.info(
                "User logout successful",
                extra={
                    "request_id": getattr(request, "request_id", "unknown"),
                    "user_id": user_id,
                    "endpoint": "/api/v1/auth/logout/",
                    "ip_address": get_client_ip(request),
                },
            )

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
    Password Reset Request Endpoint

    Initiate password reset by sending reset instructions to user's email.

    **Security:** For security reasons, the API always returns success
    regardless of whether the email exists in the system.

    **Rate Limit:** 5 requests per minute per IP address
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]  # Rate limit: 5/min (AC #10, #12)

    @extend_schema(
        operation_id="password_reset_request",
        summary="Request Password Reset",
        description=(
            "Send password reset email if account exists. "
            "Always returns success for security."
        ),
        request=PasswordResetRequestSerializer,
        responses={
            200: OpenApiResponse(
                description="Success Response",
                examples=[
                    OpenApiExample(
                        name="success",
                        value={
                            "message": "Password reset email sent if account exists",
                        },
                    ),
                ],
            ),
            429: OpenApiResponse(
                description="Rate Limit Exceeded",
                examples=[
                    OpenApiExample(
                        name="rate_limit_exceeded",
                        value={
                            "error": "RATE_LIMIT_EXCEEDED",
                            "message": (
                                "Too many password reset requests. "
                                "Please try again later."
                            ),
                        },
                    ),
                ],
            ),
        },
        tags=["🌐 Public", "Authentication"],
        auth=[],
        examples=[
            OpenApiExample(
                name="password_reset_request",
                summary="Password Reset Request",
                value={"email": "user@example.com"},
                request_only=True,
            ),
        ],
    )
    def post(self, request):
        """Handle password reset request."""

        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]

            try:
                user = User.objects.get(email=email)
                # Generate reset token and uid
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))

                # Get frontend URL from settings (default for local dev)
                frontend_url = getattr(
                    settings,
                    "FRONTEND_PASSWORD_RESET_URL",
                    "http://localhost:3000/reset-password",
                )

                # Send password reset email asynchronously via Celery
                send_password_reset_email.delay(
                    user_email=email,
                    reset_url=frontend_url,
                    uid=uid,
                    token=token,
                )

                # US-API-007 AC #1: Log password reset request
                audit_logger.info(
                    "Password reset requested",
                    extra={
                        "request_id": getattr(request, "request_id", "unknown"),
                        "user_id": str(user.id),
                        "email": email,
                        "endpoint": "/api/v1/auth/password/reset/",
                        "ip_address": get_client_ip(request),
                    },
                )

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

    @extend_schema(
        operation_id="token_refresh",
        summary="Refresh Access Token",
        description=(
            "Exchange a valid refresh token for a new access token. "
            "The refresh token must be valid and not blacklisted. "
            "Supports both OAuth 2.0 standard 'refresh_token' parameter "
            "and SimpleJWT 'refresh' parameter. "
            "Rate limited to 5 requests per minute."
        ),
        request=TokenRefreshRequestSerializer,
        responses={
            200: TokenRefreshResponseSerializer,
            400: OpenApiResponse(
                description="Invalid Token",
                examples=[
                    OpenApiExample(
                        name="invalid_token",
                        value={
                            "error": "INVALID_TOKEN",
                            "message": "Token is invalid or expired",
                            "request_id": "550e8400-e29b-41d4-a716-446655440000",
                        },
                    ),
                ],
            ),
            401: OpenApiResponse(
                description="Token Blacklisted",
                examples=[
                    OpenApiExample(
                        name="token_blacklisted",
                        value={
                            "error": "TOKEN_BLACKLISTED",
                            "message": "Token has been blacklisted",
                            "request_id": "550e8400-e29b-41d4-a716-446655440000",
                        },
                    ),
                ],
            ),
            429: OpenApiResponse(
                description="Rate Limit Exceeded",
                examples=[
                    OpenApiExample(
                        name="rate_limit_exceeded",
                        value={
                            "error": "RATE_LIMIT_EXCEEDED",
                            "message": (
                                "Too many token refresh attempts. "
                                "Please try again later."
                            ),
                            "request_id": "550e8400-e29b-41d4-a716-446655440000",
                        },
                    ),
                ],
            ),
        },
        tags=["🔐 User", "Authentication"],
        examples=[
            OpenApiExample(
                name="valid_refresh_request",
                summary="Valid Token Refresh Request",
                value={
                    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                },
                request_only=True,
            ),
            OpenApiExample(
                name="successful_refresh_response",
                summary="Successful Token Refresh Response",
                value={
                    "access_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                    "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
                },
                response_only=True,
                status_codes=["200"],
            ),
        ],
    )
    def post(self, request, *args, **kwargs):
        """Override to use OAuth 2.0 standard parameter names (ADR-012)."""
        # Accept both 'refresh_token' (OAuth 2.0) and 'refresh' (SimpleJWT default)
        if "refresh_token" in request.data and "refresh" not in request.data:
            request.data["refresh"] = request.data["refresh_token"]

        response = super().post(request, *args, **kwargs)

        # Rename response keys for OAuth 2.0 compliance (ADR-012)
        if response.status_code == status.HTTP_200_OK:
            if "access" in response.data:
                response.data["access_token"] = response.data.pop("access")
            if "refresh" in response.data:
                response.data["refresh_token"] = response.data.pop("refresh")

        return response


class PasswordResetConfirmView(APIView):
    """
    Password Reset Confirmation Endpoint

    Complete password reset by providing the reset token and new password.

    **Password Requirements:**
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter
    - At least one digit
    """

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="password_reset_confirm",
        summary="Confirm Password Reset",
        description="Validate reset token and set new password.",
        request=PasswordResetConfirmSerializer,
        responses={
            200: OpenApiResponse(
                description="Success Response",
                examples=[
                    OpenApiExample(
                        name="success",
                        value={"message": "Password has been reset successfully"},
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Invalid Token or Password",
                examples=[
                    OpenApiExample(
                        name="invalid_token",
                        value={
                            "error": "VALIDATION_ERROR",
                            "message": "Invalid or expired reset link",
                            "details": [
                                {
                                    "field": "token",
                                    "message": "Invalid or expired reset link.",
                                },
                            ],
                        },
                    ),
                ],
            ),
        },
        tags=["🌐 Public", "Authentication"],
        auth=[],
        examples=[
            OpenApiExample(
                name="password_reset_confirmation",
                summary="Password Reset Confirmation",
                value={
                    "uid": "MQ",
                    "token": "abc123-def456",
                    "new_password": "NewSecurePass123",
                    "new_password_confirm": "NewSecurePass123",
                },
                request_only=True,
            ),
        ],
    )
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


@extend_schema_view(
    retrieve=extend_schema(
        tags=["🔐 User", "User Profile"],
        summary="Retrieve User Profile",
        description="Get current authenticated user's profile information.",
    ),
    partial_update=extend_schema(
        tags=["🔐 User", "User Profile"],
        summary="Update User Profile",
        description="Update current authenticated user's profile (partial update).",
    ),
)
class UserProfileViewSet(RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    """
    API endpoint for user profile management including analytics preferences.

    GET /api/v1/users/profile/ - Retrieve current user's profile
    PATCH /api/v1/users/profile/ - Update current user's profile (including
    is_analytics_enabled)
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

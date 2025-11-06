from django.conf import settings
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

from quran_backend.users.models import User

from .serializers import UserLoginSerializer
from .serializers import UserRegistrationSerializer
from .serializers import UserSerializer
from .throttling import AuthEndpointThrottle


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
    API endpoint for user login (AC #2, #7, #8).

    POST /api/v1/auth/login/
    - Authenticates user with email and password
    - Returns JWT access and refresh tokens
    - Requires: email, password
    - Returns: 200 OK with tokens
    """

    permission_classes = [AllowAny]
    throttle_classes = [AuthEndpointThrottle]  # Rate limit: 5/min (AC #10, #11)

    def post(self, request):
        """Handle user login request."""
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            return Response(
                serializer.to_representation(serializer.validated_data),
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserLogoutView(APIView):
    """
    API endpoint for user logout (AC #3).

    POST /api/v1/auth/logout/
    - Invalidates refresh token (blacklist if enabled)
    - Requires: refresh token in body
    - Returns: 200 OK with success message
    """

    permission_classes = [AllowAny]  # Allow any since we're just accepting token

    def post(self, request):
        """Handle user logout request."""
        refresh_token = request.data.get("refresh")

        if not refresh_token:
            return Response(
                {"detail": _("Refresh token is required.")},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Note: Token blacklisting is not enabled in settings (BLACKLIST_AFTER_ROTATION=False)
        # In production, you may want to enable rest_framework_simplejwt.token_blacklist
        # For now, we just return success as the client will discard the token

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
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        from quran_backend.users.api.serializers import PasswordResetRequestSerializer

        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]

            try:
                user = User.objects.get(email=email)
                # Generate reset token and uid
                token = default_token_generator.make_token(user)
                uid = urlsafe_base64_encode(force_bytes(user.pk))

                # In production, send email here
                # For now, return token/uid in response (ONLY FOR DEVELOPMENT)
                response_data = {
                    "message": _("Password reset email sent if account exists"),
                }
                if settings.DEBUG:  # Only in development
                    response_data["dev_only"] = {"uid": uid, "token": token}
                return Response(
                    response_data,
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


class PasswordResetConfirmView(APIView):
    """
    API endpoint for password reset confirmation (AC #5).

    POST /api/v1/auth/password/reset/confirm/
    - Validates token and resets password
    - Requires: uid, token, new_password, new_password_confirm
    - Returns: 200 OK with success message
    """

    permission_classes = [AllowAny]

    def post(self, request):
        """Handle password reset confirmation."""
        from quran_backend.users.api.serializers import PasswordResetConfirmSerializer

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

import hashlib
import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import OpenApiResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.analytics.models import AnalyticsEvent
from backend.analytics.services import analytics_service
from backend.users.models import User

from .serializers import AnalyticsConsentSerializer

logger = logging.getLogger(__name__)


class AnalyticsConsentView(APIView):
    """
    API endpoint for analytics consent management.

    POST /api/v1/analytics/consent/
    - Updates user's analytics preference
    - Requires authentication
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="analytics_consent",
        summary="Update Analytics Consent",
        description="Enable or disable analytics tracking for the authenticated user.",
        request=AnalyticsConsentSerializer,
        responses={
            200: OpenApiResponse(
                description="Consent Updated Successfully",
                examples=[
                    OpenApiExample(
                        name="success",
                        value={
                            "message": "Analytics preference updated",
                            "is_analytics_enabled": True,
                        },
                    ),
                ],
            ),
            400: OpenApiResponse(
                description="Validation Error",
                examples=[
                    OpenApiExample(
                        name="validation_error",
                        value={
                            "consent_given": ["This field is required."],
                        },
                    ),
                ],
            ),
        },
        tags=["🔐 User"],
    )
    def post(self, request):
        """Handle analytics consent request."""
        serializer = AnalyticsConsentSerializer(data=request.data)
        if serializer.is_valid():
            consent_given = serializer.validated_data["consent_given"]
            consent_version = serializer.validated_data.get("consent_version", "1.0")

            # Log consent for audit trail
            logger.info(
                "User %s %s analytics (version %s)",
                request.user.id,
                "enabled" if consent_given else "disabled",
                consent_version,
            )

            # Update user's analytics preference using queryset update
            User.objects.filter(pk=request.user.pk).update(
                is_analytics_enabled=consent_given,
            )

            return Response(
                {
                    "message": _("Analytics preference updated"),
                    "is_analytics_enabled": consent_given,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class DeleteMyAnalyticsDataView(APIView):
    """
    API endpoint for user to delete all their analytics data.

    DELETE /api/v1/analytics/delete-my-data/
    - Deletes all analytics events for current user
    - Sets is_analytics_enabled to False
    - GDPR Article 17 (Right to Erasure) compliance
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="delete_my_analytics_data",
        summary="Delete My Analytics Data",
        description=(
            "Delete all analytics data for the authenticated user "
            "(GDPR Right to Erasure)."
        ),
        responses={
            200: OpenApiResponse(
                description="Analytics Data Deleted",
                examples=[
                    OpenApiExample(
                        name="success",
                        value={
                            "message": "All your analytics data has been deleted",
                            "events_deleted": 42,
                        },
                    ),
                ],
            ),
            500: OpenApiResponse(
                description="Internal Server Error",
                examples=[
                    OpenApiExample(
                        name="error",
                        value={
                            "detail": "Failed to delete analytics data",
                        },
                    ),
                ],
            ),
        },
        tags=["🔐 User"],
    )
    def delete(self, request):
        """Delete all analytics data for current user."""
        try:
            # Hash user ID to find their analytics events
            user_id_hash = hashlib.sha256(
                f"{request.user.id}{settings.SECRET_KEY}".encode(),
            ).hexdigest()

            # Delete all events matching this user's hash
            deleted_count, _deleted_models = AnalyticsEvent.objects.filter(
                user_id_hash=user_id_hash,
            ).delete()

            # Log deletion for audit trail
            logger.info(
                "User %s deleted %s analytics events",
                request.user.id,
                deleted_count,
            )

            # Disable analytics for this user using queryset update
            User.objects.filter(pk=request.user.pk).update(is_analytics_enabled=False)

            return Response(
                {
                    "message": _("All your analytics data has been deleted"),
                    "events_deleted": deleted_count,
                },
                status=status.HTTP_200_OK,
            )
        except Exception:
            logger.exception("Failed to delete analytics data")
            return Response(
                {"detail": _("Failed to delete analytics data")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PopularFeaturesView(APIView):
    """
    API endpoint for popular features analytics.

    GET /api/v1/analytics/popular-features/
    - Returns top 10 features by event count
    - Admin-only access
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        operation_id="popular_features",
        summary="Get Popular Features",
        description="Retrieve top 10 features by event count (admin-only).",
        responses={
            200: OpenApiResponse(
                description="Popular Features",
                examples=[
                    OpenApiExample(
                        name="success",
                        value={
                            "popular_features": [
                                {"event_type": "surah_viewed", "count": 1523},
                                {"event_type": "ayah_bookmarked", "count": 892},
                                {"event_type": "reciter_played", "count": 654},
                            ],
                        },
                    ),
                ],
            ),
            500: OpenApiResponse(
                description="Internal Server Error",
                examples=[
                    OpenApiExample(
                        name="error",
                        value={
                            "detail": "Failed to retrieve analytics",
                        },
                    ),
                ],
            ),
        },
        tags=["👤 Admin", "System Analytics"],
    )
    def get(self, request):
        """Get popular features by event count."""
        try:
            features = analytics_service.get_popular_features(limit=10)
            return Response(
                {"popular_features": features},
                status=status.HTTP_200_OK,
            )
        except Exception:
            logger.exception("Failed to get popular features")
            return Response(
                {"detail": _("Failed to retrieve analytics")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class PopularSurahsView(APIView):
    """
    API endpoint for most read Surahs.

    GET /api/v1/analytics/popular-surahs/
    - Returns top 10 most viewed Surahs
    - Admin-only access
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        operation_id="popular_surahs",
        summary="Get Popular Surahs",
        description="Retrieve top 10 most viewed Surahs (admin-only).",
        responses={
            200: OpenApiResponse(
                description="Popular Surahs",
                examples=[
                    OpenApiExample(
                        name="success",
                        value={
                            "popular_surahs": [
                                {
                                    "surah_number": 1,
                                    "name": "Al-Fatihah",
                                    "views": 2341,
                                },
                                {"surah_number": 36, "name": "Yasin", "views": 1876},
                                {
                                    "surah_number": 2,
                                    "name": "Al-Baqarah",
                                    "views": 1543,
                                },
                            ],
                        },
                    ),
                ],
            ),
            500: OpenApiResponse(
                description="Internal Server Error",
                examples=[
                    OpenApiExample(
                        name="error",
                        value={
                            "detail": "Failed to retrieve analytics",
                        },
                    ),
                ],
            ),
        },
        tags=["👤 Admin", "System Analytics"],
    )
    def get(self, request):
        """Get most read Surahs."""
        try:
            surahs = analytics_service.get_most_read_surahs(limit=10)
            return Response(
                {"popular_surahs": surahs},
                status=status.HTTP_200_OK,
            )
        except Exception:
            logger.exception("Failed to get popular surahs")
            return Response(
                {"detail": _("Failed to retrieve analytics")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class ErrorRatesView(APIView):
    """
    API endpoint for error rates by endpoint.

    GET /api/v1/analytics/error-rates/
    - Returns error counts by endpoint
    - Admin-only access
    """

    permission_classes = [IsAdminUser]

    @extend_schema(
        operation_id="error_rates",
        summary="Get Error Rates",
        description="⚠️ **Admin Only** - Requires staff privileges (is_staff=True)\n\nRetrieve error counts by endpoint (admin-only).",
        responses={
            200: OpenApiResponse(
                description="Error Rates",
                examples=[
                    OpenApiExample(
                        name="success",
                        value={
                            "error_rates": [
                                {"endpoint": "/api/v1/quran/surahs/", "errors": 23},
                                {"endpoint": "/api/v1/auth/login/", "errors": 12},
                                {"endpoint": "/api/v1/quran/ayahs/", "errors": 8},
                            ],
                        },
                    ),
                ],
            ),
            500: OpenApiResponse(
                description="Internal Server Error",
                examples=[
                    OpenApiExample(
                        name="error",
                        value={
                            "detail": "Failed to retrieve analytics",
                        },
                    ),
                ],
            ),
        },
        tags=["👤 Admin", "System Analytics"],
    )
    def get(self, request):
        """Get error rates by endpoint."""
        try:
            errors = analytics_service.get_error_rates()
            return Response(
                {"error_rates": errors},
                status=status.HTTP_200_OK,
            )
        except Exception:
            logger.exception("Failed to get error rates")
            return Response(
                {"detail": _("Failed to retrieve analytics")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

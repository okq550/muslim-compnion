import hashlib
import logging

from django.conf import settings
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from quran_backend.analytics.models import AnalyticsEvent
from quran_backend.analytics.services import analytics_service

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

    def post(self, request):
        """Handle analytics consent request."""
        serializer = AnalyticsConsentSerializer(data=request.data)
        if serializer.is_valid():
            consent_given = serializer.validated_data["consent_given"]
            consent_version = serializer.validated_data.get("consent_version", "1.0")

            # Update user's analytics preference
            request.user.is_analytics_enabled = consent_given
            request.user.save()

            # Log consent for audit trail
            logger.info(
                f"User {request.user.id} {'enabled' if consent_given else 'disabled'} "
                f"analytics (version {consent_version})",
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

    def delete(self, request):
        """Delete all analytics data for current user."""
        try:
            # Hash user ID to find their analytics events
            user_id_hash = hashlib.sha256(
                f"{request.user.id}{settings.SECRET_KEY}".encode(),
            ).hexdigest()

            # Delete all events matching this user's hash
            deleted_count, _ = AnalyticsEvent.objects.filter(
                user_id_hash=user_id_hash,
            ).delete()

            # Disable analytics for this user
            request.user.is_analytics_enabled = False
            request.user.save()

            # Log deletion for audit trail
            logger.info(
                f"User {request.user.id} deleted {deleted_count} analytics events",
            )

            return Response(
                {
                    "message": _("All your analytics data has been deleted"),
                    "events_deleted": deleted_count,
                },
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Failed to delete analytics data: {e}")
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

    def get(self, request):
        """Get popular features by event count."""
        try:
            features = analytics_service.get_popular_features(limit=10)
            return Response(
                {"popular_features": features},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Failed to get popular features: {e}")
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

    def get(self, request):
        """Get most read Surahs."""
        try:
            surahs = analytics_service.get_most_read_surahs(limit=10)
            return Response(
                {"popular_surahs": surahs},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Failed to get popular surahs: {e}")
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

    def get(self, request):
        """Get error rates by endpoint."""
        try:
            errors = analytics_service.get_error_rates()
            return Response(
                {"error_rates": errors},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            logger.error(f"Failed to get error rates: {e}")
            return Response(
                {"detail": _("Failed to retrieve analytics")},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

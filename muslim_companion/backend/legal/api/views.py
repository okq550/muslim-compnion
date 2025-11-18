import logging

from drf_spectacular.utils import OpenApiExample
from drf_spectacular.utils import OpenApiResponse
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from backend.legal.models import PrivacyPolicy

from .serializers import PrivacyPolicySerializer

logger = logging.getLogger(__name__)


class PrivacyPolicyView(APIView):
    """
    API endpoint for retrieving privacy policy.

    GET /api/v1/legal/privacy-policy/
    - Returns latest active privacy policy
    - Public endpoint (no authentication required)
    """

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="privacy_policy",
        summary="Get Privacy Policy",
        description="Retrieve the latest active privacy policy (public endpoint).",
        responses={
            200: OpenApiResponse(
                description="Privacy Policy",
                examples=[
                    OpenApiExample(
                        name="privacy_policy",
                        value={
                            "content": "# Privacy Policy\n\n## What Data We Collect...",
                            "version": "1.0",
                            "effective_date": "2025-11-01",
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
                            "detail": "Error retrieving privacy policy",
                        },
                    ),
                ],
            ),
        },
        tags=["Public", "Legal & Privacy"],
        auth=[],
    )
    def get(self, request):
        """Retrieve the latest active privacy policy."""
        try:
            policy = PrivacyPolicy.objects.filter(is_active=True).first()
            if policy:
                serializer = PrivacyPolicySerializer(policy)
                return Response(serializer.data, status=status.HTTP_200_OK)

            # Return default policy if none exists in database
            default_policy = {
                "content": self._get_default_privacy_policy(),
                "version": "1.0",
                "effective_date": "2025-11-01",
            }
            return Response(default_policy, status=status.HTTP_200_OK)
        except Exception:
            logger.exception("Error retrieving privacy policy")
            return Response(
                {"detail": "Error retrieving privacy policy"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    def _get_default_privacy_policy(self) -> str:
        """Return default privacy policy content."""
        return """# Privacy Policy

## What Data We Collect

We collect anonymous usage analytics to improve the Muslim Companion API and
provide a better user experience. The data we collect includes:

- **Feature Usage Events**: Which features you use (e.g., Surah viewed,
  reciter played, translation selected, bookmark created)
- **Session Information**: Anonymous session IDs to track user flows
- **Performance Metrics**: API response times and error rates
- **Country-Level Location**: Your country code (2-letter ISO code) derived
  from your IP address - we do NOT store city, coordinates, or IP addresses

## What We DO NOT Collect

We prioritize your privacy and do NOT collect:

- Email addresses in analytics events
- Names or personally identifiable information
- IP addresses
- Device serial numbers or unique identifiers
- City-level or GPS coordinates
- User-generated content (search queries are anonymized - only query length
  tracked)

## User Identification

All user IDs are hashed using SHA-256 with a secret key salt, making them
irreversible and unlinkable to your actual account.

## Data Retention

- **Analytics Events**: Automatically deleted after 90 days
- **Aggregate Metrics**: Retained indefinitely with no user linkage
- **Your Data Deletion Right**: You can request immediate deletion of all
  your analytics data via the `/api/v1/analytics/delete-my-data/` endpoint

## Your Consent

Analytics tracking is **opt-in by default**. You can:

- Enable or disable analytics via your user profile: `/api/v1/users/profile/`
- Update your preference at any time
- Your choice persists across sessions

## GDPR Compliance

We comply with GDPR requirements:

- **Article 7 (Consent)**: Explicit opt-in required
- **Article 13 (Transparency)**: This policy explains all data collection
- **Article 17 (Right to Erasure)**: You can request data deletion at any time

## Contact

For privacy questions or data deletion requests, please contact:
privacy@quranbackend.example.com

**Last Updated**: November 2025
**Version**: 1.0
"""

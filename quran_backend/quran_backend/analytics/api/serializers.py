from rest_framework import serializers


class AnalyticsConsentSerializer(serializers.Serializer):
    """Serializer for analytics consent request."""

    consent_given = serializers.BooleanField(
        required=True,
        help_text="User consent for analytics tracking (true/false)",
    )
    consent_version = serializers.CharField(
        required=False,
        default="1.0",
        help_text="Privacy policy version user consented to",
    )

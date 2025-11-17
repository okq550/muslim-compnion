from rest_framework import serializers

from backend.legal.models import PrivacyPolicy


class PrivacyPolicySerializer(serializers.ModelSerializer):
    """Serializer for privacy policy display."""

    class Meta:
        model = PrivacyPolicy
        fields = ["content", "version", "effective_date"]
        read_only_fields = ["content", "version", "effective_date"]

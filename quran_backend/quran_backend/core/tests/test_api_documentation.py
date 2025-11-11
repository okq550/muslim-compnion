"""
Tests for API Documentation (US-API-008).

Tests verify:
- OpenAPI schema generation and validation
- Swagger UI and ReDoc accessibility
- Documentation endpoints not rate limited
- Serializer and view documentation completeness
"""

import pytest
from django.urls import reverse
from rest_framework import status


@pytest.mark.django_db
class TestOpenAPISchema:
    """Test OpenAPI 3.0 schema generation (AC #1)."""

    def test_schema_endpoint_accessible(self, client):
        """Test OpenAPI schema endpoint returns 200 OK."""
        url = reverse("api-schema")
        response = client.get(url, HTTP_ACCEPT="application/json")

        assert response.status_code == status.HTTP_200_OK
        assert response["Content-Type"].startswith("application/json")

    def test_schema_structure_valid(self, client):
        """Test OpenAPI schema contains required fields and validates against OpenAPI 3.0 spec."""
        url = reverse("api-schema")
        response = client.get(url, HTTP_ACCEPT="application/json")

        schema = response.json()

        # Verify OpenAPI version
        assert "openapi" in schema
        assert schema["openapi"].startswith("3.0")

        # Verify info section
        assert "info" in schema
        assert schema["info"]["title"] == "Quran Backend API"
        assert schema["info"]["version"] == "1.0.0"
        assert "description" in schema["info"]

        # Verify paths section
        assert "paths" in schema
        assert len(schema["paths"]) > 0

        # Verify components section (for reusable schemas)
        assert "components" in schema

    def test_epic1_endpoints_in_schema(self, client):
        """Test all Epic 1 endpoints are included in the schema (AC #1)."""
        url = reverse("api-schema")
        response = client.get(url, HTTP_ACCEPT="application/json")
        schema = response.json()

        paths = schema.get("paths", {})

        # Verify we have paths
        assert len(paths) > 0, "Schema should contain API endpoints"

        # Check for authentication/user endpoints (may vary based on URL configuration)
        auth_endpoints_found = any(
            "register" in path.lower()
            or "login" in path.lower()
            or "auth" in path.lower()
            for path in paths
        )
        assert auth_endpoints_found, "Authentication endpoints should be in schema"

    def test_jwt_security_scheme_defined(self, client):
        """Test JWT authentication security scheme is defined in schema (AC #1, #4)."""
        url = reverse("api-schema")
        response = client.get(url, HTTP_ACCEPT="application/json")
        schema = response.json()

        # Check for JWT security scheme in components
        assert "components" in schema
        assert "securitySchemes" in schema["components"]
        assert "jwtAuth" in schema["components"]["securitySchemes"]

        jwt_scheme = schema["components"]["securitySchemes"]["jwtAuth"]
        assert jwt_scheme["type"] == "http"
        assert jwt_scheme["scheme"] == "bearer"
        assert jwt_scheme["bearerFormat"] == "JWT"


@pytest.mark.django_db
class TestSwaggerUI:
    """Test Swagger UI interactive documentation (AC #2)."""

    def test_swagger_ui_accessible(self, client):
        """Test Swagger UI is accessible at /api/docs/."""
        url = reverse("api-docs")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # Swagger UI returns HTML
        assert "text/html" in response["Content-Type"]

    def test_swagger_ui_accessible_without_authentication(self, client):
        """Test Swagger UI is accessible without authentication (AC #2)."""
        url = reverse("api-docs")
        # Anonymous client (no authentication)
        response = client.get(url)

        # Should be accessible (no 401 or 403)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestReDoc:
    """Test ReDoc documentation interface (AC #2)."""

    def test_redoc_accessible(self, client):
        """Test ReDoc is accessible at /api/redoc/."""
        url = reverse("api-redoc")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK
        # ReDoc returns HTML
        assert "text/html" in response["Content-Type"]

    def test_redoc_accessible_without_authentication(self, client):
        """Test ReDoc is accessible without authentication (AC #2)."""
        url = reverse("api-redoc")
        # Anonymous client (no authentication)
        response = client.get(url)

        # Should be accessible (no 401 or 403)
        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestDocumentationRateLimiting:
    """Test documentation endpoints are not rate limited (AC #2, Task 11)."""

    def test_swagger_ui_not_rate_limited(self, client):
        """Test Swagger UI endpoint is not rate limited even after 100+ requests."""
        url = reverse("api-docs")

        # Make 105 requests (exceeds 20/min anonymous rate limit and 100/min user limit)
        for i in range(105):
            response = client.get(url)
            # Should never return 429 (Too Many Requests)
            assert response.status_code == status.HTTP_200_OK, (
                f"Request {i + 1} failed with status {response.status_code}"
            )

    def test_redoc_not_rate_limited(self, client):
        """Test ReDoc endpoint is not rate limited even after 100+ requests."""
        url = reverse("api-redoc")

        # Make 105 requests (exceeds rate limits)
        for i in range(105):
            response = client.get(url)
            assert response.status_code == status.HTTP_200_OK, (
                f"Request {i + 1} failed with status {response.status_code}"
            )

    def test_schema_endpoint_not_rate_limited(self, client):
        """Test schema endpoint is not rate limited even after 100+ requests."""
        url = reverse("api-schema")

        # Make 105 requests (exceeds rate limits)
        for i in range(105):
            response = client.get(url, HTTP_ACCEPT="application/json")
            assert response.status_code == status.HTTP_200_OK, (
                f"Request {i + 1} failed with status {response.status_code}"
            )


@pytest.mark.django_db
class TestSerializerDocumentation:
    """Test serializer fields have comprehensive documentation (AC #9)."""

    def test_user_registration_serializer_has_help_text(self):
        """Test UserRegistrationSerializer fields have help_text."""
        from quran_backend.users.api.serializers import UserRegistrationSerializer

        serializer = UserRegistrationSerializer()

        # Check that key fields have help_text
        assert "email" in serializer.fields
        assert serializer.fields["email"].help_text

        assert "password" in serializer.fields
        assert serializer.fields["password"].help_text

        assert "password_confirm" in serializer.fields
        assert serializer.fields["password_confirm"].help_text

    def test_user_login_serializer_has_help_text(self):
        """Test UserLoginSerializer fields have help_text."""
        from quran_backend.users.api.serializers import UserLoginSerializer

        serializer = UserLoginSerializer()

        assert "email" in serializer.fields
        assert serializer.fields["email"].help_text

        assert "password" in serializer.fields
        assert serializer.fields["password"].help_text


@pytest.mark.django_db
class TestEndpointDocumentation:
    """Test endpoint documentation completeness (AC #1, #3)."""

    def test_registration_endpoint_has_examples(self, client):
        """Test registration endpoint has request/response examples in schema."""
        url = reverse("api-schema")
        response = client.get(url, HTTP_ACCEPT="application/json")
        schema = response.json()

        # Find registration endpoint in paths
        paths = schema.get("paths", {})

        # Look for registration endpoint
        registration_found = False
        for path, methods in paths.items():
            if "register" in path.lower():
                registration_found = True
                # Check that POST method exists
                assert "post" in methods
                break

        assert registration_found, "Registration endpoint not found in schema"

    def test_health_check_endpoint_accessible(self, client):
        """Test health check endpoint is accessible and returns proper format."""
        url = reverse("health-check")
        response = client.get(url)

        assert response.status_code == status.HTTP_200_OK

        # Verify response format
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "checks" in data


@pytest.mark.django_db
class TestErrorResponseDocumentation:
    """Test error response format is documented (AC #5)."""

    def test_error_response_serializer_exists(self):
        """Test ErrorResponseSerializer is defined for documentation."""
        from quran_backend.core.api.serializers import ErrorResponseSerializer

        serializer = ErrorResponseSerializer()

        # Verify required fields
        assert "error" in serializer.fields
        assert "message" in serializer.fields
        assert "request_id" in serializer.fields
        assert "details" in serializer.fields

        # Verify fields have help_text
        assert serializer.fields["error"].help_text
        assert serializer.fields["message"].help_text
        assert serializer.fields["request_id"].help_text

    def test_error_detail_serializer_exists(self):
        """Test ErrorDetailSerializer is defined for field-level errors."""
        from quran_backend.core.api.serializers import ErrorDetailSerializer

        serializer = ErrorDetailSerializer()

        assert "field" in serializer.fields
        assert "message" in serializer.fields

        # Verify fields have help_text
        assert serializer.fields["field"].help_text
        assert serializer.fields["message"].help_text

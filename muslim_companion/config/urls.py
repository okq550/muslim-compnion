from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path
from django.views import defaults as default_views
# from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView
from drf_spectacular.views import SpectacularRedocView
from drf_spectacular.views import SpectacularSwaggerView
from rest_framework.authtoken.views import obtain_auth_token

from backend.core.views import health_check, project_metadata  # US-API-007/009
from backend.core.views.health import (  # US-API-009: Granular health check endpoints
    cache_health_check,
    database_health_check,
    disk_health_check,
    liveness_check,
    readiness_check,
)

urlpatterns = [
    # path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    # path(
    #     "about/",
    #     TemplateView.as_view(template_name="pages/about.html"),
    #     name="about",
    # ),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("backend.users.urls", namespace="users")),
    # path("accounts/", include("allauth.urls")),
    # Your stuff: custom urls includes go here
    # ...
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]

# API URLS
urlpatterns += [
    # Health check endpoint (US-API-007)
    path("api/v1/health/", health_check, name="health-check"),
    # Granular health check endpoints (US-API-009)
    path("health/check", liveness_check, name="health-liveness"),
    path("health/ready", readiness_check, name="health-readiness"),
    path("health/db", database_health_check, name="health-database"),
    path("health/cache", cache_health_check, name="health-cache"),
    path("health/disk", disk_health_check, name="health-disk"),
    # Project metadata endpoint (US-API-009)
    path("api/meta/", project_metadata, name="project-metadata"),
    # API base url
    path("api/", include("config.api_router")),
    # DRF auth token
    path("api/auth-token/", obtain_auth_token, name="obtain_auth_token"),
    # Quran app API urls
    path("api/v1/quran/", include("backend.quran.urls", namespace="quran")),
    # API Documentation (US-API-008)
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-docs",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="api-schema"),
        name="api-redoc",
    ),
]

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]

from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from quran_backend.analytics.api.views import AnalyticsConsentView
from quran_backend.analytics.api.views import DeleteMyAnalyticsDataView
from quran_backend.analytics.api.views import ErrorRatesView
from quran_backend.analytics.api.views import PopularFeaturesView
from quran_backend.analytics.api.views import PopularSurahsView
from quran_backend.legal.api.views import PrivacyPolicyView
from quran_backend.users.api.views import PasswordResetConfirmView
from quran_backend.users.api.views import PasswordResetRequestView
from quran_backend.users.api.views import ThrottledTokenRefreshView
from quran_backend.users.api.views import UserLoginView
from quran_backend.users.api.views import UserLogoutView
from quran_backend.users.api.views import UserProfileViewSet
from quran_backend.users.api.views import UserRegistrationView
from quran_backend.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)


app_name = "api"
urlpatterns = [
    *router.urls,
    # Authentication endpoints
    path("v1/auth/register/", UserRegistrationView.as_view(), name="auth-register"),
    path("v1/auth/login/", UserLoginView.as_view(), name="auth-login"),
    path("v1/auth/logout/", UserLogoutView.as_view(), name="auth-logout"),
    path(
        "v1/auth/token/refresh/",
        ThrottledTokenRefreshView.as_view(),
        name="auth-token-refresh",
    ),
    path(
        "v1/auth/password/reset/",
        PasswordResetRequestView.as_view(),
        name="auth-password-reset",
    ),
    path(
        "v1/auth/password/reset/confirm/",
        PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
    # User profile endpoints
    path(
        "v1/users/profile/",
        UserProfileViewSet.as_view({"get": "retrieve", "patch": "partial_update"}),
        name="user-profile",
    ),
    # Legal endpoints
    path(
        "v1/legal/privacy-policy/",
        PrivacyPolicyView.as_view(),
        name="privacy-policy",
    ),
    # Analytics endpoints
    path(
        "v1/analytics/consent/",
        AnalyticsConsentView.as_view(),
        name="analytics-consent",
    ),
    path(
        "v1/analytics/delete-my-data/",
        DeleteMyAnalyticsDataView.as_view(),
        name="analytics-delete-data",
    ),
    path(
        "v1/analytics/popular-features/",
        PopularFeaturesView.as_view(),
        name="analytics-popular-features",
    ),
    path(
        "v1/analytics/popular-surahs/",
        PopularSurahsView.as_view(),
        name="analytics-popular-surahs",
    ),
    path(
        "v1/analytics/error-rates/",
        ErrorRatesView.as_view(),
        name="analytics-error-rates",
    ),
]

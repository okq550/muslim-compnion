from django.conf import settings
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter
from rest_framework_simplejwt.views import TokenRefreshView

from quran_backend.users.api.views import PasswordResetConfirmView
from quran_backend.users.api.views import PasswordResetRequestView
from quran_backend.users.api.views import UserLoginView
from quran_backend.users.api.views import UserLogoutView
from quran_backend.users.api.views import UserRegistrationView
from quran_backend.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)


app_name = "api"
urlpatterns = router.urls + [
    # Authentication endpoints
    path("v1/auth/register/", UserRegistrationView.as_view(), name="auth-register"),
    path("v1/auth/login/", UserLoginView.as_view(), name="auth-login"),
    path("v1/auth/logout/", UserLogoutView.as_view(), name="auth-logout"),
    path(
        "v1/auth/token/refresh/", TokenRefreshView.as_view(), name="auth-token-refresh"
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
]

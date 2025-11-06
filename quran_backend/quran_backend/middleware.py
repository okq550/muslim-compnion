"""Custom middleware for the Quran Backend application."""

from django.utils import translation


class ForceArabicMiddleware:
    """Force Arabic language for all requests."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        translation.activate("ar")
        request.LANGUAGE_CODE = "ar"
        return self.get_response(request)

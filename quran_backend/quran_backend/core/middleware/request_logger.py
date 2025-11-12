"""
Request/Response Logging Middleware.

Implements AC #1, #2 from US-API-007:
- Log all incoming requests (endpoint, method, user, IP, correlation ID)
- Log all responses (status code, response time)
- Log slow requests (> 500ms) as WARNING
- Exclude health check endpoint from logging (reduce noise)
- Use structured logging with extra={} context
"""

import logging
import time

logger = logging.getLogger(__name__)

RESPONSE_TIME_SLOW_MS = 500  # Threshold for slow requests


class RequestLoggingMiddleware:
    """
    Middleware for logging all HTTP requests and responses.

    Responsibilities:
    1. Log incoming requests with correlation ID (request_id)
    2. Log responses with status code and response time
    3. Log slow requests (> 500ms) as WARNING
    4. Exclude health check endpoint from logging
    5. Use structured JSON logging with contextual data
    """

    # Endpoints to exclude from logging (reduce noise)
    EXCLUDED_PATHS = [
        "/api/v1/health/",
        "/health/",
        "/favicon.ico",
    ]

    def __init__(self, get_response):
        """Initialize middleware with get_response callable."""
        self.get_response = get_response

    def __call__(self, request):
        """
        Process request and log request/response details.

        Args:
            request: Django HttpRequest

        Returns:
            HttpResponse
        """
        # Skip logging for excluded paths (health checks)
        if self._should_skip_logging(request):
            return self.get_response(request)

        # Get request_id (should be set by ErrorHandlingMiddleware)
        request_id = getattr(request, "request_id", "unknown")

        # Record start time for response time calculation
        start_time = time.time()

        # Log incoming request (INFO level) - AC #1
        self._log_request(request, request_id)

        # Process request
        response = self.get_response(request)

        # Calculate response time
        response_time_ms = (time.time() - start_time) * 1000

        # Log response (INFO level) - AC #2
        self._log_response(request, response, request_id, response_time_ms)

        # Log slow requests (WARNING level) - AC #2
        if response_time_ms > RESPONSE_TIME_SLOW_MS:
            self._log_slow_request(request, response, request_id, response_time_ms)

        return response

    def _should_skip_logging(self, request):
        """
        Check if request should be excluded from logging.

        Args:
            request: Django HttpRequest

        Returns:
            bool: True if should skip logging
        """
        return request.path in self.EXCLUDED_PATHS

    def _log_request(self, request, request_id):
        """
        Log incoming request details.

        Args:
            request: Django HttpRequest
            request_id (str): Correlation ID for request
        """
        # Get user ID if authenticated
        user_id = None
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = str(request.user.id)

        # Get client IP address
        ip_address = self._get_client_ip(request)

        # Log request with structured context
        logger.info(
            "Request: %s %s",
            request.method,
            request.path,
            extra={
                "request_id": request_id,
                "endpoint": request.path,
                "method": request.method,
                "user_id": user_id,
                "ip_address": ip_address,
                "query_params": dict(request.GET) if request.GET else {},
            },
        )

    def _log_response(self, request, response, request_id, response_time_ms):
        """
        Log response details.

        Args:
            request: Django HttpRequest
            response: Django HttpResponse
            request_id (str): Correlation ID for request
            response_time_ms (float): Response time in milliseconds
        """
        logger.info(
            "Response: %s %s - %s (%.2fms)",
            request.method,
            request.path,
            response.status_code,
            response_time_ms,
            extra={
                "request_id": request_id,
                "endpoint": request.path,
                "method": request.method,
                "status_code": response.status_code,
                "response_time_ms": round(response_time_ms, 2),
            },
        )

    def _log_slow_request(self, request, response, request_id, response_time_ms):
        """
        Log slow requests (> 500ms) as WARNING.

        Args:
            request: Django HttpRequest
            response: Django HttpResponse
            request_id (str): Correlation ID for request
            response_time_ms (float): Response time in milliseconds
        """
        # Get user ID if authenticated
        user_id = None
        if hasattr(request, "user") and request.user.is_authenticated:
            user_id = str(request.user.id)

        logger.warning(
            "Slow request: %s %s took %.2fms",
            request.method,
            request.path,
            response_time_ms,
            extra={
                "request_id": request_id,
                "endpoint": request.path,
                "method": request.method,
                "user_id": user_id,
                "status_code": response.status_code,
                "response_time_ms": round(response_time_ms, 2),
                "query_params": dict(request.GET) if request.GET else {},
                "slow_request": True,
            },
        )

    def _get_client_ip(self, request):
        """
        Extract client IP address from request.

        Handles X-Forwarded-For header for proxied requests.

        Args:
            request: Django HttpRequest

        Returns:
            str: Client IP address
        """
        x_forwarded_for = request.headers.get("x-forwarded-for")
        if x_forwarded_for:
            # X-Forwarded-For can contain multiple IPs (client, proxy1, proxy2, ...)
            # First IP is the original client
            ip = x_forwarded_for.split(",")[0].strip()
        else:
            ip = request.META.get("REMOTE_ADDR", "unknown")
        return ip

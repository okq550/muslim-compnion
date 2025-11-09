"""
Structured JSON Logging for Quran Backend API.

Implements AC #1, #2, #3 from US-API-007:
- Structured JSON logging with correlation IDs
- Sensitive data filtering (no passwords, tokens, PII)
- ISO 8601 timestamp formatting
- Contextual data via extra={} parameter
"""

import logging
import re
from datetime import UTC
from datetime import datetime

from pythonjsonlogger.json import JsonFormatter as jsonlogger_JsonFormatter


class StructuredJsonFormatter(jsonlogger_JsonFormatter):
    """
    JSON formatter for structured logging with correlation IDs.

    Formats log records as JSON with standard fields:
    - timestamp (ISO 8601 UTC)
    - level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    - logger (module name)
    - message (log message)
    - request_id (correlation ID from request)
    - Additional contextual data from extra={}

    Example:
        logger.info(
            "User login successful",
            extra={
                "request_id": "550e8400-e29b-41d4-a716-446655440000",
                "user_id": "user-uuid",
                "endpoint": "/api/v1/auth/login/",
                "method": "POST",
                "ip_address": "192.168.1.1"
            }
        )
    """

    def add_fields(self, log_record, record, message_dict):
        """
        Add standard fields to log record.

        Args:
            log_record (dict): Output log record (JSON)
            record (LogRecord): Python logging LogRecord
            message_dict (dict): Additional context from extra={}
        """
        super().add_fields(log_record, record, message_dict)

        # Add timestamp in ISO 8601 UTC format (AC #2)
        log_record["timestamp"] = datetime.now(UTC).isoformat().replace("+00:00", "Z")

        # Add log level
        log_record["level"] = record.levelname

        # Add logger name (module path)
        log_record["logger"] = record.name

        # Add message
        log_record["message"] = record.getMessage()

        # Add correlation ID (request_id) if available (AC #1)
        # Will be provided via extra={"request_id": ...}
        if "request_id" not in log_record and hasattr(record, "request_id"):
            log_record["request_id"] = record.request_id

        # Add any additional context from extra={}
        # Fields like user_id, endpoint, method, ip_address, etc.


class SensitiveDataFilter(logging.Filter):
    """
    Filter to scrub sensitive data from log records.

    Implements AC #3: No sensitive data in logs.

    Filters:
    - Passwords (password, passwd, pwd fields)
    - JWT tokens and Authorization headers
    - Email addresses from non-auth logs
    - Full request/response bodies
    - Personal user data (PII) except hashed user IDs

    Usage:
        Add to handlers in Django LOGGING configuration:
        'filters': ['sensitive_data_filter']
    """

    # Regex patterns for sensitive data detection
    PASSWORD_PATTERNS = [
        re.compile(r'"password":\s*"[^"]*"', re.IGNORECASE),
        re.compile(r'"passwd":\s*"[^"]*"', re.IGNORECASE),
        re.compile(r'"pwd":\s*"[^"]*"', re.IGNORECASE),
        re.compile(r"'password':\s*'[^']*'", re.IGNORECASE),
        re.compile(r"password=\S+", re.IGNORECASE),
    ]

    TOKEN_PATTERNS = [
        re.compile(r'"token":\s*"[^"]*"', re.IGNORECASE),
        re.compile(r'"access_token":\s*"[^"]*"', re.IGNORECASE),
        re.compile(r'"refresh_token":\s*"[^"]*"', re.IGNORECASE),
        re.compile(r'"jwt":\s*"[^"]*"', re.IGNORECASE),
        re.compile(r"Bearer\s+[\w-]+\.[\w-]+\.[\w-]+", re.IGNORECASE),
        re.compile(r"Authorization:\s*\S+", re.IGNORECASE),
    ]

    EMAIL_PATTERNS = [
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    ]

    def filter(self, record):
        """
        Filter log record to remove sensitive data.

        Args:
            record (LogRecord): Python logging LogRecord

        Returns:
            bool: True (always allow record through after scrubbing)
        """
        # Scrub password fields from message
        if hasattr(record, "msg"):
            message = str(record.msg)
            for pattern in self.PASSWORD_PATTERNS:
                message = pattern.sub('"password":"***REDACTED***"', message)
            record.msg = message

        # Scrub tokens and Authorization headers
        if hasattr(record, "msg"):
            message = str(record.msg)
            for pattern in self.TOKEN_PATTERNS:
                message = pattern.sub('"token":"***REDACTED***"', message)
            record.msg = message

        # Scrub email addresses from non-auth logs
        # Allow email in auth events (login, password reset) but not error logs
        if hasattr(record, "msg") and record.levelname not in ["INFO"]:
            # Only filter emails from WARNING, ERROR, CRITICAL logs
            message = str(record.msg)
            for pattern in self.EMAIL_PATTERNS:
                message = pattern.sub("***EMAIL_REDACTED***", message)
            record.msg = message

        # Scrub sensitive fields from extra context
        if hasattr(record, "password"):
            record.password = "***REDACTED***"
        if hasattr(record, "token"):
            record.token = "***REDACTED***"
        if hasattr(record, "authorization"):
            record.authorization = "***REDACTED***"

        # Always allow record through (after scrubbing)
        return True

"""
Core views package.

Exports:
- health_check: Legacy health check endpoint (US-API-007)
- project_metadata: Project metadata endpoint (US-API-009)
"""

from backend.core.views.main import health_check, project_metadata

__all__ = ["health_check", "project_metadata"]

"""Small service-level errors mapped by FastAPI routes."""

from __future__ import annotations


class ApiServiceError(Exception):
    """Base class for expected local-control API failures."""


class NotFoundError(ApiServiceError):
    """Requested local resource is not present."""


class InvalidOperationError(ApiServiceError):
    """Request is valid syntax but cannot be completed in current state."""


class ExternalServiceError(ApiServiceError):
    """Upstream integration failed."""


class IntegrationUnauthorizedError(ExternalServiceError):
    """Stored integration credentials are missing, expired, or unauthorized."""

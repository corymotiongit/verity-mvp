"""
Verity - Custom Exceptions.

Centralized exception handling with standardized error responses.
"""

from typing import Any
from uuid import UUID


class VerityException(Exception):
    """Base exception for Verity application."""

    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
        request_id: UUID | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.request_id = request_id
        super().__init__(message)


class UnauthorizedException(VerityException):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Invalid or missing authentication token"):
        super().__init__(
            code="UNAUTHORIZED",
            message=message,
            status_code=401,
        )


class ForbiddenException(VerityException):
    """Raised when user lacks required permissions."""

    def __init__(self, message: str = "Insufficient permissions", required_role: str | None = None):
        details = {"required_role": required_role} if required_role else None
        super().__init__(
            code="FORBIDDEN",
            message=message,
            status_code=403,
            details=details,
        )


class NotFoundException(VerityException):
    """Raised when a resource is not found."""

    def __init__(self, resource_type: str, resource_id: str | UUID):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource_type} not found: {resource_id}",
            status_code=404,
            details={"resource_type": resource_type, "resource_id": str(resource_id)},
        )


class ConflictException(VerityException):
    """Raised when state transition is not allowed."""

    def __init__(self, message: str, current_state: str | None = None, target_state: str | None = None):
        details = {}
        if current_state:
            details["current_state"] = current_state
        if target_state:
            details["target_state"] = target_state
        super().__init__(
            code="CONFLICT",
            message=message,
            status_code=409,
            details=details if details else None,
        )


class ValidationException(VerityException):
    """Raised for validation errors."""

    def __init__(self, message: str, errors: list[dict[str, Any]] | None = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details={"errors": errors} if errors else None,
        )


class FeatureDisabledException(VerityException):
    """Raised when a feature flag is disabled."""

    def __init__(self, feature_name: str):
        super().__init__(
            code="FEATURE_DISABLED",
            message=f"Feature '{feature_name}' is currently disabled",
            status_code=503,
            details={"feature": feature_name},
        )


class ExternalServiceException(VerityException):
    """Raised when an external service fails."""

    def __init__(self, service_name: str, message: str):
        super().__init__(
            code="EXTERNAL_SERVICE_ERROR",
            message=f"{service_name} error: {message}",
            status_code=502,
            details={"service": service_name},
        )

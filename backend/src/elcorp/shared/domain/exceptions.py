"""
Domain exceptions - Used across all bounded contexts.
All business logic exceptions inherit from DomainException.
"""


class DomainException(Exception):
    """Base exception for all domain-level errors."""

    def __init__(self, message: str, code: str = "DOMAIN_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)

    def to_dict(self) -> dict:
        """Convert exception to API response format."""
        return {"error": self.code, "message": self.message}


class ValidationException(DomainException):
    """Raised when domain validation fails."""

    def __init__(self, message: str, field: str = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field

    def to_dict(self) -> dict:
        data = super().to_dict()
        if self.field:
            data["field"] = self.field
        return data


class NotFoundError(DomainException):
    """Raised when an aggregate or entity is not found."""

    def __init__(self, resource_type: str, identifier: str):
        message = f"{resource_type} with identifier '{identifier}' not found"
        super().__init__(message, "NOT_FOUND")
        self.resource_type = resource_type
        self.identifier = identifier


class UnauthorizedError(DomainException):
    """Raised when an operation is not authorized."""

    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, "UNAUTHORIZED")


class ConflictError(DomainException):
    """Raised when there is a conflict (duplicate, constraint violation, etc)."""

    def __init__(self, message: str, conflict_field: str = None):
        super().__init__(message, "CONFLICT")
        self.conflict_field = conflict_field

    def to_dict(self) -> dict:
        data = super().to_dict()
        if self.conflict_field:
            data["field"] = self.conflict_field
        return data


class InternalServerError(DomainException):
    """Raised for unexpected internal errors."""

    def __init__(self, message: str = "Internal server error"):
        super().__init__(message, "INTERNAL_ERROR")

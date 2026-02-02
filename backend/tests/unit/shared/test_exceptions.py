"""
Unit tests for shared domain exceptions.
"""

import pytest
from src.elcorp.shared.domain import (
    DomainException,
    ValidationException,
    NotFoundError,
    UnauthorizedError,
    ConflictError,
)


class TestDomainException:
    """Test domain exception base class."""

    def test_domain_exception_creation(self):
        """Test creating a domain exception."""
        exc = DomainException("Test error", "TEST_CODE")
        assert exc.message == "Test error"
        assert exc.code == "TEST_CODE"

    def test_domain_exception_to_dict(self):
        """Test converting exception to dict."""
        exc = DomainException("Test error", "TEST_CODE")
        result = exc.to_dict()
        assert result["error"] == "TEST_CODE"
        assert result["message"] == "Test error"


class TestValidationException:
    """Test validation exception."""

    def test_validation_exception_with_field(self):
        """Test validation exception with field info."""
        exc = ValidationException("Email is invalid", field="email")
        result = exc.to_dict()
        assert result["error"] == "VALIDATION_ERROR"
        assert result["field"] == "email"
        assert result["message"] == "Email is invalid"


class TestNotFoundError:
    """Test not found error."""

    def test_not_found_error_message(self):
        """Test not found error message format."""
        exc = NotFoundError("User", "123")
        assert "User" in exc.message
        assert "123" in exc.message
        assert exc.code == "NOT_FOUND"


class TestUnauthorizedError:
    """Test unauthorized error."""

    def test_unauthorized_error_default_message(self):
        """Test unauthorized error with default message."""
        exc = UnauthorizedError()
        assert exc.message == "Unauthorized"
        assert exc.code == "UNAUTHORIZED"


class TestConflictError:
    """Test conflict error."""

    def test_conflict_error_with_field(self):
        """Test conflict error with field info."""
        exc = ConflictError("Email already exists", conflict_field="email")
        result = exc.to_dict()
        assert result["error"] == "CONFLICT"
        assert result["field"] == "email"

"""
Unit tests for User aggregate.
"""

import pytest
from datetime import datetime, timezone
from src.elcorp.identity.domain import User, UserStatus
from src.elcorp.shared.domain import Email, PhoneNumber, ValidationException, UserPasswordChangedEvent


class TestUserAggregate:
    """Test User aggregate root."""

    @pytest.fixture
    def user(self):
        """Create a test user."""
        return User(
            id="user-123",
            username="john.doe",
            email=Email("john@example.com"),
            phone=PhoneNumber("+26461234567"),
        )

    def test_user_creation(self, user):
        """Test creating a user."""
        assert user.id == "user-123"
        assert user.username == "john.doe"
        assert user.status == UserStatus.ACTIVE

    def test_set_password_and_verify(self, user):
        """Test setting and verifying password."""
        user.set_password("SecureP@ss123")
        assert user.verify_password("SecureP@ss123")
        assert not user.verify_password("WrongPassword")

    def test_password_strength_validation(self, user):
        """Test that weak passwords are rejected."""
        with pytest.raises(ValidationException):
            user.set_password("weak")  # Too short

    def test_password_change_event(self, user):
        """Test that password change creates event."""
        user.set_password("SecureP@ss123")
        assert len(user.events) == 1
        assert user.events[0].__class__.__name__ == "UserPasswordChangedEvent"

    def test_enable_mfa(self, user):
        """Test enabling MFA."""
        user.enable_mfa("totp", secret="secret-code")
        assert user.mfa_enabled
        assert user.mfa_method == "totp"
        assert user.mfa_secret == "secret-code"

    def test_invalid_mfa_method(self, user):
        """Test that invalid MFA method raises exception."""
        with pytest.raises(ValidationException):
            user.enable_mfa("invalid_method")

    def test_disable_mfa(self, user):
        """Test disabling MFA."""
        user.enable_mfa("totp", secret="secret")
        user.disable_mfa()
        assert not user.mfa_enabled
        assert user.mfa_method is None

    def test_record_failed_login(self, user):
        """Test recording failed login attempts."""
        user.record_failed_login()
        assert user.failed_login_attempts == 1

    def test_account_locked_after_5_failures(self, user):
        """Test that account locks after 5 failed attempts."""
        for _ in range(5):
            user.record_failed_login()
        assert user.status == UserStatus.LOCKED
        assert len(user.events) > 0

    def test_record_successful_login(self, user):
        """Test recording successful login."""
        user.record_failed_login()
        user.record_failed_login()
        user.record_successful_login()
        assert user.failed_login_attempts == 0
        assert user.last_login_at is not None

    def test_unlock_account(self, user):
        """Test unlocking a locked account."""
        user.lock()
        assert user.status == UserStatus.LOCKED
        user.unlock()
        assert user.status == UserStatus.ACTIVE
        assert user.failed_login_attempts == 0

    def test_is_active(self, user):
        """Test is_active check."""
        assert user.is_active()
        user.lock()
        assert not user.is_active()

    def test_soft_delete(self, user):
        """Test soft deleting user."""
        user.soft_delete()
        assert user.status == UserStatus.DELETED
        assert user.deleted_at is not None

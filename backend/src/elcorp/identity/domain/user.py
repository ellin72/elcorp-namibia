"""
User aggregate root - Core domain model for user management.
Implements DDD aggregate pattern with invariants and business rules.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, List
from enum import Enum
import uuid

from ...shared.domain import (
    Email,
    PhoneNumber,
    WalletAddress,
    DomainException,
    ValidationException,
    UserRegisteredEvent,
    UserPasswordChangedEvent,
    UserMFAEnabledEvent,
    UserLockedEvent,
)
from ...shared.security import PasswordHasher


class UserStatus(Enum):
    """User account status."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    SUSPENDED = "suspended"
    DELETED = "deleted"


@dataclass
class User:
    """
    User aggregate root - Manages user identity and authentication.
    All changes go through this aggregate's methods.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    username: str = ""
    email: Email = None
    phone: PhoneNumber = None
    password_hash: str = ""
    role: str = "user"  # 'user', 'staff', 'admin'
    status: UserStatus = UserStatus.ACTIVE
    wallet_address: Optional[WalletAddress] = None
    mfa_enabled: bool = False
    mfa_method: Optional[str] = None  # 'totp', 'sms'
    mfa_secret: Optional[str] = None  # Encrypted TOTP secret
    failed_login_attempts: int = 0
    last_login_at: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    deleted_at: Optional[datetime] = None

    # Domain events (not persisted, used for event sourcing/notifications)
    events: List = field(default_factory=list)

    def set_password(self, password: str) -> None:
        """
        Set/change user password with validation and hashing.
        Invariant: Password must meet strength requirements.
        """
        PasswordHasher.validate_password_strength(password)
        self.password_hash = PasswordHasher.hash_password(password)
        self.password_changed_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

        # Emit event
        self.events.append(
            UserPasswordChangedEvent(
                user_id=self.id,
                changed_at=self.password_changed_at,
            )
        )

    def verify_password(self, password: str) -> bool:
        """
        Verify a password against the stored hash.
        """
        return PasswordHasher.verify_password(password, self.password_hash)

    def enable_mfa(self, method: str, secret: Optional[str] = None) -> None:
        """
        Enable multi-factor authentication.
        Invariant: Only 'totp' or 'sms' methods supported.
        """
        if method not in ("totp", "sms"):
            raise ValidationException(f"Unsupported MFA method: {method}", field="mfa_method")

        self.mfa_enabled = True
        self.mfa_method = method
        self.mfa_secret = secret
        self.updated_at = datetime.now(timezone.utc)

        self.events.append(
            UserMFAEnabledEvent(
                user_id=self.id,
                mfa_method=method,
            )
        )

    def disable_mfa(self) -> None:
        """Disable multi-factor authentication."""
        self.mfa_enabled = False
        self.mfa_method = None
        self.mfa_secret = None
        self.updated_at = datetime.now(timezone.utc)

    def record_failed_login(self) -> None:
        """
        Record a failed login attempt.
        Invariant: Lock account after 5 consecutive failed attempts.
        """
        self.failed_login_attempts += 1
        self.updated_at = datetime.now(timezone.utc)

        if self.failed_login_attempts >= 5:
            self.lock()

    def record_successful_login(self) -> None:
        """
        Record a successful login and reset failed attempts.
        """
        self.failed_login_attempts = 0
        self.last_login_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

    def lock(self) -> None:
        """
        Lock the user account (due to failed login attempts or admin action).
        """
        self.status = UserStatus.LOCKED
        self.updated_at = datetime.now(timezone.utc)

        self.events.append(
            UserLockedEvent(
                user_id=self.id,
                reason="Failed login attempts" if self.failed_login_attempts >= 5 else "Admin action",
            )
        )

    def unlock(self) -> None:
        """Unlock the user account and reset failed login attempts."""
        self.status = UserStatus.ACTIVE
        self.failed_login_attempts = 0
        self.updated_at = datetime.now(timezone.utc)

    def set_wallet_address(self, address: str, blockchain: str = "ethereum") -> None:
        """
        Set user's blockchain wallet address.
        Invariant: Valid address format for the blockchain.
        """
        self.wallet_address = WalletAddress(value=address, blockchain=blockchain)
        self.updated_at = datetime.now(timezone.utc)

    def is_active(self) -> bool:
        """Check if user account is active."""
        return self.status == UserStatus.ACTIVE

    def soft_delete(self) -> None:
        """Soft delete user (for GDPR compliance)."""
        self.status = UserStatus.DELETED
        self.deleted_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)

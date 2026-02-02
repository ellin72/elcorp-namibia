"""
Domain events - Used for event-driven architecture within and between bounded contexts.
Domain events are immutable records of something that happened.
"""

from abc import ABC
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict
from uuid import uuid4


@dataclass
class DomainEvent(ABC):
    """
    Base class for all domain events.
    Domain events are fact recordings of something that happened in the domain.
    """

    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_name: str = field(default="")
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: str = ""
    aggregate_type: str = ""

    def __post_init__(self):
        """Automatically set event_name from class name if not provided."""
        if not self.event_name:
            self.event_name = self.__class__.__name__

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "event_name": self.event_name,
            "occurred_at": self.occurred_at.isoformat(),
            "aggregate_id": self.aggregate_id,
            "aggregate_type": self.aggregate_type,
        }


# Identity Domain Events
@dataclass
class UserRegisteredEvent(DomainEvent):
    """Raised when a new user is registered."""

    user_id: str = ""
    username: str = ""
    email: str = ""
    phone: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "phone": self.phone,
        })
        return data


@dataclass
class UserPasswordChangedEvent(DomainEvent):
    """Raised when a user changes their password."""

    user_id: str = ""
    changed_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "user_id": self.user_id,
            "changed_at": self.changed_at.isoformat(),
        })
        return data


@dataclass
class UserMFAEnabledEvent(DomainEvent):
    """Raised when user enables multi-factor authentication."""

    user_id: str = ""
    mfa_method: str = ""  # 'totp', 'sms', etc.

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "user_id": self.user_id,
            "mfa_method": self.mfa_method,
        })
        return data


@dataclass
class UserLockedEvent(DomainEvent):
    """Raised when a user account is locked (e.g., too many failed login attempts)."""

    user_id: str = ""
    reason: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "user_id": self.user_id,
            "reason": self.reason,
        })
        return data


@dataclass
class DeviceTokenCreatedEvent(DomainEvent):
    """Raised when a new device token is created."""

    user_id: str = ""
    device_id: str = ""
    device_name: str = ""

    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data.update({
            "user_id": self.user_id,
            "device_id": self.device_id,
            "device_name": self.device_name,
        })
        return data

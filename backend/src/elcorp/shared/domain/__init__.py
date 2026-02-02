"""
Shared domain module - Contains exceptions, value objects, and domain events.
This is the shared kernel across all bounded contexts.
"""

from .exceptions import (
    DomainException,
    ValidationException,
    NotFoundError,
    UnauthorizedError,
    ConflictError,
    InternalServerError,
)
from .value_objects import (
    Email,
    PhoneNumber,
    WalletAddress,
    Money,
    UserId,
)
from .events import (
    DomainEvent,
    UserRegisteredEvent,
    PasswordChangedEvent,
    MFAEnabledEvent,
    UserLockedEvent,
    DeviceTokenCreatedEvent,
)

__all__ = [
    "DomainException",
    "ValidationException",
    "NotFoundError",
    "UnauthorizedError",
    "ConflictError",
    "InternalServerError",
    "Email",
    "PhoneNumber",
    "WalletAddress",
    "Money",
    "UserId",
    "DomainEvent",
    "UserRegisteredEvent",
    "PasswordChangedEvent",
    "MFAEnabledEvent",
    "UserLockedEvent",
    "DeviceTokenCreatedEvent",
]

"""
Commands - Represent user intentions to modify domain state.
Commands are immutable requests for action.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RegisterUserCommand:
    """Command to register a new user."""

    username: str
    email: str
    phone: str
    password: str


@dataclass(frozen=True)
class LoginUserCommand:
    """Command to authenticate a user."""

    username: str
    password: str
    device_id: str
    device_name: Optional[str] = None


@dataclass(frozen=True)
class UpdateUserProfileCommand:
    """Command to update user profile."""

    user_id: str
    phone: Optional[str] = None
    wallet_address: Optional[str] = None

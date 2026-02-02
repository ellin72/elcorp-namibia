"""
Data Transfer Objects (DTOs) for identity operations.
DTOs handle input validation using Pydantic.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime


class UserRegisterDTO(BaseModel):
    """DTO for user registration."""

    username: str = Field(..., min_length=3, max_length=32)
    email: EmailStr
    phone: str = Field(..., pattern=r"^(\+264|0)[0-9]{8}$")
    password: str = Field(..., min_length=8)
    password_confirm: str = Field(..., min_length=8)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v):
        """Validate username format."""
        import re
        if not re.match(r"^[a-zA-Z0-9._-]+$", v):
            raise ValueError("Username can only contain letters, numbers, dots, hyphens, and underscores")
        return v

    @field_validator("password_confirm")
    @classmethod
    def passwords_match(cls, v, info):
        """Ensure passwords match."""
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "john.doe",
                "email": "john@example.com",
                "phone": "+26461234567",
                "password": "SecureP@ss123",
                "password_confirm": "SecureP@ss123",
            }
        }
    }


class UserLoginDTO(BaseModel):
    """DTO for user login."""

    username: str = Field(...)
    password: str = Field(...)
    device_id: str = Field(..., description="Unique device identifier")
    device_name: Optional[str] = Field(None, description="Device name for display")

    model_config = {
        "json_schema_extra": {
            "example": {
                "username": "john.doe",
                "password": "SecureP@ss123",
                "device_id": "device-uuid-here",
                "device_name": "Chrome on Windows",
            }
        }
    }


class UserProfileDTO(BaseModel):
    """DTO for user profile response."""

    id: str
    username: str
    email: str
    phone: str
    role: str
    wallet_address: Optional[str] = None
    mfa_enabled: bool
    created_at: datetime
    last_login_at: Optional[datetime] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "user-uuid",
                "username": "john.doe",
                "email": "john@example.com",
                "phone": "+26461234567",
                "role": "user",
                "wallet_address": "0x1234567890abcdef",
                "mfa_enabled": False,
                "created_at": "2026-02-02T10:00:00Z",
                "last_login_at": "2026-02-02T15:30:00Z",
            }
        }
    }

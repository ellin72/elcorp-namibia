"""
SQLAlchemy persistence models for identity domain.
These are separate from domain models to avoid framework coupling.
"""

from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
import enum

Base = declarative_base()


class UserModelStatus(enum.Enum):
    """User status enumeration for database."""
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOCKED = "locked"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserModel(Base):
    """SQLAlchemy User model for persistence."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    username = Column(String(32), unique=True, nullable=False, index=True)
    email = Column(String(254), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False)
    status = Column(Enum(UserModelStatus), default=UserModelStatus.ACTIVE, nullable=False)
    wallet_address = Column(String(255), nullable=True, unique=True)
    wallet_blockchain = Column(String(20), nullable=True, default="ethereum")
    mfa_enabled = Column(Boolean, default=False)
    mfa_method = Column(String(20), nullable=True)
    mfa_secret = Column(String(255), nullable=True)  # Encrypted TOTP secret
    failed_login_attempts = Column(Integer, default=0)
    last_login_at = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)
    deleted_at = Column(DateTime, nullable=True)


class DeviceTokenModel(Base):
    """SQLAlchemy DeviceToken model for persistence."""
    __tablename__ = "device_tokens"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    device_id = Column(String(255), nullable=False)
    device_name = Column(String(255), nullable=True)
    refresh_token = Column(String(1000), nullable=False)
    token_jti = Column(String(36), nullable=True, index=True)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    revoked_at = Column(DateTime, nullable=True)

    __table_args__ = (
        # Unique constraint per user-device
        # In production, add: UniqueConstraint('user_id', 'device_id', name='uq_user_device'),
    )

"""
DeviceToken entity - Tracks devices and device-bound refresh tokens.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional
import uuid


@dataclass
class DeviceToken:
    """
    Device token entity - One refresh token per device.
    Enables per-device revocation and tracking.
    """

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    device_id: str = ""
    device_name: str = ""  # e.g., "Chrome on Windows", "Safari on iPhone"
    refresh_token: str = ""
    token_jti: str = ""  # JWT ID for token revocation tracking
    last_used_at: Optional[datetime] = None
    expires_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    revoked_at: Optional[datetime] = None

    def is_valid(self) -> bool:
        """Check if token is still valid (not expired, not revoked)."""
        now = datetime.now(timezone.utc)
        return self.revoked_at is None and self.expires_at > now

    def revoke(self) -> None:
        """Revoke this device token."""
        self.revoked_at = datetime.now(timezone.utc)

    def record_usage(self) -> None:
        """Record that this token was used."""
        self.last_used_at = datetime.now(timezone.utc)

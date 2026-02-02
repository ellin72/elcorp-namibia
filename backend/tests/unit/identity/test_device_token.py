"""
Unit tests for device token entity.
"""

import pytest
from datetime import datetime, timedelta, timezone
from src.elcorp.identity.domain import DeviceToken


class TestDeviceToken:
    """Test DeviceToken entity."""

    @pytest.fixture
    def device_token(self):
        """Create a test device token."""
        return DeviceToken(
            id="token-123",
            user_id="user-456",
            device_id="device-789",
            device_name="Chrome on Windows",
            refresh_token="refresh-token-value",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

    def test_device_token_creation(self, device_token):
        """Test creating a device token."""
        assert device_token.user_id == "user-456"
        assert device_token.device_id == "device-789"
        assert not device_token.revoked_at

    def test_token_is_valid(self, device_token):
        """Test checking if token is valid."""
        assert device_token.is_valid()

    def test_token_is_invalid_when_revoked(self, device_token):
        """Test that revoked tokens are invalid."""
        device_token.revoke()
        assert not device_token.is_valid()

    def test_token_is_invalid_when_expired(self):
        """Test that expired tokens are invalid."""
        token = DeviceToken(
            id="token-123",
            user_id="user-456",
            device_id="device-789",
            device_name="Device",
            refresh_token="value",
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert not token.is_valid()

    def test_record_usage(self, device_token):
        """Test recording token usage."""
        device_token.record_usage()
        assert device_token.last_used_at is not None

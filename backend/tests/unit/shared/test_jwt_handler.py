"""
Unit tests for JWT handler.
"""

import pytest
from datetime import datetime, timedelta, timezone
from src.elcorp.shared.security import JWTHandler
from src.elcorp.shared.domain import UnauthorizedError


class TestJWTHandler:
    """Test JWT token handling."""

    @pytest.fixture
    def jwt_handler(self, jwt_secret):
        """Create JWT handler for tests."""
        return JWTHandler(jwt_secret)

    def test_create_access_token(self, jwt_handler):
        """Test creating an access token."""
        token = jwt_handler.create_access_token(
            user_id="user-123",
            device_id="device-456",
        )
        assert isinstance(token, str)
        assert len(token) > 0

    def test_verify_valid_access_token(self, jwt_handler):
        """Test verifying a valid access token."""
        token = jwt_handler.create_access_token(
            user_id="user-123",
            device_id="device-456",
        )
        payload = jwt_handler.verify_token(token, token_type="access")
        assert payload.sub == "user-123"
        assert payload.device_id == "device-456"
        assert payload.token_type == "access"

    def test_expired_token_raises_error(self, jwt_handler):
        """Test that expired token raises error."""
        token = jwt_handler.create_access_token(
            user_id="user-123",
            device_id="device-456",
            expires_delta=timedelta(seconds=-1),  # Already expired
        )
        with pytest.raises(UnauthorizedError) as exc_info:
            jwt_handler.verify_token(token)
        assert "expired" in str(exc_info.value).lower()

    def test_invalid_token_raises_error(self, jwt_handler):
        """Test that invalid token raises error."""
        with pytest.raises(UnauthorizedError):
            jwt_handler.verify_token("invalid.token.here")

    def test_token_revocation(self, jwt_handler):
        """Test token revocation by JTI."""
        token = jwt_handler.create_access_token(
            user_id="user-123",
            device_id="device-456",
        )
        payload = jwt_handler.verify_token(token)

        # Revoke the token
        jwt_handler.revoke_token(payload.jti)

        # Trying to verify revoked token should fail
        with pytest.raises(UnauthorizedError) as exc_info:
            jwt_handler.verify_token(token)
        assert "revoked" in str(exc_info.value).lower()

    def test_refresh_token_generation(self, jwt_handler):
        """Test generating refresh token."""
        token = jwt_handler.create_refresh_token(
            user_id="user-123",
            device_id="device-456",
        )
        payload = jwt_handler.verify_token(token, token_type="refresh")
        assert payload.token_type == "refresh"

    def test_refresh_access_token(self, jwt_handler):
        """Test using refresh token to get new access token."""
        refresh_token = jwt_handler.create_refresh_token(
            user_id="user-123",
            device_id="device-456",
        )
        new_access_token = jwt_handler.refresh_access_token(refresh_token)
        payload = jwt_handler.verify_token(new_access_token, token_type="access")
        assert payload.sub == "user-123"
        assert payload.device_id == "device-456"

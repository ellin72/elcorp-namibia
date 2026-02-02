"""
JWT token handling - Hardened JWT implementation with device binding and revocation.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict
import jwt
import uuid
from ..domain.exceptions import UnauthorizedError


@dataclass
class TokenPayload:
    """JWT token payload structure."""

    sub: str  # Subject (user ID)
    jti: str  # JWT ID (unique token ID for revocation)
    device_id: str  # Device identifier
    iat: datetime  # Issued at
    exp: datetime  # Expiration
    token_type: str = "access"  # 'access' or 'refresh'
    scope: str = "read write"  # Space-separated permissions


class JWTHandler:
    """
    Hardened JWT token handler with device binding and revocation.
    """

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire_minutes = 15
        self.refresh_token_expire_days = 7
        self.revoked_tokens: set = set()  # In production, use Redis

    def create_access_token(
        self, user_id: str, device_id: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a hardened access token with device binding.
        """
        if expires_delta is None:
            expires_delta = timedelta(minutes=self.access_token_expire_minutes)

        now = datetime.now(timezone.utc)
        expire = now + expires_delta

        payload = {
            "sub": user_id,
            "jti": str(uuid.uuid4()),  # Unique token ID for revocation
            "device_id": device_id,  # Bind token to device
            "iat": now,
            "exp": expire,
            "token_type": "access",
            "scope": "read write",
        }

        encoded = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return encoded

    def create_refresh_token(
        self, user_id: str, device_id: str, expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a refresh token with device binding.
        Refresh tokens have longer expiration than access tokens.
        """
        if expires_delta is None:
            expires_delta = timedelta(days=self.refresh_token_expire_days)

        now = datetime.now(timezone.utc)
        expire = now + expires_delta

        payload = {
            "sub": user_id,
            "jti": str(uuid.uuid4()),  # Unique token ID for revocation
            "device_id": device_id,  # Bind token to device
            "iat": now,
            "exp": expire,
            "token_type": "refresh",
            "scope": "refresh",
        }

        encoded = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        return encoded

    def verify_token(self, token: str, token_type: str = "access") -> TokenPayload:
        """
        Verify JWT token and return payload.
        Checks signature, expiration, and revocation status.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])

            # Check token type
            if payload.get("token_type") != token_type:
                raise UnauthorizedError(f"Invalid token type. Expected {token_type}")

            # Check revocation status
            if payload.get("jti") in self.revoked_tokens:
                raise UnauthorizedError("Token has been revoked")

            return TokenPayload(
                sub=payload["sub"],
                jti=payload["jti"],
                device_id=payload["device_id"],
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                token_type=payload.get("token_type", "access"),
                scope=payload.get("scope", "read write"),
            )

        except jwt.ExpiredSignatureError:
            raise UnauthorizedError("Token has expired")
        except jwt.InvalidTokenError as e:
            raise UnauthorizedError(f"Invalid token: {str(e)}")

    def revoke_token(self, jti: str) -> None:
        """
        Revoke a token by JTI (JWT ID).
        In production, store in Redis with TTL equal to token expiration.
        """
        self.revoked_tokens.add(jti)

    def refresh_access_token(self, refresh_token: str) -> str:
        """
        Use a refresh token to get a new access token.
        Validates that the refresh token is valid and not expired.
        """
        payload = self.verify_token(refresh_token, token_type="refresh")

        # Create new access token with same device binding
        return self.create_access_token(
            user_id=payload.sub,
            device_id=payload.device_id,
        )

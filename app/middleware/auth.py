"""JWT authentication middleware."""

from __future__ import annotations

import functools
from datetime import datetime, timedelta, timezone

import jwt
from flask import current_app, g, request

from app.utils.errors import UnauthorizedError


def create_access_token(user_id: str, roles: list[str]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "roles": roles,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(seconds=current_app.config["JWT_ACCESS_TOKEN_EXPIRES"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def create_refresh_token(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": now,
        "exp": now + timedelta(seconds=current_app.config["JWT_REFRESH_TOKEN_EXPIRES"]),
    }
    return jwt.encode(payload, current_app.config["JWT_SECRET_KEY"], algorithm="HS256")


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, current_app.config["JWT_SECRET_KEY"], algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise UnauthorizedError("Token has expired")
    except jwt.InvalidTokenError:
        raise UnauthorizedError("Invalid token")


def _get_bearer_token() -> str:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise UnauthorizedError("Missing or malformed Authorization header")
    return header[7:]


def jwt_required(fn):
    """Decorator that verifies an access JWT and sets g.current_user_id / g.current_roles."""

    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        token = _get_bearer_token()
        payload = decode_token(token)
        if payload.get("type") != "access":
            raise UnauthorizedError("Invalid token type")
        g.current_user_id = payload["sub"]
        g.current_roles = payload.get("roles", [])
        return fn(*args, **kwargs)

    return wrapper

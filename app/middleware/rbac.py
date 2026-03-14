"""Role-based access control decorator."""

from __future__ import annotations

import functools

from flask import g
from app.utils.errors import ForbiddenError


def roles_required(*allowed_roles: str):
    """Decorator — must be applied *after* @jwt_required so g.current_roles is set."""

    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            user_roles = set(getattr(g, "current_roles", []))
            if not user_roles.intersection(allowed_roles):
                raise ForbiddenError("Insufficient permissions")
            return fn(*args, **kwargs)

        return wrapper

    return decorator

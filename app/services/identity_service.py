"""Identity service — signup, profile management, user lookup."""

from __future__ import annotations

import structlog

from app.extensions import db
from app.models.user import User, Role
from app.services.audit_service import log_event
from app.utils.errors import ConflictError, NotFoundError

logger = structlog.get_logger()


def signup(*, email: str, password: str, first_name: str, last_name: str, phone: str = "") -> User:
    """Register a new user and assign the default 'user' role."""
    if User.query.filter_by(email=email).first():
        raise ConflictError("A user with this email already exists")

    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        phone=phone,
    )
    user.set_password(password)

    # assign default role
    role = Role.query.filter_by(name="user").first()
    if role:
        user.roles.append(role)

    db.session.add(user)
    db.session.commit()

    log_event("user.signup", user_id=user.id, entity_type="user", entity_id=user.id)
    logger.info("user.signup", user_id=user.id, email=email)
    return user


def get_user(user_id: str) -> User:
    user = db.session.get(User, user_id)
    if not user:
        raise NotFoundError("User not found")
    return user


def update_profile(user_id: str, data: dict) -> User:
    user = get_user(user_id)
    allowed = {"first_name", "last_name", "phone", "date_of_birth", "national_id", "address"}
    for key in allowed:
        if key in data:
            setattr(user, key, data[key])
    db.session.commit()

    log_event(
        "user.profile_updated",
        user_id=user_id,
        entity_type="user",
        entity_id=user_id,
        detail={"fields": [k for k in data if k in allowed]},
    )
    return user


def list_users(*, page: int = 1, per_page: int = 20):
    return User.query.order_by(User.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


def authenticate(email: str, password: str) -> User:
    user = User.query.filter_by(email=email).first()
    if not user or not user.check_password(password):
        log_event("auth.failed_login", detail={"email": email})
        raise NotFoundError("Invalid email or password")
    if not user.is_active:
        raise NotFoundError("Account is deactivated")
    log_event("auth.login", user_id=user.id, entity_type="user", entity_id=user.id)
    return user


def seed_roles() -> None:
    """Create default roles if they don't exist."""
    for name, desc in [
        ("admin", "System administrator"),
        ("staff", "Staff / reviewer"),
        ("user", "Regular user"),
    ]:
        if not Role.query.filter_by(name=name).first():
            db.session.add(Role(name=name, description=desc))
    db.session.commit()

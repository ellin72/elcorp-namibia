"""Permission model and role-permission mapping."""

from __future__ import annotations

from app.extensions import db

role_permissions = db.Table(
    "role_permissions",
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
    db.Column("permission_id", db.Integer, db.ForeignKey("permissions.id"), primary_key=True),
)


class Permission(db.Model):
    __tablename__ = "permissions"

    id: int = db.Column(db.Integer, primary_key=True)
    codename: str = db.Column(db.String(100), unique=True, nullable=False)
    description: str = db.Column(db.String(255), default="")

    roles = db.relationship("Role", secondary=role_permissions, backref="permissions", lazy="joined")

    def __repr__(self) -> str:
        return f"<Permission {self.codename}>"


# ---- Default permissions to seed ----

DEFAULT_PERMISSIONS = [
    ("users.read", "View user profiles"),
    ("users.write", "Edit user profiles"),
    ("users.admin", "Manage user accounts"),
    ("kyc.upload", "Upload KYC documents"),
    ("kyc.review", "Review KYC submissions"),
    ("payments.create", "Create payments"),
    ("payments.read", "View payments"),
    ("payments.process", "Process payments"),
    ("merchants.read", "View merchants"),
    ("merchants.write", "Manage merchants"),
    ("webhooks.manage", "Manage webhook subscriptions"),
    ("audit.read", "View audit logs"),
    ("admin.stats", "View system statistics"),
]

ROLE_DEFAULTS: dict[str, list[str]] = {
    "user": [
        "users.read", "users.write", "kyc.upload",
        "payments.create", "payments.read",
    ],
    "staff": [
        "users.read", "users.write", "kyc.upload", "kyc.review",
        "payments.create", "payments.read", "payments.process",
        "merchants.read", "audit.read",
    ],
    "admin": [p[0] for p in DEFAULT_PERMISSIONS],  # all permissions
}

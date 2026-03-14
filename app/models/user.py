"""User and Role models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import bcrypt
from sqlalchemy import Index

from app.extensions import db


class Role(db.Model):
    __tablename__ = "roles"

    id: int = db.Column(db.Integer, primary_key=True)
    name: str = db.Column(db.String(50), unique=True, nullable=False)
    description: str = db.Column(db.String(255), default="")

    def __repr__(self) -> str:
        return f"<Role {self.name}>"


# association table
user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.String(36), db.ForeignKey("users.id"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("roles.id"), primary_key=True),
)


class User(db.Model):
    __tablename__ = "users"
    __table_args__ = (
        Index("ix_users_email", "email", unique=True),
    )

    id: str = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email: str = db.Column(db.String(255), unique=True, nullable=False)
    password_hash: str = db.Column(db.String(255), nullable=False)
    first_name: str = db.Column(db.String(100), nullable=False)
    last_name: str = db.Column(db.String(100), nullable=False)
    phone: str = db.Column(db.String(30), default="")
    date_of_birth: datetime | None = db.Column(db.Date, nullable=True)
    national_id: str = db.Column(db.String(100), default="")
    address: str = db.Column(db.Text, default="")

    is_active: bool = db.Column(db.Boolean, default=True)
    is_verified: bool = db.Column(db.Boolean, default=False)
    verification_status: str = db.Column(
        db.String(20), default="pending"
    )  # pending | under_review | verified | rejected

    created_at: datetime = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # relationships
    roles = db.relationship("Role", secondary=user_roles, backref="users", lazy="joined")
    kyc_documents = db.relationship("KYCDocument", backref="user", lazy="dynamic")
    payments = db.relationship("Payment", backref="payer", lazy="dynamic", foreign_keys="Payment.user_id")

    # ---- password helpers ----

    def set_password(self, plaintext: str) -> None:
        self.password_hash = bcrypt.hashpw(
            plaintext.encode(), bcrypt.gensalt()
        ).decode()

    def check_password(self, plaintext: str) -> bool:
        return bcrypt.checkpw(plaintext.encode(), self.password_hash.encode())

    # ---- role helpers ----

    def has_role(self, role_name: str) -> bool:
        return any(r.name == role_name for r in self.roles)

    def to_dict(self, include_sensitive: bool = False) -> dict:
        data = {
            "id": self.id,
            "email": self.email,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "phone": self.phone,
            "is_active": self.is_active,
            "is_verified": self.is_verified,
            "verification_status": self.verification_status,
            "roles": [r.name for r in self.roles],
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_sensitive:
            data.update(
                {
                    "date_of_birth": str(self.date_of_birth) if self.date_of_birth else None,
                    "national_id": self.national_id,
                    "address": self.address,
                }
            )
        return data

    def __repr__(self) -> str:
        return f"<User {self.email}>"

"""Merchant model for payment onboarding."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.extensions import db


class Merchant(db.Model):
    __tablename__ = "merchants"

    id: str = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: str = db.Column(db.String(200), nullable=False)
    business_type: str = db.Column(db.String(100), default="")  # clinic | fintech | retail
    registration_number: str = db.Column(db.String(100), default="")
    contact_email: str = db.Column(db.String(255), nullable=False)
    contact_phone: str = db.Column(db.String(30), default="")
    address: str = db.Column(db.Text, default="")

    api_key: str = db.Column(db.String(255), unique=True, nullable=False)
    webhook_url: str = db.Column(db.String(500), default="")
    is_active: bool = db.Column(db.Boolean, default=True)
    sandbox_mode: bool = db.Column(db.Boolean, default=True)

    # settlement info
    settlement_bank: str = db.Column(db.String(100), default="")
    settlement_account: str = db.Column(db.String(100), default="")  # stored encrypted
    settlement_frequency: str = db.Column(db.String(20), default="daily")  # daily | weekly | monthly

    onboarded_by: str | None = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    status: str = db.Column(
        db.String(20), default="pending"
    )  # pending | active | suspended | deactivated

    created_at: datetime = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: datetime = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    payments = db.relationship("Payment", backref="merchant", lazy="dynamic")

    def to_dict(self, include_keys: bool = False) -> dict:
        data = {
            "id": self.id,
            "name": self.name,
            "business_type": self.business_type,
            "registration_number": self.registration_number,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "is_active": self.is_active,
            "sandbox_mode": self.sandbox_mode,
            "status": self.status,
            "settlement_frequency": self.settlement_frequency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_keys:
            data["api_key"] = self.api_key
        return data

    def __repr__(self) -> str:
        return f"<Merchant {self.name} status={self.status}>"

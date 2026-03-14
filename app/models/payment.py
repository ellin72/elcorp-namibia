"""Payment and PaymentToken models."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.extensions import db


class PaymentToken(db.Model):
    """Tokenised payment instrument (card, bank account)."""

    __tablename__ = "payment_tokens"

    id: str = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: str = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    token: str = db.Column(db.String(255), unique=True, nullable=False)
    instrument_type: str = db.Column(db.String(30), nullable=False)  # card | bank_account
    last_four: str = db.Column(db.String(4), default="")
    is_active: bool = db.Column(db.Boolean, default=True)
    created_at: datetime = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    payments = db.relationship("Payment", backref="payment_token_rel", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "token": self.token,
            "instrument_type": self.instrument_type,
            "last_four": self.last_four,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Payment(db.Model):
    """A single payment transaction."""

    __tablename__ = "payments"

    id: str = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: str = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)
    merchant_id: str = db.Column(db.String(36), db.ForeignKey("merchants.id"), nullable=False, index=True)
    payment_token_id: str | None = db.Column(db.String(36), db.ForeignKey("payment_tokens.id"), nullable=True)

    amount: int = db.Column(db.BigInteger, nullable=False)  # amount in smallest currency unit (cents)
    currency: str = db.Column(db.String(3), nullable=False, default="NAD")
    description: str = db.Column(db.String(500), default="")
    reference: str = db.Column(db.String(100), unique=True, nullable=False)

    status: str = db.Column(
        db.String(20), default="pending"
    )  # pending | processing | completed | failed | refunded
    gateway_ref: str = db.Column(db.String(255), default="")
    failure_reason: str = db.Column(db.Text, default="")

    created_at: datetime = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = db.Column(db.DateTime, nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "merchant_id": self.merchant_id,
            "payment_token_id": self.payment_token_id,
            "amount": self.amount,
            "currency": self.currency,
            "description": self.description,
            "reference": self.reference,
            "status": self.status,
            "gateway_ref": self.gateway_ref,
            "failure_reason": self.failure_reason,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

    def __repr__(self) -> str:
        return f"<Payment {self.reference} {self.status} {self.amount}{self.currency}>"

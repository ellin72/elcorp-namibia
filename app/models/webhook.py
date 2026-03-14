"""Webhook models — subscriptions and delivery log."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.extensions import db


class WebhookSubscription(db.Model):
    """A merchant's webhook subscription for event notifications."""

    __tablename__ = "webhook_subscriptions"

    id: str = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    merchant_id: str = db.Column(db.String(36), db.ForeignKey("merchants.id"), nullable=False, index=True)
    url: str = db.Column(db.String(500), nullable=False)
    secret: str = db.Column(db.String(255), nullable=False)  # HMAC signing secret
    events: str = db.Column(db.Text, default="*")  # comma-separated event names or *
    is_active: bool = db.Column(db.Boolean, default=True)
    created_at: datetime = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    deliveries = db.relationship("WebhookDelivery", backref="subscription", lazy="dynamic")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "merchant_id": self.merchant_id,
            "url": self.url,
            "events": self.events,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class WebhookDelivery(db.Model):
    """Record of each webhook delivery attempt."""

    __tablename__ = "webhook_deliveries"

    id: str = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    subscription_id: str = db.Column(
        db.String(36), db.ForeignKey("webhook_subscriptions.id"), nullable=False, index=True
    )
    event: str = db.Column(db.String(100), nullable=False)
    payload: str = db.Column(db.Text, nullable=False)  # JSON
    response_status: int = db.Column(db.Integer, nullable=True)
    response_body: str = db.Column(db.Text, default="")
    success: bool = db.Column(db.Boolean, default=False)
    attempts: int = db.Column(db.Integer, default=1)
    created_at: datetime = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "subscription_id": self.subscription_id,
            "event": self.event,
            "response_status": self.response_status,
            "success": self.success,
            "attempts": self.attempts,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

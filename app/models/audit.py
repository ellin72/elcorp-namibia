"""Audit log model — immutable event store for compliance."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.extensions import db


class AuditLog(db.Model):
    __tablename__ = "audit_logs"
    __table_args__ = (
        db.Index("ix_audit_user", "user_id"),
        db.Index("ix_audit_entity", "entity_type", "entity_id"),
        db.Index("ix_audit_created", "created_at"),
    )

    id: str = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: str | None = db.Column(db.String(36), nullable=True)  # who performed the action
    action: str = db.Column(db.String(100), nullable=False)           # e.g. "user.signup", "kyc.approved"
    entity_type: str = db.Column(db.String(50), default="")           # e.g. "user", "payment", "kyc"
    entity_id: str = db.Column(db.String(36), default="")
    detail: str = db.Column(db.Text, default="")                      # JSON-serialised extra data
    ip_address: str = db.Column(db.String(45), default="")
    user_agent: str = db.Column(db.String(500), default="")
    created_at: datetime = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "detail": self.detail,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} user={self.user_id}>"

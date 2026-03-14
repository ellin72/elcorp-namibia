"""KYC document model."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.extensions import db


class KYCDocument(db.Model):
    __tablename__ = "kyc_documents"

    id: str = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: str = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False, index=True)

    document_type: str = db.Column(
        db.String(50), nullable=False
    )  # national_id | passport | drivers_license | proof_of_address
    file_path: str = db.Column(db.String(500), nullable=False)
    file_hash: str = db.Column(db.String(128), default="")
    original_filename: str = db.Column(db.String(255), default="")
    mime_type: str = db.Column(db.String(100), default="")

    status: str = db.Column(
        db.String(20), default="pending"
    )  # pending | approved | rejected
    rejection_reason: str = db.Column(db.Text, default="")
    reviewed_by: str | None = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=True)
    reviewed_at: datetime | None = db.Column(db.DateTime, nullable=True)

    created_at: datetime = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )
    updated_at: datetime = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    reviewer = db.relationship("User", foreign_keys=[reviewed_by], backref="reviewed_documents")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "document_type": self.document_type,
            "original_filename": self.original_filename,
            "mime_type": self.mime_type,
            "status": self.status,
            "rejection_reason": self.rejection_reason,
            "reviewed_by": self.reviewed_by,
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def __repr__(self) -> str:
        return f"<KYCDocument {self.id} type={self.document_type} status={self.status}>"

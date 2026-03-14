"""Revoked token model for refresh-token rotation."""

from __future__ import annotations

from datetime import datetime, timezone

from app.extensions import db


class RevokedToken(db.Model):
    """Stores JTIs of consumed or revoked refresh tokens."""

    __tablename__ = "revoked_tokens"

    jti: str = db.Column(db.String(36), primary_key=True)
    revoked_at: datetime = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc)
    )

    @classmethod
    def is_revoked(cls, jti: str) -> bool:
        return db.session.get(cls, jti) is not None

    @classmethod
    def revoke(cls, jti: str) -> None:
        if not cls.is_revoked(jti):
            db.session.add(cls(jti=jti))
            db.session.commit()

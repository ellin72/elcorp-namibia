"""Audit logging service — writes immutable event records."""

from __future__ import annotations

import json
from flask import request as flask_request

from app.extensions import db
from app.models.audit import AuditLog


def log_event(
    action: str,
    *,
    user_id: str | None = None,
    entity_type: str = "",
    entity_id: str = "",
    detail: dict | str = "",
) -> AuditLog:
    """Persist an audit event."""
    if isinstance(detail, dict):
        detail = json.dumps(detail)

    ip = ""
    ua = ""
    try:
        ip = flask_request.remote_addr or ""
        ua = flask_request.headers.get("User-Agent", "")[:500]
    except RuntimeError:
        pass  # outside request context

    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        detail=detail,
        ip_address=ip,
        user_agent=ua,
    )
    db.session.add(entry)
    db.session.commit()
    return entry


def get_logs(
    *,
    user_id: str | None = None,
    action: str | None = None,
    entity_type: str | None = None,
    page: int = 1,
    per_page: int = 50,
):
    """Retrieve paginated audit logs with optional filters."""
    query = AuditLog.query.order_by(AuditLog.created_at.desc())
    if user_id:
        query = query.filter_by(user_id=user_id)
    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))
    if entity_type:
        query = query.filter_by(entity_type=entity_type)
    return query.paginate(page=page, per_page=per_page, error_out=False)

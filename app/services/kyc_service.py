"""KYC document service — upload, review, verification workflow."""

from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone

import structlog
from flask import current_app
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models.kyc import KYCDocument
from app.models.user import User
from app.services.audit_service import log_event
from app.utils.errors import NotFoundError, ValidationError

logger = structlog.get_logger()


def _allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]


def upload_document(
    user_id: str,
    document_type: str,
    file: FileStorage,
) -> KYCDocument:
    """Save an uploaded KYC document for a user."""
    from app.utils.validators import VALID_DOC_TYPES

    if document_type not in VALID_DOC_TYPES:
        raise ValidationError(f"document_type must be one of {VALID_DOC_TYPES}")

    if not file or not file.filename:
        raise ValidationError("No file provided")

    if not _allowed_file(file.filename):
        raise ValidationError("File type not allowed")

    original = secure_filename(file.filename)
    ext = original.rsplit(".", 1)[1].lower()
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    user_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], user_id)
    os.makedirs(user_dir, exist_ok=True)
    dest = os.path.join(user_dir, stored_name)

    file_bytes = file.read()
    file_hash = hashlib.sha256(file_bytes).hexdigest()

    with open(dest, "wb") as f:
        f.write(file_bytes)

    doc = KYCDocument(
        user_id=user_id,
        document_type=document_type,
        file_path=dest,
        file_hash=file_hash,
        original_filename=original,
        mime_type=file.content_type or "",
    )
    db.session.add(doc)
    db.session.commit()

    log_event(
        "kyc.uploaded",
        user_id=user_id,
        entity_type="kyc",
        entity_id=doc.id,
        detail={"document_type": document_type},
    )
    logger.info("kyc.uploaded", user_id=user_id, doc_id=doc.id)
    return doc


def review_document(
    doc_id: str,
    reviewer_id: str,
    decision: str,
    rejection_reason: str = "",
) -> KYCDocument:
    """Approve or reject a KYC document."""
    if decision not in ("approved", "rejected"):
        raise ValidationError("decision must be 'approved' or 'rejected'")

    doc = db.session.get(KYCDocument, doc_id)
    if not doc:
        raise NotFoundError("KYC document not found")

    doc.status = decision
    doc.reviewed_by = reviewer_id
    doc.reviewed_at = datetime.now(timezone.utc)
    if decision == "rejected":
        doc.rejection_reason = rejection_reason

    # Update user verification status when all required docs are approved
    _update_user_verification(doc.user_id)

    db.session.commit()

    log_event(
        f"kyc.{decision}",
        user_id=reviewer_id,
        entity_type="kyc",
        entity_id=doc.id,
        detail={"decision": decision, "reason": rejection_reason},
    )
    return doc


def _update_user_verification(user_id: str) -> None:
    """Set user verified if they have at least one approved national_id or passport."""
    approved = KYCDocument.query.filter_by(
        user_id=user_id, status="approved"
    ).filter(
        KYCDocument.document_type.in_(["national_id", "passport"])
    ).first()

    user = db.session.get(User, user_id)
    if user and approved:
        user.is_verified = True
        user.verification_status = "verified"
    elif user:
        user.verification_status = "under_review"


def get_documents(user_id: str) -> list[KYCDocument]:
    return KYCDocument.query.filter_by(user_id=user_id).order_by(KYCDocument.created_at.desc()).all()


def get_pending_documents(page: int = 1, per_page: int = 20):
    return KYCDocument.query.filter_by(status="pending").order_by(
        KYCDocument.created_at.asc()
    ).paginate(page=page, per_page=per_page, error_out=False)

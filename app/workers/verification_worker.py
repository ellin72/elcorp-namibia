"""KYC verification background worker."""

from __future__ import annotations

import structlog

from app.celery_app import celery_app
from app.extensions import db
from app.models.kyc import KYCDocument
from app.models.user import User
from app.services.audit_service import log_event

logger = structlog.get_logger()


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60, queue="verification")
def run_verification(self, doc_id: str) -> dict:
    """Run automated verification checks on a KYC document.

    In the MVP this performs basic sanity checks. Production would call
    an external identity-verification provider.
    """
    doc = db.session.get(KYCDocument, doc_id)
    if not doc:
        logger.warning("verification.doc_not_found", doc_id=doc_id)
        return {"status": "skipped", "reason": "document not found"}

    # ---- Basic automated checks ----
    checks_passed = True
    reasons: list[str] = []

    if not doc.file_hash:
        checks_passed = False
        reasons.append("file hash missing")

    if doc.mime_type and doc.mime_type not in (
        "image/png", "image/jpeg", "application/pdf",
    ):
        checks_passed = False
        reasons.append(f"unsupported mime type: {doc.mime_type}")

    if checks_passed:
        doc.status = "approved"
        _update_user_verification(doc.user_id)
        log_event(
            "kyc.auto_approved",
            entity_type="kyc",
            entity_id=doc.id,
            detail={"auto": True},
        )
    else:
        doc.status = "pending"  # stays pending for manual review
        log_event(
            "kyc.auto_check_flagged",
            entity_type="kyc",
            entity_id=doc.id,
            detail={"reasons": reasons},
        )

    db.session.commit()
    logger.info("verification.completed", doc_id=doc_id, passed=checks_passed)
    return {"doc_id": doc_id, "passed": checks_passed, "reasons": reasons}


@celery_app.task(queue="verification")
def check_pending_verifications() -> int:
    """Periodic task — attempt auto-verification on pending documents."""
    pending = KYCDocument.query.filter_by(status="pending").limit(100).all()
    count = 0
    for doc in pending:
        run_verification.delay(doc.id)
        count += 1
    logger.info("verification.batch_queued", count=count)
    return count


def _update_user_verification(user_id: str) -> None:
    approved = KYCDocument.query.filter_by(
        user_id=user_id, status="approved"
    ).filter(
        KYCDocument.document_type.in_(["national_id", "passport"])
    ).first()

    user = db.session.get(User, user_id)
    if user and approved:
        user.is_verified = True
        user.verification_status = "verified"

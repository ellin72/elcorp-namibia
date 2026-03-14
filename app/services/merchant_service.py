"""Merchant onboarding service."""

from __future__ import annotations

import uuid

import structlog

from app.extensions import db
from app.models.merchant import Merchant
from app.services.audit_service import log_event
from app.utils.errors import ConflictError, NotFoundError
from app.utils.encryption import encrypt_value

logger = structlog.get_logger()


def onboard_merchant(data: dict, onboarded_by: str | None = None) -> Merchant:
    """Create and activate a new merchant."""
    if Merchant.query.filter_by(contact_email=data["contact_email"]).first():
        raise ConflictError("A merchant with this email already exists")

    api_key = f"sk_sandbox_{uuid.uuid4().hex}"

    # Encrypt settlement account if provided
    settlement_account = data.get("settlement_account", "")
    if settlement_account:
        settlement_account = encrypt_value(settlement_account)

    merchant = Merchant(
        name=data["name"],
        business_type=data.get("business_type", ""),
        registration_number=data.get("registration_number", ""),
        contact_email=data["contact_email"],
        contact_phone=data.get("contact_phone", ""),
        address=data.get("address", ""),
        api_key=api_key,
        webhook_url=data.get("webhook_url", ""),
        settlement_bank=data.get("settlement_bank", ""),
        settlement_account=settlement_account,
        settlement_frequency=data.get("settlement_frequency", "daily"),
        onboarded_by=onboarded_by,
        status="active",
        sandbox_mode=True,
    )
    db.session.add(merchant)
    db.session.commit()

    log_event(
        "merchant.onboarded",
        user_id=onboarded_by,
        entity_type="merchant",
        entity_id=merchant.id,
        detail={"name": data["name"]},
    )
    logger.info("merchant.onboarded", merchant_id=merchant.id, name=data["name"])
    return merchant


def get_merchant(merchant_id: str) -> Merchant:
    merchant = db.session.get(Merchant, merchant_id)
    if not merchant:
        raise NotFoundError("Merchant not found")
    return merchant


def list_merchants(page: int = 1, per_page: int = 20):
    return Merchant.query.order_by(Merchant.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )


def update_merchant(merchant_id: str, data: dict) -> Merchant:
    merchant = get_merchant(merchant_id)
    allowed = {
        "name", "business_type", "registration_number", "contact_email",
        "contact_phone", "address", "webhook_url", "settlement_bank",
        "settlement_frequency",
    }
    for key in allowed:
        if key in data:
            setattr(merchant, key, data[key])

    if "settlement_account" in data and data["settlement_account"]:
        merchant.settlement_account = encrypt_value(data["settlement_account"])

    db.session.commit()
    log_event(
        "merchant.updated",
        entity_type="merchant",
        entity_id=merchant_id,
        detail={"fields": [k for k in data if k in allowed]},
    )
    return merchant


def deactivate_merchant(merchant_id: str) -> Merchant:
    merchant = get_merchant(merchant_id)
    merchant.is_active = False
    merchant.status = "deactivated"
    db.session.commit()
    log_event("merchant.deactivated", entity_type="merchant", entity_id=merchant_id)
    return merchant

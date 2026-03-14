"""Payment service — create payments, tokenisation, sandbox gateway, settlement stubs."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import structlog

from app.extensions import db
from app.models.payment import Payment, PaymentToken
from app.models.merchant import Merchant
from app.services.audit_service import log_event
from app.utils.errors import NotFoundError, ValidationError

logger = structlog.get_logger()


# ---- Tokenisation ----

def create_payment_token(
    user_id: str,
    instrument_type: str,
    last_four: str,
) -> PaymentToken:
    """Create a tokenised payment instrument for a user."""
    if instrument_type not in ("card", "bank_account"):
        raise ValidationError("instrument_type must be 'card' or 'bank_account'")

    token = PaymentToken(
        user_id=user_id,
        token=f"tok_{uuid.uuid4().hex}",
        instrument_type=instrument_type,
        last_four=last_four[-4:] if last_four else "",
    )
    db.session.add(token)
    db.session.commit()

    log_event(
        "payment.token_created",
        user_id=user_id,
        entity_type="payment_token",
        entity_id=token.id,
    )
    return token


# ---- Payment creation ----

def create_payment(
    user_id: str,
    merchant_id: str,
    amount: int,
    currency: str = "NAD",
    description: str = "",
    payment_token_id: str | None = None,
) -> Payment:
    """Create a new payment in sandbox mode."""
    merchant = db.session.get(Merchant, merchant_id)
    if not merchant or not merchant.is_active:
        raise NotFoundError("Merchant not found or inactive")

    reference = f"pay_{uuid.uuid4().hex[:16]}"

    payment = Payment(
        user_id=user_id,
        merchant_id=merchant_id,
        amount=amount,
        currency=currency,
        description=description,
        reference=reference,
        payment_token_id=payment_token_id,
        status="pending",
    )
    db.session.add(payment)
    db.session.commit()

    log_event(
        "payment.created",
        user_id=user_id,
        entity_type="payment",
        entity_id=payment.id,
        detail={"amount": amount, "currency": currency, "merchant_id": merchant_id},
    )
    logger.info("payment.created", payment_id=payment.id, amount=amount)
    return payment


# ---- Sandbox gateway simulation ----

def process_payment(payment_id: str) -> Payment:
    """Simulate processing through the sandbox gateway."""
    payment = db.session.get(Payment, payment_id)
    if not payment:
        raise NotFoundError("Payment not found")
    if payment.status != "pending":
        raise ValidationError(f"Payment is already {payment.status}")

    payment.status = "processing"
    db.session.commit()

    # Simulate instant gateway approval for sandbox
    payment.status = "completed"
    payment.gateway_ref = f"gw_{uuid.uuid4().hex[:12]}"
    payment.completed_at = datetime.now(timezone.utc)
    db.session.commit()

    log_event(
        "payment.completed",
        user_id=payment.user_id,
        entity_type="payment",
        entity_id=payment.id,
        detail={"gateway_ref": payment.gateway_ref},
    )
    logger.info("payment.completed", payment_id=payment.id)
    return payment


# ---- Test payout simulation ----

def simulate_payout(merchant_id: str, amount: int, currency: str = "NAD") -> dict:
    """Simulate a settlement payout to a merchant."""
    merchant = db.session.get(Merchant, merchant_id)
    if not merchant:
        raise NotFoundError("Merchant not found")

    payout_ref = f"po_{uuid.uuid4().hex[:12]}"
    log_event(
        "payment.payout_simulated",
        entity_type="merchant",
        entity_id=merchant_id,
        detail={"amount": amount, "currency": currency, "payout_ref": payout_ref},
    )
    return {
        "payout_ref": payout_ref,
        "merchant_id": merchant_id,
        "amount": amount,
        "currency": currency,
        "status": "settled",
        "settled_at": datetime.now(timezone.utc).isoformat(),
    }


# ---- Queries ----

def get_payment(payment_id: str) -> Payment:
    payment = db.session.get(Payment, payment_id)
    if not payment:
        raise NotFoundError("Payment not found")
    return payment


def list_user_payments(user_id: str, page: int = 1, per_page: int = 20):
    return Payment.query.filter_by(user_id=user_id).order_by(
        Payment.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)


def list_merchant_payments(merchant_id: str, page: int = 1, per_page: int = 20):
    return Payment.query.filter_by(merchant_id=merchant_id).order_by(
        Payment.created_at.desc()
    ).paginate(page=page, per_page=per_page, error_out=False)

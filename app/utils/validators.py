"""Input validators used across services and routes."""

from __future__ import annotations

import re

from email_validator import validate_email, EmailNotValidError
from app.utils.errors import ValidationError

_PHONE_RE = re.compile(r"^\+?[1-9]\d{6,14}$")
_PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*]).{8,128}$")

VALID_DOC_TYPES = {"national_id", "passport", "drivers_license", "proof_of_address"}
VALID_CURRENCIES = {"NAD", "USD", "ZAR", "EUR"}


def validate_signup_payload(data: dict) -> dict:
    """Validate and return cleaned signup data or raise ValidationError."""
    errors: list[str] = []

    email = (data.get("email") or "").strip().lower()
    try:
        valid = validate_email(email, check_deliverability=False)
        email = valid.normalized
    except EmailNotValidError:
        errors.append("Invalid email address")

    password = data.get("password", "")
    if not _PASSWORD_RE.match(password):
        errors.append(
            "Password must be 8–128 chars with uppercase, lowercase, digit, and special character"
        )

    first_name = (data.get("first_name") or "").strip()
    last_name = (data.get("last_name") or "").strip()
    if not first_name:
        errors.append("first_name is required")
    if not last_name:
        errors.append("last_name is required")

    phone = (data.get("phone") or "").strip()
    if phone and not _PHONE_RE.match(phone):
        errors.append("Invalid phone number format")

    if errors:
        raise ValidationError("Validation failed", detail="; ".join(errors))

    return {
        "email": email,
        "password": password,
        "first_name": first_name,
        "last_name": last_name,
        "phone": phone,
    }


def validate_payment_payload(data: dict) -> dict:
    errors: list[str] = []

    amount = data.get("amount")
    if not isinstance(amount, int) or amount <= 0:
        errors.append("amount must be a positive integer (smallest currency unit)")

    currency = (data.get("currency") or "NAD").upper()
    if currency not in VALID_CURRENCIES:
        errors.append(f"currency must be one of {VALID_CURRENCIES}")

    merchant_id = data.get("merchant_id", "")
    if not merchant_id:
        errors.append("merchant_id is required")

    if errors:
        raise ValidationError("Validation failed", detail="; ".join(errors))

    return {
        "amount": amount,
        "currency": currency,
        "merchant_id": merchant_id,
        "description": (data.get("description") or "")[:500],
        "payment_token_id": data.get("payment_token_id"),
    }


def validate_merchant_payload(data: dict) -> dict:
    errors: list[str] = []

    name = (data.get("name") or "").strip()
    if not name:
        errors.append("name is required")

    contact_email = (data.get("contact_email") or "").strip().lower()
    try:
        valid = validate_email(contact_email, check_deliverability=False)
        contact_email = valid.normalized
    except EmailNotValidError:
        errors.append("Invalid contact_email")

    if errors:
        raise ValidationError("Validation failed", detail="; ".join(errors))

    return {
        "name": name,
        "contact_email": contact_email,
        "business_type": (data.get("business_type") or "")[:100],
        "registration_number": (data.get("registration_number") or "")[:100],
        "contact_phone": (data.get("contact_phone") or "")[:30],
        "address": (data.get("address") or "")[:500],
        "webhook_url": (data.get("webhook_url") or "")[:500],
        "settlement_bank": (data.get("settlement_bank") or "")[:100],
        "settlement_account": (data.get("settlement_account") or "")[:100],
        "settlement_frequency": data.get("settlement_frequency", "daily"),
    }

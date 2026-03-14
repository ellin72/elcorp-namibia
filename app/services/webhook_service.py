"""Webhook delivery service — signs & posts events to merchant endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid

import requests
import structlog

from app.extensions import db
from app.models.webhook import WebhookDelivery, WebhookSubscription

logger = structlog.get_logger()

DELIVERY_TIMEOUT = 10  # seconds


def create_subscription(
    merchant_id: str,
    url: str,
    events: str = "*",
) -> WebhookSubscription:
    """Register a new webhook subscription for a merchant."""
    secret = f"whsec_{uuid.uuid4().hex}"
    sub = WebhookSubscription(
        merchant_id=merchant_id,
        url=url,
        secret=secret,
        events=events,
    )
    db.session.add(sub)
    db.session.commit()
    return sub


def list_subscriptions(merchant_id: str) -> list[WebhookSubscription]:
    return WebhookSubscription.query.filter_by(merchant_id=merchant_id, is_active=True).all()


def delete_subscription(subscription_id: str) -> None:
    sub = db.session.get(WebhookSubscription, subscription_id)
    if sub:
        sub.is_active = False
        db.session.commit()


def dispatch_event(merchant_id: str, event: str, payload: dict) -> None:
    """Send an event to all active subscriptions for a merchant."""
    subs = WebhookSubscription.query.filter_by(
        merchant_id=merchant_id, is_active=True
    ).all()

    for sub in subs:
        # Check event filter
        if sub.events != "*" and event not in sub.events.split(","):
            continue
        _deliver(sub, event, payload)


def _deliver(sub: WebhookSubscription, event: str, payload: dict) -> WebhookDelivery:
    """Post the event and record the delivery attempt."""
    body = json.dumps({"event": event, "data": payload}, default=str)
    signature = hmac.new(
        sub.secret.encode(), body.encode(), hashlib.sha256
    ).hexdigest()

    delivery = WebhookDelivery(
        subscription_id=sub.id,
        event=event,
        payload=body,
    )

    try:
        resp = requests.post(
            sub.url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Elcorp-Signature": signature,
                "X-Elcorp-Event": event,
            },
            timeout=DELIVERY_TIMEOUT,
        )
        delivery.response_status = resp.status_code
        delivery.response_body = resp.text[:2000]
        delivery.success = 200 <= resp.status_code < 300
    except requests.RequestException as exc:
        delivery.response_body = str(exc)[:2000]
        delivery.success = False

    db.session.add(delivery)
    db.session.commit()

    logger.info(
        "webhook.delivered",
        subscription_id=sub.id,
        event=event,
        success=delivery.success,
        status=delivery.response_status,
    )
    return delivery

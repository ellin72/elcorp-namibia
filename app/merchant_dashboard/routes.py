"""Merchant dashboard routes — overview, transactions, webhooks."""

from flask import g, redirect, render_template, request, session, url_for

from app.merchant_dashboard import merchant_dashboard_bp
from app.extensions import db
from app.models.merchant import Merchant
from app.models.payment import Payment
from app.models.webhook import WebhookSubscription, WebhookDelivery


def _current_merchant() -> Merchant | None:
    mid = session.get("merchant_id")
    if not mid:
        return None
    return db.session.get(Merchant, mid)


def _login_required(fn):
    """Simple session-based auth for merchant dashboard."""
    from functools import wraps

    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not _current_merchant():
            return redirect(url_for("merchant_dashboard.login"))
        return fn(*args, **kwargs)
    return wrapper


# ---------- Auth ----------

@merchant_dashboard_bp.route("/login", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        api_key = request.form.get("api_key", "").strip()
        merchant = Merchant.query.filter_by(api_key=api_key, is_active=True).first()
        if merchant:
            session["merchant_id"] = merchant.id
            return redirect(url_for("merchant_dashboard.overview"))
        error = "Invalid API key"
    return render_template("merchant/login.html", error=error)


@merchant_dashboard_bp.route("/logout")
def logout():
    session.pop("merchant_id", None)
    return redirect(url_for("merchant_dashboard.login"))


# ---------- Overview ----------

@merchant_dashboard_bp.route("/")
@_login_required
def overview():
    merchant = _current_merchant()
    total_payments = Payment.query.filter_by(merchant_id=merchant.id).count()
    completed = Payment.query.filter_by(merchant_id=merchant.id, status="completed").count()
    total_volume = (
        db.session.query(db.func.coalesce(db.func.sum(Payment.amount), 0))
        .filter_by(merchant_id=merchant.id, status="completed")
        .scalar()
    )
    recent = (
        Payment.query.filter_by(merchant_id=merchant.id)
        .order_by(Payment.created_at.desc())
        .limit(10)
        .all()
    )
    return render_template(
        "merchant/overview.html",
        merchant=merchant,
        total_payments=total_payments,
        completed=completed,
        total_volume=total_volume,
        recent=recent,
    )


# ---------- Transactions ----------

@merchant_dashboard_bp.route("/transactions")
@_login_required
def transactions():
    merchant = _current_merchant()
    page = request.args.get("page", 1, type=int)
    pagination = (
        Payment.query.filter_by(merchant_id=merchant.id)
        .order_by(Payment.created_at.desc())
        .paginate(page=page, per_page=25, error_out=False)
    )
    return render_template(
        "merchant/transactions.html",
        merchant=merchant,
        pagination=pagination,
    )


# ---------- Webhooks ----------

@merchant_dashboard_bp.route("/webhooks")
@_login_required
def webhooks():
    merchant = _current_merchant()
    subs = WebhookSubscription.query.filter_by(merchant_id=merchant.id).all()
    return render_template("merchant/webhooks.html", merchant=merchant, subscriptions=subs)


@merchant_dashboard_bp.route("/webhooks/<sub_id>/deliveries")
@_login_required
def webhook_deliveries(sub_id: str):
    merchant = _current_merchant()
    deliveries = (
        WebhookDelivery.query.filter_by(subscription_id=sub_id)
        .order_by(WebhookDelivery.created_at.desc())
        .limit(50)
        .all()
    )
    return render_template(
        "merchant/deliveries.html",
        merchant=merchant,
        deliveries=deliveries,
        subscription_id=sub_id,
    )

"""Dashboard routes for user profile, vehicles, Elcoin wallet, and security settings."""
from flask import render_template, flash, redirect, url_for, jsonify
from flask_login import login_required, current_user
from decimal import Decimal
from ..models import Transaction, User, Vehicle
from app import db
from .forms import VehicleForm, ProfileForm, PasswordChangeForm, SendCoinForm, TwoFactorForm
from . import bp
from ..utils import generate_otp_secret  # helper to create a secret


# 🔹 Make `user` available in all templates rendered in this blueprint
@bp.app_context_processor
def inject_user():
    """Inject current_user into all templates."""
    return dict(user=current_user)


#############################################################
@bp.route('/home')
@login_required
def home():
    """Dashboard home view — HTML template renders with JS-based live widgets."""
    return render_template("dashboard/home.html")


@bp.route('/api/wallet_overview')
@login_required
def api_wallet_overview():
    """JSON endpoint for wallet balance and recent transactions."""
    sent = db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0))\
        .filter(Transaction.from_user_id == current_user.id).scalar()
    received = db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0))\
        .filter(Transaction.to_user_id == current_user.id).scalar()
    balance = received - sent

    recent_tx = Transaction.query.filter(
        (Transaction.from_user_id == current_user.id) |
        (Transaction.to_user_id == current_user.id)
    ).order_by(Transaction.timestamp.desc()).limit(5).all()

    tx_list = [{
        "timestamp": tx.timestamp.strftime("%Y-%m-%d %H:%M"),
        "direction": "out" if tx.from_user_id == current_user.id else "in",
        "counterparty": tx.receiver.wallet_address if tx.from_user_id == current_user.id else tx.sender.wallet_address,
        "amount": str(tx.amount)
    } for tx in recent_tx]

    return jsonify({"balance": str(balance), "transactions": tx_list})


@bp.route('/api/vehicles_overview')
@login_required
def api_vehicles_overview():
    """JSON endpoint for vehicle count and status."""
    vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    return jsonify({
        "count": len(vehicles),
        "pending": sum(1 for v in vehicles if not v.verified),
        "vehicles": [
            {"make": v.make, "model": v.model, "verified": v.verified}
            for v in vehicles
        ]
    })

#############################################################

@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """View and update user profile."""
    pform = ProfileForm(obj=current_user)
    pwdform = PasswordChangeForm()

    if pform.validate_on_submit() and pform.submit.data:
        current_user.full_name = pform.full_name.data.strip()
        current_user.email = pform.email.data.lower()
        current_user.phone = pform.phone.data.strip() or None
        current_user.organization = pform.organization.data.strip() or None
        db.session.commit()
        flash("Profile updated successfully.", "success")
        return redirect(url_for("dashboard.profile"))

    if pwdform.validate_on_submit() and pwdform.submit.data:
        if not current_user.check_password(pwdform.current_password.data):
            flash("Current password is incorrect.", "danger")
        else:
            current_user.set_password(pwdform.new_password.data)
            db.session.commit()
            flash("Password changed successfully.", "success")
            return redirect(url_for("dashboard.profile"))

    return render_template("dashboard/profile.html", pform=pform, pwdform=pwdform)


@bp.route("/elcar", methods=["GET", "POST"])
@login_required
def elcar():
    """Manage user's vehicles."""
    form = VehicleForm()
    if form.validate_on_submit():
        if form.id.data:
            v = Vehicle.query.get(int(form.id.data))
        else:
            v = Vehicle(user_id=current_user.id)
        v.make = form.make.data
        v.model = form.model.data
        v.plate_number = form.plate_number.data.strip()
        db.session.add(v)
        db.session.commit()
        flash("Vehicle saved.", "success")
        return redirect(url_for("dashboard.elcar"))

    vehicles = Vehicle.query.filter_by(user_id=current_user.id).all()
    return render_template("dashboard/elcar.html", vehicles=vehicles, form=form)


@bp.route("/elcoin", methods=["GET", "POST"])
@login_required
def elcoin():
    """View balance, transaction history, and send Elcoin."""
    form = SendCoinForm()
    if form.validate_on_submit():
        recipient = User.query.filter_by(
            wallet_address=form.recipient_address.data.strip()
        ).first()
        if not recipient:
            flash("No user with that wallet address.", "danger")
        else:
            tx = Transaction(
                from_user_id=current_user.id,
                to_user_id=recipient.id,
                amount=Decimal(form.amount.data)
            )
            db.session.add(tx)
            db.session.commit()
            flash("Elcoin sent successfully.", "success")
            return redirect(url_for("dashboard.elcoin"))

    sent = db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0))\
        .filter(Transaction.from_user_id == current_user.id).scalar()
    received = db.session.query(db.func.coalesce(db.func.sum(Transaction.amount), 0))\
        .filter(Transaction.to_user_id == current_user.id).scalar()
    balance = received - sent

    history = Transaction.query.filter(
        (Transaction.from_user_id == current_user.id) |
        (Transaction.to_user_id == current_user.id)
    ).order_by(Transaction.timestamp.desc()).all()

    return render_template("dashboard/elcoin.html", form=form, balance=balance, history=history)


@bp.route("/settings", methods=["GET", "POST"])
@login_required
def settings():
    """Manage security settings, including two-factor authentication."""
    form = TwoFactorForm(enable_2fa=bool(current_user.otp_secret))

    if form.validate_on_submit():
        if form.enable_2fa.data and not current_user.otp_secret:
            current_user.otp_secret = generate_otp_secret()
        elif not form.enable_2fa.data:
            current_user.otp_secret = None
        db.session.commit()
        flash("Security settings updated.", "success")
        return redirect(url_for("dashboard.settings"))

    return render_template("dashboard/settings.html", form=form)
#############################################################
# Note: The actual HTML templates (e.g., dashboard/home.html, dashboard/profile.html)
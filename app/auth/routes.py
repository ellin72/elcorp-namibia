from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from passlib.hash import bcrypt
import pyotp
from sqlalchemy import desc
from ..extensions import db, limiter
from ..audit import log_action
from .forms import RegisterForm, LoginForm, TwoFactorForm, ChangePasswordForm
from ..models import User, PasswordHistory
from . import bp

# This file contains the authentication routes for user registration, login, 2FA, and password management.
# @bp.route("/login"), @bp.route("/register") etc.

@bp.route("/register", methods=["GET","POST"])
@limiter.limit("5/minute")
def register():
    if current_user.is_authenticated:
        flash("You are already logged in.", "info")
        return redirect(url_for("main.index"))
    
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("auth.login"))
        user = User(email=form.email.data.lower(),
                    password_hash=bcrypt.hash(form.password.data))
        db.session.add(user)
        db.session.commit()
        flash("Account created. Please sign in.", "success")
        return redirect(url_for("auth.login"))
    return render_template("auth/register.html", form=form)

@bp.route("/login", methods=["GET","POST"])
@limiter.limit("10/minute")
def login():
    if current_user.is_authenticated:
        flash("You are already logged in.", "info")
        return redirect(url_for("main.index"))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user and bcrypt.verify(form.password.data, user.password_hash):
            if user.otp_secret:
                request.environ["pending_user_id"] = user.id
                return redirect(url_for("auth.two_factor"))
            login_user(user, remember=form.remember.data)
            flash("Welcome back.", "success")
            return redirect(url_for("main.index"))
        flash("Invalid credentials.", "danger")
    return render_template("auth/login.html", form=form)

@bp.route("/2fa", methods=["GET","POST"])
@login_required
def two_factor():
    if not current_user.otp_secret:
        flash("2FA not enabled for your account.", "warning")
        return redirect(url_for("main.index"))
    if "pending_user_id" not in request.environ:
        flash("2FA session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))
    if request.environ["pending_user_id"] != current_user.id:
        flash("Invalid 2FA session. Please log in again.", "danger")
        return redirect(url_for("auth.login"))
    
    # Clear pending_user_id to prevent reuse
    del request.environ["pending_user_id"]
    
    # If 2FA is already verified, redirect to main page
    if current_user.is_authenticated and current_user.otp_verified:
        flash("2FA already verified.", "info")
        return redirect(url_for("main.index"))
    
    # If 2FA secret is not set, redirect to setup
    if not current_user.otp_secret:
        flash("2FA not set up. Please configure it first.", "warning")
        return redirect(url_for("auth.setup_2fa"))
    
    # If 2FA secret is set, proceed to verification
    if current_user.otp_verified:
        flash("2FA already verified.", "info")
        return redirect(url_for("main.index"))
    
    # If we reach here, user needs to enter 2FA code
    # Render 2FA form
    form = TwoFactorForm()
    if form.validate_on_submit():
        totp = pyotp.TOTP(current_user.otp_secret)
        if totp.verify(form.token.data, valid_window=1):
            flash("2FA verified.", "success")
            return redirect(url_for("main.index"))
        flash("Invalid code.", "danger")
    return render_template("auth/two_factor.html", form=form)

@bp.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("main.index"))

@bp.route("/change-password", methods=["GET","POST"])
@login_required
@limiter.limit("5/minute")
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not bcrypt.verify(form.current_password.data, current_user.password_hash):
            flash("Current password is incorrect.", "danger")
            log_action("password_change_failed", {"reason":"bad_current_password"})
            return redirect(url_for("auth.change_password"))

        if current_app.config["REQUIRE_2FA_REAUTH"] and current_user.otp_secret:
            if not form.token.data:
                flash("Enter your 2FA code to continue.", "warning")
                log_action("password_change_failed",{"reason":"missing_2fa"})
                return redirect(url_for("auth.change_password"))
            totp = pyotp.TOTP(current_user.otp_secret)
            if not totp.verify(form.token.data, valid_window=1):
                flash("Invalid 2FA code.", "danger")
                log_action("password_change_failed",{"reason":"bad_2fa"})
                return redirect(url_for("auth.change_password"))

        # Prevent reuse
        N = current_app.config["PASSWORD_HISTORY_COUNT"]
        recent = [current_user.password_hash] + [
            ph.password_hash for ph in PasswordHistory.query
                .filter_by(user_id=current_user.id)
                .order_by(desc(PasswordHistory.created_at))
                .limit(N).all()
        ]
        for old in recent:
            if bcrypt.verify(form.new_password.data, old):
                flash(f"New password must not match your last {N} passwords.", "danger")
                log_action("password_change_failed",{"reason":"password_reuse"})
                return redirect(url_for("auth.change_password"))

        # Save history, update, prune
        db.session.add(PasswordHistory(user_id=current_user.id,
                                       password_hash=current_user.password_hash))
        current_user.password_hash = bcrypt.hash(form.new_password.data)
        db.session.commit()

        all_hist = PasswordHistory.query.filter_by(user_id=current_user.id) \
                     .order_by(desc(PasswordHistory.created_at)).all()
        if len(all_hist) > N:
            for ph in all_hist[N:]:
                db.session.delete(ph)
            db.session.commit()

        log_action("password_change",{"user_id":current_user.id,
                                     "two_factor_checked":bool(current_user.otp_secret)})
        flash("Password updated successfully.", "success")
        return redirect(url_for("main.index"))
    return render_template("auth/change_password.html", form=form)

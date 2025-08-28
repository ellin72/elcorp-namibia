"""Authentication routes for user registration, login, 2FA, and password management."""

from urllib.parse import urlparse
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from passlib.hash import bcrypt
import pyotp
from sqlalchemy import desc
from app.email import send_password_reset_email
from app.models import User, PasswordHistory, Role
from ..extensions import db, limiter
from ..audit import log_action
from .forms import RegisterForm, LoginForm, TwoFactorForm, ChangePasswordForm
from .forms import ResetPasswordRequestForm, ResetPasswordForm
from . import bp

# -------------------------
# USER REGISTRATION
# -------------------------
@bp.route("/register", methods=["GET", "POST"])
@limiter.limit("5/minute")
def register():
    """Handle user registration with form validation, role assignment, and account creation."""
    if current_user.is_authenticated:
        flash("You are already logged in.", "info")
        return redirect(url_for("main.index"))
    
    form = RegisterForm()
    if form.validate_on_submit():
        if User.query.filter_by(email=form.email.data.lower()).first():
            flash("Email already registered.", "warning")
            return redirect(url_for("auth.login"))

        # Get the selected role or fall back to "user"
        selected_role = Role.query.filter_by(name=form.role.data).first()
        if not selected_role:
            selected_role = Role.query.filter_by(name="user").first()

        user = User(
            full_name=form.full_name.data.strip(),
            username=form.username.data.strip().lower(),
            email=form.email.data.lower(),
            phone=form.phone.data.strip(),
            organization=form.organization.data.strip() if form.organization.data else None,
            password_hash=bcrypt.hash(form.password.data),
            agreed_terms=form.agree_terms.data,
            role=selected_role   # assign relationship directly
        )

        db.session.add(user)
        db.session.commit()
        flash("Account created successfully. Please sign in.", "success")
        return redirect(url_for("auth.login"))

    return render_template("auth/register.html", form=form)

# -------------------------
# LOGIN
# -------------------------
@bp.route("/login", methods=["GET", "POST"])
@limiter.limit("10/minute")
def login():
    """Handle user login with form validation, 2FA, and session management."""
    if current_user.is_authenticated:
        flash("You are already logged in.", "info")
        return redirect(url_for("dashboard.home"))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data.strip().lower()).first()
        if user and bcrypt.verify(form.password.data, user.password_hash):
            if user.otp_secret:
                request.environ["pending_user_id"] = user.id
                return redirect(url_for("auth.two_factor"))

            login_user(user, remember=form.remember.data)
            flash("Welcome back.", "success")

            next_page = request.args.get("next")
            if not next_page or urlparse(next_page).netloc != "":
                next_page = url_for("dashboard.home")
            return redirect(next_page)

        flash("Invalid credentials.", "danger")

    return render_template("auth/login.html", form=form)

# -------------------------
# TWO FACTOR AUTH
# -------------------------
@bp.route("/2fa", methods=["GET", "POST"])
@login_required
def two_factor():
    """Handle two-factor authentication (2FA) verification."""
    if not current_user.otp_secret:
        flash("2FA not enabled for your account.", "warning")
        return redirect(url_for("dashboard.home"))

    if "pending_user_id" not in request.environ:
        flash("2FA session expired. Please log in again.", "warning")
        return redirect(url_for("auth.login"))

    if request.environ["pending_user_id"] != current_user.id:
        flash("Invalid 2FA session. Please log in again.", "danger")
        return redirect(url_for("auth.login"))

    form = TwoFactorForm()
    if form.validate_on_submit():
        totp = pyotp.TOTP(current_user.otp_secret)
        if totp.verify(form.token.data, valid_window=1):
            flash("2FA verified.", "success")
            del request.environ["pending_user_id"]

            next_page = request.args.get("next")
            if not next_page or urlparse(next_page).netloc != "":
                next_page = url_for("dashboard.home")
            return redirect(next_page)

        flash("Invalid code.", "danger")

    return render_template("auth/two_factor.html", form=form)

# -------------------------
# LOGOUT
# -------------------------
@bp.route("/logout")
@login_required
def logout():
    """Log out the current user and redirect to the main page."""
    logout_user()
    flash("Signed out.", "info")
    return redirect(url_for("main.index"))

# -------------------------
# CHANGE PASSWORD
# -------------------------
@bp.route("/change-password", methods=["GET", "POST"])
@login_required
@limiter.limit("5/minute")
def change_password():
    """Allow logged-in users to change their password with validation and history checks."""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if not bcrypt.verify(form.current_password.data, current_user.password_hash):
            flash("Current password is incorrect.", "danger")
            log_action("password_change_failed", {"reason": "bad_current_password"})
            return redirect(url_for("auth.change_password"))

        if current_app.config["REQUIRE_2FA_REAUTH"] and current_user.otp_secret:
            if not form.token.data:
                flash("Enter your 2FA code to continue.", "warning")
                log_action("password_change_failed", {"reason": "missing_2fa"})
                return redirect(url_for("auth.change_password"))
            totp = pyotp.TOTP(current_user.otp_secret)
            if not totp.verify(form.token.data, valid_window=1):
                flash("Invalid 2FA code.", "danger")
                log_action("password_change_failed", {"reason": "bad_2fa"})
                return redirect(url_for("auth.change_password"))

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
                log_action("password_change_failed", {"reason": "password_reuse"})
                return redirect(url_for("auth.change_password"))

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

        log_action("password_change", {"user_id": current_user.id,
                                       "two_factor_checked": bool(current_user.otp_secret)})
        flash("Password updated successfully.", "success")
        return redirect(url_for("main.index"))

    return render_template("auth/change_password.html", form=form)

# -------------------------
# FORGOT PASSWORD
# -------------------------
@bp.route("/forgot_password", methods=["GET", "POST"])
def forgot_password():
    """Handle password reset requests by sending a reset email if the user exists."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    
    expiry = current_app.config.get("PASSWORD_RESET_TOKEN_EXPIRY")
    print("PASSWORD_RESET_TOKEN_EXPIRY:", expiry, type(expiry))

    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for reset instructions.')
        return redirect(url_for('auth.login'))

    return render_template(
        'auth/forgot_password.html',
        title='Reset Password',
        form=form
    )

# -------------------------
# RESET PASSWORD
# -------------------------
@bp.route("/reset_password/<token>", methods=["GET", "POST"])
def reset_password(token):
    """Allow users to reset their password using a valid token."""
    if current_user.is_authenticated:
        return redirect(url_for("main.index"))
    
    user = User.verify_reset_password_token(token)
    if not user:
        flash('Invalid or expired token.')
        return redirect(url_for('auth.login'))

    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset. You can now sign in.')
        return redirect(url_for('auth.login'))

    return render_template(
        'auth/reset_password.html',
        title='Set New Password',
        form=form
    )

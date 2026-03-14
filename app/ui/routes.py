"""UI routes — serves HTML pages; all data fetched client-side via the API."""

from flask import render_template
from app.ui import ui_bp


@ui_bp.route("/")
def landing():
    return render_template("ui/landing.html")


@ui_bp.route("/login")
def login():
    return render_template("ui/login.html")


@ui_bp.route("/signup")
def signup():
    return render_template("ui/signup.html")


@ui_bp.route("/dashboard")
def dashboard():
    return render_template("ui/dashboard.html")


@ui_bp.route("/profile")
def profile():
    return render_template("ui/profile.html")


@ui_bp.route("/kyc")
def kyc():
    return render_template("ui/kyc.html")


@ui_bp.route("/payments")
def payments():
    return render_template("ui/payments.html")


@ui_bp.route("/merchants")
def merchants():
    return render_template("ui/merchants.html")


@ui_bp.route("/webhooks")
def webhooks():
    return render_template("ui/webhooks.html")


@ui_bp.route("/admin")
def admin():
    return render_template("ui/admin.html")


@ui_bp.route("/health")
def health():
    return render_template("ui/health.html")

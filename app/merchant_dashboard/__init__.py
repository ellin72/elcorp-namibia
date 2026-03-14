"""Merchant dashboard blueprint — server-rendered UI for merchant portal."""

from flask import Blueprint

merchant_dashboard_bp = Blueprint(
    "merchant_dashboard",
    __name__,
    template_folder="templates",
    static_folder="static",
)

from app.merchant_dashboard import routes  # noqa: E402, F401

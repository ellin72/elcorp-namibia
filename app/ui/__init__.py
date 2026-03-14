"""Frontend blueprint — serves the SPA-style UI for interacting with all APIs."""

from flask import Blueprint

ui_bp = Blueprint(
    "ui",
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/ui/static",
)

from app.ui import routes  # noqa: E402, F401

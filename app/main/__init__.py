from flask import Blueprint

bp = Blueprint(
    "main",
    __name__,
    template_folder="templates/main"   # points to app/main/templates/main/
)

from . import routes   # noqa: E402,F401

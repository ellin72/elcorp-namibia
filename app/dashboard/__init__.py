# app/dashboard/__init__.py
from flask import Blueprint

bp = Blueprint(
    "dashboard",
    __name__,
    url_prefix="/dashboard",
    template_folder="templates/dashboard"   # points to app/dashboard/templates/dashboard/
)

from . import routes  # noqa
# This import is necessary to register the routes with the blueprint
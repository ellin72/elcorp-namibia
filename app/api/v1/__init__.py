"""API v1 blueprint — aggregates all sub-route modules."""

from flask import Blueprint

api_v1_bp = Blueprint("api_v1", __name__)

# Import route modules so their @api_v1_bp decorators register
from app.api.v1 import auth  # noqa: E402, F401
from app.api.v1 import identity  # noqa: E402, F401
from app.api.v1 import payments  # noqa: E402, F401
from app.api.v1 import merchants  # noqa: E402, F401
from app.api.v1 import admin  # noqa: E402, F401
from app.api.v1 import health  # noqa: E402, F401

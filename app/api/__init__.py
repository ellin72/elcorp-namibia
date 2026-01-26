"""
app/api/__init__.py - API module for REST endpoints
"""
from flask import Blueprint

bp = Blueprint('api', __name__, url_prefix='/api/v1')

from . import routes
from . import dashboard

def register_blueprints(app):
    """Register all API blueprints."""
    app.register_blueprint(bp)
    app.register_blueprint(dashboard.bp)
"""
app/api_v1/__init__.py - API v1 Blueprint for versioned endpoints
"""
from flask import Blueprint

bp = Blueprint('api_v1', __name__, url_prefix='/api/v1')

from . import auth_routes, users_routes, service_requests_routes

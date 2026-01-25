"""
app/api/__init__.py - API module for REST endpoints
"""
from flask import Blueprint

bp = Blueprint('api', __name__, url_prefix='/api/v1')

from . import routes

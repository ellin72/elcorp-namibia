"""Health and readiness endpoints."""

from flask import jsonify

from app.api.v1 import api_v1_bp
from app.extensions import db


@api_v1_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "elcorp-api", "version": "1.0.0"})


@api_v1_bp.route("/health/ready", methods=["GET"])
def readiness():
    """Check that the database is reachable."""
    try:
        db.session.execute(db.text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    status_code = 200 if db_ok else 503
    return jsonify({"status": "ready" if db_ok else "not_ready", "database": db_ok}), status_code

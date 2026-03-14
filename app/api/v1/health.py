"""Health and readiness endpoints."""

import time

from flask import current_app, jsonify

from app.api.v1 import api_v1_bp
from app.extensions import db


@api_v1_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "healthy", "service": "elcorp-api", "version": "1.0.0"})


@api_v1_bp.route("/health/ready", methods=["GET"])
def readiness():
    """Deep health check — DB, cache, and component status."""
    checks: dict[str, dict] = {}

    # --- Database ---
    t0 = time.monotonic()
    try:
        db.session.execute(db.text("SELECT 1"))
        checks["database"] = {"status": "ok", "latency_ms": _ms(t0)}
    except Exception as exc:
        checks["database"] = {"status": "error", "error": str(exc)}

    # --- Redis / cache ---
    t0 = time.monotonic()
    try:
        import redis
        r = redis.from_url(current_app.config.get("REDIS_URL", ""), socket_timeout=2)
        r.ping()
        checks["redis"] = {"status": "ok", "latency_ms": _ms(t0)}
    except Exception:
        checks["redis"] = {"status": "unavailable", "latency_ms": _ms(t0)}

    # --- Celery ---
    celery_broker = current_app.config.get("CELERY_BROKER_URL", "")
    checks["celery"] = {
        "status": "configured" if celery_broker else "not_configured",
        "broker": celery_broker.split("@")[-1] if celery_broker else "",
    }

    # --- Storage ---
    upload = current_app.config.get("UPLOAD_FOLDER", "uploads")
    import os
    checks["storage"] = {"status": "ok" if os.path.isdir(upload) else "missing", "path": upload}

    all_ok = checks["database"].get("status") == "ok"
    overall = "ready" if all_ok else "degraded"
    status_code = 200 if all_ok else 503

    return jsonify({"status": overall, "checks": checks}), status_code


def _ms(start: float) -> float:
    return round((time.monotonic() - start) * 1000, 2)

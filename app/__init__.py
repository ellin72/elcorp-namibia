"""Elcorp Namibia — Digital Identity & Payments MVP."""

import os
import structlog
from flask import Flask
from flask_cors import CORS

from app.config import config_by_name
from app.extensions import db, migrate, limiter


def create_app(config_name: str | None = None) -> Flask:
    """Application factory."""
    if config_name is None:
        config_name = os.getenv("FLASK_ENV", "development")

    app = Flask(__name__)
    app.config.from_object(config_by_name[config_name])

    # ---------- extensions ----------
    db.init_app(app)
    migrate.init_app(app, db)
    limiter.init_app(app)
    CORS(app, origins=app.config["CORS_ORIGINS"].split(","))

    # ---------- structured logging ----------
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # ---------- blueprints ----------
    from app.api.v1 import api_v1_bp  # noqa: E402

    app.register_blueprint(api_v1_bp, url_prefix="/api/v1")

    # ---------- monitoring ----------
    if app.config.get("PROMETHEUS_ENABLED"):
        from prometheus_flask_instrumentator import PrometheusMetrics

        PrometheusMetrics(app)

    # ---------- error handlers ----------
    _register_error_handlers(app)

    # ---------- upload folder ----------
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    return app


def _register_error_handlers(app: Flask) -> None:
    from app.utils.errors import (
        APIError,
        handle_api_error,
        handle_404,
        handle_422,
        handle_500,
    )

    app.register_error_handler(APIError, handle_api_error)
    app.register_error_handler(404, handle_404)
    app.register_error_handler(422, handle_422)
    app.register_error_handler(500, handle_500)

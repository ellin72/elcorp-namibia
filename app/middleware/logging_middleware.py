"""Request/response logging middleware with correlation IDs."""

from __future__ import annotations

import time
import uuid

import structlog
from flask import Flask, g, request

logger = structlog.get_logger()


def init_request_logging(app: Flask) -> None:
    """Register before/after hooks for structured request logging."""

    @app.before_request
    def _set_correlation_id():
        g.correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
        g.request_start = time.monotonic()

    @app.after_request
    def _log_request(response):
        duration_ms = round((time.monotonic() - getattr(g, "request_start", time.monotonic())) * 1000, 2)
        correlation_id = getattr(g, "correlation_id", "")

        response.headers["X-Correlation-ID"] = correlation_id

        # Skip noisy health probes in logs
        if request.path in ("/api/v1/health", "/health"):
            return response

        logger.info(
            "http.request",
            method=request.method,
            path=request.path,
            status=response.status_code,
            duration_ms=duration_ms,
            correlation_id=correlation_id,
            remote_addr=request.remote_addr,
            user_id=getattr(g, "current_user_id", None),
        )
        return response

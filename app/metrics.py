"""Custom Prometheus metrics for Elcorp API.

Registered in the app factory when PROMETHEUS_ENABLED=true.
"""

from __future__ import annotations

import time

from flask import Flask, g, request
from prometheus_flask_exporter import PrometheusMetrics

from prometheus_client import Counter, Histogram

# ---- Custom counters and histograms ----

PAYMENT_CREATED = Counter(
    "elcorp_payments_created_total",
    "Total payments created",
    ["currency", "status"],
)

PAYMENT_PROCESSED = Counter(
    "elcorp_payments_processed_total",
    "Total payments processed (completed / failed)",
    ["outcome"],  # completed | failed
)

KYC_UPLOADS = Counter(
    "elcorp_kyc_uploads_total",
    "Total KYC document uploads",
    ["document_type"],
)

AUTH_EVENTS = Counter(
    "elcorp_auth_events_total",
    "Authentication events",
    ["event"],  # signup | login | refresh | failed_login
)

API_ERRORS = Counter(
    "elcorp_api_errors_total",
    "Application-level errors returned",
    ["status_code", "endpoint"],
)

REQUEST_LATENCY = Histogram(
    "elcorp_request_duration_seconds",
    "Request duration in seconds",
    ["method", "endpoint", "status"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


def init_metrics(app: Flask) -> PrometheusMetrics:
    """Bind PrometheusMetrics and register request-level hooks."""
    metrics = PrometheusMetrics(app)

    @app.before_request
    def _start_timer():
        g.metrics_start = time.monotonic()

    @app.after_request
    def _observe_latency(response):
        start = getattr(g, "metrics_start", None)
        if start is not None:
            elapsed = time.monotonic() - start
            endpoint = request.endpoint or "unknown"
            REQUEST_LATENCY.labels(
                method=request.method,
                endpoint=endpoint,
                status=response.status_code,
            ).observe(elapsed)

            if response.status_code >= 400:
                API_ERRORS.labels(
                    status_code=response.status_code,
                    endpoint=endpoint,
                ).inc()
        return response

    return metrics

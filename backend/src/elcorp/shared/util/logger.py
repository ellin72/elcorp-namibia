"""
Structured logging - JSON-formatted structured logging for production.
"""

import logging
import json
from datetime import datetime
from typing import Any, Dict


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include extra fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms

        # Include exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_data)


def setup_logging(app_name: str, level: str = "INFO"):
    """
    Setup structured logging for the application.
    """
    logger = logging.getLogger(app_name)
    logger.setLevel(getattr(logging, level))

    # Console handler with JSON formatting
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(JSONFormatter())
    logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.LoggerAdapter:
    """
    Get a logger with the given name.
    Returns a LoggerAdapter that allows adding contextual information.
    """
    logger = logging.getLogger(name)
    return logging.LoggerAdapter(logger, {})

"""Custom error types and Flask error handlers."""

from __future__ import annotations

from flask import jsonify


class APIError(Exception):
    """Base exception for API errors — caught by the error handler."""

    def __init__(self, message: str, status_code: int = 400, detail: str = ""):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.detail = detail


class NotFoundError(APIError):
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, status_code=404)


class UnauthorizedError(APIError):
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, status_code=401)


class ForbiddenError(APIError):
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message, status_code=403)


class ConflictError(APIError):
    def __init__(self, message: str = "Conflict"):
        super().__init__(message, status_code=409)


class ValidationError(APIError):
    def __init__(self, message: str = "Validation error", detail: str = ""):
        super().__init__(message, status_code=422, detail=detail)


# ---------- Flask error handlers ----------

def handle_api_error(error: APIError):
    payload = {"error": error.message}
    if error.detail:
        payload["detail"] = error.detail
    return jsonify(payload), error.status_code


def handle_404(error):
    return jsonify({"error": "Not found"}), 404


def handle_422(error):
    return jsonify({"error": "Unprocessable entity"}), 422


def handle_500(error):
    return jsonify({"error": "Internal server error"}), 500

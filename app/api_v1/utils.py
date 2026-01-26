"""
app/api_v1/utils.py - Utility functions for API v1
"""
from flask import jsonify
from typing import Any, Dict, Optional


def api_response(
    data: Any = None,
    message: str = "",
    code: int = 200,
    paginate: Optional[Dict[str, Any]] = None,
) -> tuple:
    """
    Standardized API success response.
    
    Args:
        data: Response data
        message: Optional message
        code: HTTP status code
        paginate: Optional pagination info
    
    Returns:
        Flask response tuple (response, status_code)
    """
    response = {
        "success": True,
        "data": data,
    }
    
    if message:
        response["message"] = message
    
    if paginate:
        response["pagination"] = paginate
    
    return jsonify(response), code


def api_error(
    message: str,
    code: int = 400,
    error_code: str = None,
    details: Dict[str, Any] = None,
) -> tuple:
    """
    Standardized API error response.
    
    Args:
        message: Error message
        code: HTTP status code
        error_code: Error code identifier
        details: Optional error details
    
    Returns:
        Flask response tuple (response, status_code)
    """
    error_code = error_code or _http_error_code(code)
    
    response = {
        "success": False,
        "error": {
            "code": error_code,
            "message": message,
        }
    }
    
    if details:
        response["error"]["details"] = details
    
    return jsonify(response), code


def _http_error_code(status_code: int) -> str:
    """Map HTTP status code to error code."""
    codes = {
        400: "BAD_REQUEST",
        401: "UNAUTHORIZED",
        403: "FORBIDDEN",
        404: "NOT_FOUND",
        409: "CONFLICT",
        422: "VALIDATION_ERROR",
        429: "RATE_LIMIT_EXCEEDED",
        500: "INTERNAL_ERROR",
    }
    return codes.get(status_code, "ERROR")


def get_pagination_params(
    default_per_page: int = 20,
    max_per_page: int = 100,
) -> tuple:
    """
    Extract pagination parameters from request args.
    
    Args:
        default_per_page: Default items per page
        max_per_page: Maximum items per page
    
    Returns:
        (page, per_page) tuple
    """
    from flask import request
    
    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", default_per_page))
        
        # Validate
        if page < 1:
            page = 1
        if per_page < 1:
            per_page = default_per_page
        if per_page > max_per_page:
            per_page = max_per_page
        
        return page, per_page
    except (ValueError, TypeError):
        return 1, default_per_page


def paginate_query(query, page: int, per_page: int) -> tuple:
    """
    Apply pagination to a SQLAlchemy query.
    
    Args:
        query: SQLAlchemy query object
        page: Page number
        per_page: Items per page
    
    Returns:
        (items, pagination_info) tuple
    """
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    pagination_info = {
        "page": page,
        "per_page": per_page,
        "total": paginated.total,
        "pages": paginated.pages,
    }
    
    return paginated.items, pagination_info

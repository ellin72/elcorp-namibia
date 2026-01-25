"""
app/api/utils.py - Utility functions for API responses and pagination
"""
from typing import Dict, Any, List, Tuple
from flask import request, jsonify
from werkzeug.exceptions import HTTPException


def api_response(
    data: Any = None,
    message: str = None,
    status_code: int = 200,
    paginate: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], int]:
    """
    Create a consistent JSON response format for API endpoints.
    
    Args:
        data: The response payload
        message: Optional message to include
        status_code: HTTP status code
        paginate: Optional pagination info dict with 'total', 'page', 'per_page', 'pages'
    
    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        "success": 200 <= status_code < 300,
        "data": data,
    }
    
    if message:
        response["message"] = message
    
    if paginate:
        response["pagination"] = paginate
    
    return jsonify(response), status_code


def api_error(
    message: str,
    status_code: int = 400,
    errors: Dict[str, Any] = None
) -> Tuple[Dict[str, Any], int]:
    """
    Create a consistent error response format for API endpoints.
    
    Args:
        message: Error message
        status_code: HTTP status code
        errors: Optional dict of field-specific errors (for validation)
    
    Returns:
        Tuple of (response_dict, status_code)
    """
    response = {
        "success": False,
        "message": message,
    }
    
    if errors:
        response["errors"] = errors
    
    return jsonify(response), status_code


def get_pagination_params(
    default_per_page: int = 20,
    max_per_page: int = 100
) -> Tuple[int, int]:
    """
    Extract and validate pagination parameters from request.
    
    Args:
        default_per_page: Default items per page
        max_per_page: Maximum allowed items per page
    
    Returns:
        Tuple of (page, per_page)
    """
    try:
        page = max(1, int(request.args.get('page', 1)))
        per_page = int(request.args.get('per_page', default_per_page))
        
        # Enforce maximum per_page
        per_page = min(per_page, max_per_page)
        per_page = max(1, per_page)  # Minimum 1
        
        return page, per_page
    except (ValueError, TypeError):
        return 1, default_per_page


def paginate_query(query, page: int, per_page: int) -> Tuple[List, Dict[str, int]]:
    """
    Paginate a SQLAlchemy query and return results with pagination info.
    
    Args:
        query: SQLAlchemy query object
        page: Page number (1-indexed)
        per_page: Items per page
    
    Returns:
        Tuple of (items, pagination_info)
    """
    paginated = query.paginate(page=page, per_page=per_page, error_out=False)
    
    pagination_info = {
        "total": paginated.total,
        "page": page,
        "per_page": per_page,
        "pages": paginated.pages,
    }
    
    return paginated.items, pagination_info


def validate_request_json(required_fields: List[str] = None) -> Tuple[Dict, int, str]:
    """
    Validate incoming JSON request.
    
    Args:
        required_fields: List of required field names
    
    Returns:
        Tuple of (json_data, status_code, error_message)
        On success: (data, 200, '')
        On failure: (None, 400, error_message)
    """
    if not request.is_json:
        return None, 400, "Content-Type must be application/json"
    
    data = request.get_json(silent=True)
    if data is None:
        return None, 400, "Invalid JSON payload"
    
    if required_fields:
        missing = [f for f in required_fields if f not in data]
        if missing:
            return None, 400, f"Missing required fields: {', '.join(missing)}"
    
    return data, 200, ""

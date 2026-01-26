"""
app/api_v1/service_requests_routes.py - Service request endpoints for API v1
"""
import logging
from flask import request
from .auth_routes import token_required
from . import bp
from .utils import api_response, api_error, get_pagination_params, paginate_query
from app.models import ServiceRequest, User
from app.extensions import db

logger = logging.getLogger("app.api_v1.service_requests")


@bp.route("/service-requests/mine", methods=["GET"])
@token_required
def get_user_service_requests():
    """Get service requests created by current user."""
    try:
        page, per_page = get_pagination_params()
        
        query = ServiceRequest.query.filter_by(created_by=request.user_id).order_by(
            ServiceRequest.created_at.desc()
        )
        
        requests_list, pagination_info = paginate_query(query, page, per_page)
        
        data = [
            {
                "id": sr.id,
                "title": sr.title,
                "description": sr.description,
                "category": sr.category,
                "status": sr.status,
                "priority": sr.priority,
                "assigned_to": sr.assigned_to,
                "created_at": sr.created_at.isoformat(),
                "updated_at": sr.updated_at.isoformat(),
            }
            for sr in requests_list
        ]
        
        return api_response(data=data, paginate=pagination_info)
    
    except Exception as e:
        logger.error(f"Error fetching service requests: {str(e)}")
        return api_error("An error occurred while fetching requests", 500)


@bp.route("/service-requests", methods=["POST"])
@token_required
def create_service_request():
    """Create a new service request."""
    try:
        data = request.get_json()
        if not data:
            return api_error("Request body is required", 400)
        
        # Validate required fields
        if not data.get("title") or not data.get("description"):
            return api_error("Title and description are required", 400)
        
        sr = ServiceRequest(
            title=data["title"],
            description=data["description"],
            category=data.get("category", "other"),
            priority=data.get("priority", "normal"),
            created_by=request.user_id,
        )
        
        db.session.add(sr)
        db.session.commit()
        
        logger.info(f"Service request created: {sr.id} by user {request.user_id}")
        
        return api_response(
            data={
                "id": sr.id,
                "title": sr.title,
                "status": sr.status,
                "created_at": sr.created_at.isoformat(),
            },
            message="Service request created successfully",
        )
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating service request: {str(e)}")
        return api_error("An error occurred while creating request", 500)


@bp.route("/service-requests/<request_id>", methods=["GET"])
@token_required
def get_service_request(request_id):
    """Get a specific service request."""
    sr = ServiceRequest.query.get(request_id)
    if not sr:
        return api_error("Service request not found", 404)
    
    # Check authorization
    if sr.created_by != request.user_id and request.user_role != "admin" and request.user_role != "staff":
        return api_error("You don't have permission to view this request", 403)
    
    return api_response(
        data={
            "id": sr.id,
            "title": sr.title,
            "description": sr.description,
            "category": sr.category,
            "status": sr.status,
            "priority": sr.priority,
            "assigned_to": sr.assigned_to,
            "created_by": sr.created_by,
            "created_at": sr.created_at.isoformat(),
            "updated_at": sr.updated_at.isoformat(),
        }
    )

"""
app/api/routes.py - REST API endpoints for users, profiles, and management
"""
import logging
from datetime import datetime
from flask import request, current_app
from flask_login import login_required, current_user
from sqlalchemy import or_

from app.extensions import db
from app.models import User, UserProfile, Role
from app.security import require_role, require_admin, can_access_user, is_admin
from . import bp
from .utils import (
    api_response, api_error, get_pagination_params, paginate_query, 
    validate_request_json
)

logger = logging.getLogger("app.api")


# ============================================================================
# Health Check
# ============================================================================
@bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return api_response(
        data={"status": "healthy", "timestamp": datetime.utcnow().isoformat()},
        message="API is operational"
    )


# ============================================================================
# User Endpoints
# ============================================================================
@bp.route("/users", methods=["GET"])
@login_required
@require_admin
def list_users():
    """
    List all users with pagination and filtering.
    Requires admin role.
    
    Query parameters:
        - page: Page number (default 1)
        - per_page: Items per page (default 20, max 100)
        - search: Search by username, email, or full_name
        - role: Filter by role name
        - active: Filter by is_active status (true/false)
    """
    try:
        page, per_page = get_pagination_params(
            default_per_page=current_app.config.get("API_ITEMS_PER_PAGE", 20)
        )
        
        query = User.query
        
        # Search filter
        search_term = request.args.get('search', '').strip()
        if search_term:
            query = query.filter(
                or_(
                    User.username.ilike(f"%{search_term}%"),
                    User.email.ilike(f"%{search_term}%"),
                    User.full_name.ilike(f"%{search_term}%"),
                )
            )
        
        # Role filter
        role_name = request.args.get('role', '').strip()
        if role_name:
            query = query.join(Role).filter(Role.name == role_name)
        
        # Active filter
        active_param = request.args.get('active', '').lower()
        if active_param in ('true', 'false'):
            query = query.filter(User.is_active == (active_param == 'true'))
        
        users, pagination_info = paginate_query(query, page, per_page)
        
        user_data = [
            {
                "id": u.id,
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "role": u.role.name if u.role else None,
                "is_active": u.is_active,
                "is_admin": u.is_admin,
                "last_login": u.last_login.isoformat() if u.last_login else None,
                "created_at": u.created_at.isoformat(),
            }
            for u in users
        ]
        
        return api_response(data=user_data, paginate=pagination_info)
    
    except Exception as e:
        logger.error(f"Error listing users: {str(e)}")
        return api_error("Failed to list users", 500)


@bp.route("/users/<int:user_id>", methods=["GET"])
@login_required
def get_user(user_id):
    """
    Get a specific user's details.
    Users can view their own profile. Admins can view any user.
    """
    try:
        if not can_access_user(user_id):
            return api_error("Access denied", 403)
        
        user = User.query.get(user_id)
        if not user:
            return api_error("User not found", 404)
        
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "organization": user.organization,
            "role": user.role.name if user.role else None,
            "is_active": user.is_active,
            "is_admin": user.is_admin,
            "wallet_address": user.wallet_address,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat(),
        }
        
        return api_response(data=user_data)
    
    except Exception as e:
        logger.error(f"Error getting user {user_id}: {str(e)}")
        return api_error("Failed to retrieve user", 500)


@bp.route("/users", methods=["POST"])
@login_required
@require_admin
def create_user():
    """
    Create a new user. Requires admin role.
    
    Request JSON:
        {
            "username": "string",
            "email": "string",
            "full_name": "string",
            "phone": "string",
            "password": "string",
            "organization": "string" (optional),
            "role": "string" (user, staff, admin - defaults to user),
        }
    """
    try:
        data, status_code, error_msg = validate_request_json(
            required_fields=["username", "email", "full_name", "phone", "password"]
        )
        if error_msg:
            return api_error(error_msg, status_code)
        
        # Validate unique fields
        if User.query.filter_by(username=data["username"].lower()).first():
            return api_error("Username already exists", 400)
        
        if User.query.filter_by(email=data["email"].lower()).first():
            return api_error("Email already exists", 400)
        
        if User.query.filter_by(phone=data["phone"]).first():
            return api_error("Phone number already registered", 400)
        
        # Get role
        role_name = data.get("role", "user").lower()
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            return api_error(f"Role '{role_name}' does not exist", 400)
        
        # Create user
        user = User(
            username=data["username"].lower(),
            email=data["email"].lower(),
            full_name=data["full_name"],
            phone=data["phone"],
            organization=data.get("organization"),
            role=role,
        )
        user.set_password(data["password"])
        
        db.session.add(user)
        db.session.flush()
        
        # Create user profile
        profile = UserProfile(user_id=user.id)
        db.session.add(profile)
        
        db.session.commit()
        
        logger.info(f"User created: {user.username} with role {role.name}")
        
        return api_response(
            data={"id": user.id, "username": user.username, "email": user.email},
            message="User created successfully",
            status_code=201
        )
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating user: {str(e)}")
        return api_error("Failed to create user", 500)


@bp.route("/users/<int:user_id>", methods=["PUT"])
@login_required
def update_user(user_id):
    """
    Update user information.
    Users can update their own profile. Admins can update any user.
    
    Request JSON (all fields optional):
        {
            "full_name": "string",
            "phone": "string",
            "organization": "string",
            "role": "string" (admin only),
            "is_active": "boolean" (admin only),
        }
    """
    try:
        if not can_access_user(user_id):
            return api_error("Access denied", 403)
        
        user = User.query.get(user_id)
        if not user:
            return api_error("User not found", 404)
        
        data, status_code, error_msg = validate_request_json()
        if error_msg and status_code != 200:
            return api_error(error_msg, status_code)
        
        # Non-admin users can only update their own full_name, phone, organization
        if not is_admin():
            allowed_fields = {"full_name", "phone", "organization"}
            data = {k: v for k, v in data.items() if k in allowed_fields}
        
        # Update basic fields
        if "full_name" in data:
            user.full_name = data["full_name"]
        if "phone" in data:
            if User.query.filter_by(phone=data["phone"]).filter(User.id != user_id).first():
                return api_error("Phone number already in use", 400)
            user.phone = data["phone"]
        if "organization" in data:
            user.organization = data["organization"]
        
        # Admin-only updates
        if is_admin():
            if "role" in data:
                role = Role.query.filter_by(name=data["role"]).first()
                if not role:
                    return api_error(f"Role '{data['role']}' does not exist", 400)
                user.role = role
            
            if "is_active" in data:
                user.is_active = bool(data["is_active"])
        
        db.session.commit()
        
        logger.info(f"User updated: {user.username}")
        
        return api_response(
            data={"id": user.id, "username": user.username},
            message="User updated successfully"
        )
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user {user_id}: {str(e)}")
        return api_error("Failed to update user", 500)


@bp.route("/users/<int:user_id>", methods=["DELETE"])
@login_required
@require_admin
def delete_user(user_id):
    """
    Delete a user. Requires admin role.
    Note: This soft-deletes the user by marking is_active as False.
    """
    try:
        if user_id == current_user.id:
            return api_error("Cannot delete your own account", 400)
        
        user = User.query.get(user_id)
        if not user:
            return api_error("User not found", 404)
        
        user.is_active = False
        db.session.commit()
        
        logger.info(f"User deactivated: {user.username}")
        
        return api_response(message="User deleted successfully")
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user {user_id}: {str(e)}")
        return api_error("Failed to delete user", 500)


@bp.route("/users/<int:user_id>/role", methods=["PUT"])
@login_required
@require_admin
def update_user_role(user_id):
    """
    Update a user's role. Requires admin role.
    
    Request JSON:
        {
            "role": "string" (user, staff, admin)
        }
    """
    try:
        user = User.query.get(user_id)
        if not user:
            return api_error("User not found", 404)
        
        data, status_code, error_msg = validate_request_json(required_fields=["role"])
        if error_msg:
            return api_error(error_msg, status_code)
        
        role = Role.query.filter_by(name=data["role"]).first()
        if not role:
            return api_error(f"Role '{data['role']}' does not exist", 400)
        
        old_role = user.role.name if user.role else None
        user.role = role
        db.session.commit()
        
        logger.info(f"User role updated: {user.username} from {old_role} to {role.name}")
        
        return api_response(message=f"User role updated to {role.name}")
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating role for user {user_id}: {str(e)}")
        return api_error("Failed to update user role", 500)


# ============================================================================
# User Profile Endpoints
# ============================================================================
@bp.route("/profiles/<int:user_id>", methods=["GET"])
@login_required
def get_profile(user_id):
    """
    Get a user's profile information.
    Users can view their own profile. Admins can view any user's.
    """
    try:
        if not can_access_user(user_id):
            return api_error("Access denied", 403)
        
        user = User.query.get(user_id)
        if not user:
            return api_error("User not found", 404)
        
        # Get or create profile
        profile = user.profile or UserProfile(user_id=user_id)
        
        profile_data = {
            "user_id": profile.user_id,
            "bio": profile.bio,
            "profile_picture_url": profile.profile_picture_url,
            "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
            "country": profile.country,
            "city": profile.city,
            "phone_verified": profile.phone_verified,
            "email_verified": profile.email_verified,
            "created_at": profile.created_at.isoformat(),
            "last_updated": profile.last_updated.isoformat(),
        }
        
        return api_response(data=profile_data)
    
    except Exception as e:
        logger.error(f"Error getting profile for user {user_id}: {str(e)}")
        return api_error("Failed to retrieve profile", 500)


@bp.route("/profiles/<int:user_id>", methods=["PUT"])
@login_required
def update_profile(user_id):
    """
    Update a user's profile information.
    Users can update their own profile. Admins can update any user's.
    
    Request JSON (all fields optional):
        {
            "bio": "string",
            "profile_picture_url": "string",
            "date_of_birth": "YYYY-MM-DD",
            "country": "string",
            "city": "string",
        }
    """
    try:
        if not can_access_user(user_id):
            return api_error("Access denied", 403)
        
        user = User.query.get(user_id)
        if not user:
            return api_error("User not found", 404)
        
        data, status_code, error_msg = validate_request_json()
        if error_msg and status_code != 200:
            return api_error(error_msg, status_code)
        
        # Get or create profile
        profile = user.profile
        if not profile:
            profile = UserProfile(user_id=user_id)
            db.session.add(profile)
        
        # Update fields
        if "bio" in data:
            profile.bio = data["bio"][:500] if data["bio"] else None
        if "profile_picture_url" in data:
            profile.profile_picture_url = data["profile_picture_url"]
        if "date_of_birth" in data:
            if data["date_of_birth"]:
                profile.date_of_birth = datetime.fromisoformat(data["date_of_birth"]).date()
            else:
                profile.date_of_birth = None
        if "country" in data:
            profile.country = data["country"]
        if "city" in data:
            profile.city = data["city"]
        
        profile.last_updated = datetime.utcnow()
        db.session.commit()
        
        logger.info(f"Profile updated for user {user_id}")
        
        return api_response(message="Profile updated successfully")
    
    except ValueError as e:
        logger.warning(f"Invalid date format: {str(e)}")
        return api_error("Invalid date format. Use YYYY-MM-DD", 400)
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile for user {user_id}: {str(e)}")
        return api_error("Failed to update profile", 500)


# ============================================================================
# Role Endpoints
# ============================================================================
@bp.route("/roles", methods=["GET"])
@login_required
def list_roles():
    """
    List all available roles.
    """
    try:
        roles = Role.query.all()
        role_data = [
            {
                "id": r.id,
                "name": r.name,
                "description": r.description,
                "user_count": r.users.count(),
            }
            for r in roles
        ]
        
        return api_response(data=role_data)
    
    except Exception as e:
        logger.error(f"Error listing roles: {str(e)}")
        return api_error("Failed to list roles", 500)


# ============================================================================
# Current User Endpoint
# ============================================================================
@bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    """
    Get current authenticated user's information.
    """
    try:
        user = current_user
        
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "organization": user.organization,
            "role": user.role.name if user.role else None,
            "is_admin": user.is_admin,
            "is_active": user.is_active,
            "wallet_address": user.wallet_address,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat(),
        }
        
        return api_response(data=user_data)
    
    except Exception as e:
        logger.error(f"Error getting current user: {str(e)}")
        return api_error("Failed to retrieve current user info", 500)


@bp.route("/me/profile", methods=["GET"])
@login_required
def get_current_user_profile():
    """
    Get current user's profile information.
    """
    return get_profile(current_user.id)


@bp.route("/me/profile", methods=["PUT"])
@login_required
def update_current_user_profile():
    """
    Update current user's profile information.
    """
    return update_profile(current_user.id)


# ============================================================================
# Service Request Endpoints
# ============================================================================

@bp.route("/service-requests", methods=["POST"])
@login_required
def create_service_request():
    """
    Create a new service request (User).
    Only authenticated users can create service requests.
    
    Request body:
        - title: str (required)
        - description: str (required)
        - category: str (required) - compliance, support, inquiry, complaint, other
        - priority: str (optional) - low, normal, high, urgent (default: normal)
    """
    try:
        from app.models import ServiceRequest
        
        if not validate_request_json(request):
            return api_error("Invalid request format", 400)
        
        data = request.get_json()
        
        # Validate required fields
        if not data.get('title') or not data.get('description') or not data.get('category'):
            return api_error("Missing required fields: title, description, category", 400)
        
        # Validate category
        if data['category'] not in ServiceRequest.VALID_CATEGORIES:
            return api_error(f"Invalid category. Must be one of: {', '.join(ServiceRequest.VALID_CATEGORIES)}", 400)
        
        # Validate priority if provided
        priority = data.get('priority', ServiceRequest.PRIORITY_NORMAL)
        if priority not in ServiceRequest.VALID_PRIORITIES:
            return api_error(f"Invalid priority. Must be one of: {', '.join(ServiceRequest.VALID_PRIORITIES)}", 400)
        
        # Create new service request
        service_request = ServiceRequest(
            title=data['title'],
            description=data['description'],
            category=data['category'],
            priority=priority,
            created_by=current_user.id,
            status=ServiceRequest.STATUS_DRAFT
        )
        
        db.session.add(service_request)
        db.session.commit()
        
        logger.info(f"Service request {service_request.id} created by user {current_user.id}")
        
        return api_response(
            data={
                "id": service_request.id,
                "title": service_request.title,
                "description": service_request.description,
                "category": service_request.category,
                "priority": service_request.priority,
                "status": service_request.status,
                "created_by": service_request.created_by,
                "assigned_to": service_request.assigned_to,
                "created_at": service_request.created_at.isoformat(),
                "updated_at": service_request.updated_at.isoformat(),
            },
            message="Service request created successfully",
            status_code=201
        )
    
    except Exception as e:
        logger.error(f"Error creating service request: {str(e)}")
        return api_error("Failed to create service request", 500)


@bp.route("/service-requests/mine", methods=["GET"])
@login_required
def get_user_service_requests():
    """
    Get all service requests created by the current user (User).
    
    Query parameters:
        - page: Page number (default 1)
        - per_page: Items per page (default 20, max 100)
        - status: Filter by status
        - priority: Filter by priority
    """
    try:
        from app.models import ServiceRequest
        
        page, per_page = get_pagination_params(
            default_per_page=current_app.config.get("API_ITEMS_PER_PAGE", 20)
        )
        
        query = ServiceRequest.query.filter_by(created_by=current_user.id)
        
        # Status filter
        status_param = request.args.get('status', '').strip()
        if status_param and status_param in ServiceRequest.VALID_STATUSES:
            query = query.filter_by(status=status_param)
        
        # Priority filter
        priority_param = request.args.get('priority', '').strip()
        if priority_param and priority_param in ServiceRequest.VALID_PRIORITIES:
            query = query.filter_by(priority=priority_param)
        
        # Order by created_at descending
        query = query.order_by(ServiceRequest.created_at.desc())
        
        requests, pagination_info = paginate_query(query, page, per_page)
        
        requests_data = [
            {
                "id": sr.id,
                "title": sr.title,
                "description": sr.description,
                "category": sr.category,
                "priority": sr.priority,
                "status": sr.status,
                "assigned_to": sr.assigned_to,
                "created_at": sr.created_at.isoformat(),
                "updated_at": sr.updated_at.isoformat(),
            }
            for sr in requests
        ]
        
        return api_response(data=requests_data, paginate=pagination_info)
    
    except Exception as e:
        logger.error(f"Error retrieving user service requests: {str(e)}")
        return api_error("Failed to retrieve service requests", 500)


@bp.route("/service-requests/<request_id>", methods=["GET"])
@login_required
def get_service_request(request_id):
    """
    Get a specific service request (User/Staff/Admin).
    User can only access their own requests unless they are staff/admin.
    """
    try:
        from app.models import ServiceRequest
        
        service_request = ServiceRequest.query.get(request_id)
        
        if not service_request:
            return api_error("Service request not found", 404)
        
        # Check access permissions
        is_admin = current_user.role and current_user.role.name == "admin"
        is_staff = current_user.role and current_user.role.name == "staff"
        is_creator = service_request.created_by == current_user.id
        is_assignee = service_request.assigned_to == current_user.id
        
        if not (is_creator or is_assignee or is_staff or is_admin):
            logger.warning(f"Access denied for user {current_user.id} to service request {request_id}")
            return api_error("You do not have permission to access this request", 403)
        
        return api_response(data={
            "id": service_request.id,
            "title": service_request.title,
            "description": service_request.description,
            "category": service_request.category,
            "priority": service_request.priority,
            "status": service_request.status,
            "created_by": service_request.created_by,
            "creator_name": service_request.creator.full_name if service_request.creator else None,
            "assigned_to": service_request.assigned_to,
            "assignee_name": service_request.assignee.full_name if service_request.assignee else None,
            "created_at": service_request.created_at.isoformat(),
            "updated_at": service_request.updated_at.isoformat(),
        })
    
    except Exception as e:
        logger.error(f"Error retrieving service request: {str(e)}")
        return api_error("Failed to retrieve service request", 500)


@bp.route("/service-requests/<request_id>", methods=["PUT"])
@login_required
def update_service_request(request_id):
    """
    Update a service request (User can only edit draft requests).
    
    Request body:
        - title: str (optional)
        - description: str (optional)
        - category: str (optional)
        - priority: str (optional)
    """
    try:
        from app.models import ServiceRequest
        
        service_request = ServiceRequest.query.get(request_id)
        
        if not service_request:
            return api_error("Service request not found", 404)
        
        # Only creator can edit draft requests
        if service_request.created_by != current_user.id:
            logger.warning(f"Access denied for user {current_user.id} to edit request {request_id}")
            return api_error("You do not have permission to edit this request", 403)
        
        if not service_request.can_edit(current_user):
            return api_error("Can only edit draft service requests", 400)
        
        if not validate_request_json(request):
            return api_error("Invalid request format", 400)
        
        data = request.get_json()
        
        # Update fields
        if 'title' in data:
            service_request.title = data['title']
        if 'description' in data:
            service_request.description = data['description']
        if 'category' in data:
            if data['category'] not in ServiceRequest.VALID_CATEGORIES:
                return api_error(f"Invalid category. Must be one of: {', '.join(ServiceRequest.VALID_CATEGORIES)}", 400)
            service_request.category = data['category']
        if 'priority' in data:
            if data['priority'] not in ServiceRequest.VALID_PRIORITIES:
                return api_error(f"Invalid priority. Must be one of: {', '.join(ServiceRequest.VALID_PRIORITIES)}", 400)
            service_request.priority = data['priority']
        
        db.session.commit()
        logger.info(f"Service request {request_id} updated by user {current_user.id}")
        
        return api_response(data={
            "id": service_request.id,
            "title": service_request.title,
            "description": service_request.description,
            "category": service_request.category,
            "priority": service_request.priority,
            "status": service_request.status,
            "created_at": service_request.created_at.isoformat(),
            "updated_at": service_request.updated_at.isoformat(),
        }, message="Service request updated successfully")
    
    except Exception as e:
        logger.error(f"Error updating service request: {str(e)}")
        return api_error("Failed to update service request", 500)


@bp.route("/service-requests/<request_id>/submit", methods=["POST"])
@login_required
def submit_service_request(request_id):
    """
    Submit a draft service request (User).
    Only creator can submit their draft requests.
    Triggers email notification.
    """
    try:
        from app.models import ServiceRequest, ServiceRequestHistory
        from app.audit import log_action
        from app.email_service import send_service_request_submitted_email
        
        service_request = ServiceRequest.query.get(request_id)
        
        if not service_request:
            return api_error("Service request not found", 404)
        
        # Only creator can submit
        if service_request.created_by != current_user.id:
            logger.warning(f"Access denied for user {current_user.id} to submit request {request_id}")
            return api_error("You do not have permission to submit this request", 403)
        
        if not service_request.can_submit(current_user):
            return api_error("Can only submit draft service requests", 400)
        
        # Record history
        old_status = service_request.status
        service_request.status = ServiceRequest.STATUS_SUBMITTED
        
        history = ServiceRequestHistory(
            service_request_id=service_request.id,
            action="submitted",
            old_status=old_status,
            new_status=service_request.status,
            changed_by=current_user.id,
            details={"submitted_at": datetime.utcnow().isoformat()}
        )
        
        db.session.add(history)
        db.session.commit()
        
        # Log action
        log_action(
            "service_request_submitted",
            {
                "service_request_id": service_request.id,
                "user_id": current_user.id
            }
        )
        
        logger.info(f"Service request {request_id} submitted by user {current_user.id}")
        
        # Send notification email
        try:
            send_service_request_submitted_email(service_request)
        except Exception as e:
            logger.error(f"Failed to send submission email: {str(e)}")
        
        return api_response(data={
            "id": service_request.id,
            "status": service_request.status,
            "updated_at": service_request.updated_at.isoformat(),
        }, message="Service request submitted successfully")
    
    except Exception as e:
        logger.error(f"Error submitting service request: {str(e)}")
        return api_error("Failed to submit service request", 500)


@bp.route("/service-requests/assigned", methods=["GET"])
@login_required
@require_role('staff', 'admin')
def get_assigned_service_requests():
    """
    Get service requests assigned to the current staff member (Staff/Admin).
    
    Query parameters:
        - page: Page number (default 1)
        - per_page: Items per page (default 20, max 100)
        - status: Filter by status
    """
    try:
        from app.models import ServiceRequest
        
        page, per_page = get_pagination_params(
            default_per_page=current_app.config.get("API_ITEMS_PER_PAGE", 20)
        )
        
        query = ServiceRequest.query.filter_by(assigned_to=current_user.id)
        
        # Status filter
        status_param = request.args.get('status', '').strip()
        if status_param and status_param in ServiceRequest.VALID_STATUSES:
            query = query.filter_by(status=status_param)
        
        # Order by created_at descending
        query = query.order_by(ServiceRequest.created_at.desc())
        
        requests, pagination_info = paginate_query(query, page, per_page)
        
        requests_data = [
            {
                "id": sr.id,
                "title": sr.title,
                "description": sr.description,
                "category": sr.category,
                "priority": sr.priority,
                "status": sr.status,
                "created_by": sr.created_by,
                "creator_name": sr.creator.full_name if sr.creator else None,
                "created_at": sr.created_at.isoformat(),
                "updated_at": sr.updated_at.isoformat(),
            }
            for sr in requests
        ]
        
        return api_response(data=requests_data, paginate=pagination_info)
    
    except Exception as e:
        logger.error(f"Error retrieving assigned service requests: {str(e)}")
        return api_error("Failed to retrieve assigned requests", 500)


@bp.route("/service-requests/<request_id>/status", methods=["PATCH"])
@login_required
@require_role('staff', 'admin')
def update_service_request_status(request_id):
    """
    Update service request status (Staff/Admin).
    - Staff can move to in_review
    - Admin can approve/reject/complete
    
    Request body:
        - status: str (required) - in_review, approved, rejected, completed
        - notes: str (optional) - additional notes
    """
    try:
        from app.models import ServiceRequest, ServiceRequestHistory
        from app.audit import log_action
        from app.email_service import send_service_request_status_email
        
        service_request = ServiceRequest.query.get(request_id)
        
        if not service_request:
            return api_error("Service request not found", 404)
        
        if not validate_request_json(request):
            return api_error("Invalid request format", 400)
        
        data = request.get_json()
        new_status = data.get('status', '').strip()
        notes = data.get('notes', '').strip()
        
        if not new_status or new_status not in ServiceRequest.VALID_STATUSES:
            return api_error(f"Invalid status. Must be one of: {', '.join(ServiceRequest.VALID_STATUSES)}", 400)
        
        # Check permissions based on role
        is_admin = current_user.role and current_user.role.name == "admin"
        is_staff = current_user.role and current_user.role.name == "staff"
        
        if new_status == ServiceRequest.STATUS_IN_REVIEW:
            if not is_staff:
                return api_error("Only staff can move requests to in_review", 403)
            if service_request.status != ServiceRequest.STATUS_SUBMITTED:
                return api_error("Request must be in submitted status to move to in_review", 400)
        
        elif new_status in [ServiceRequest.STATUS_APPROVED, ServiceRequest.STATUS_REJECTED]:
            if not is_admin:
                return api_error("Only admin can approve or reject requests", 403)
            if service_request.status != ServiceRequest.STATUS_IN_REVIEW:
                return api_error("Request must be in in_review status to approve or reject", 400)
        
        elif new_status == ServiceRequest.STATUS_COMPLETED:
            if not is_admin:
                return api_error("Only admin can mark requests as completed", 403)
            if service_request.status not in [ServiceRequest.STATUS_APPROVED, ServiceRequest.STATUS_COMPLETED]:
                return api_error("Request must be approved before completing", 400)
        
        # Update status
        old_status = service_request.status
        service_request.status = new_status
        
        # Record history
        history = ServiceRequestHistory(
            service_request_id=service_request.id,
            action="status_changed",
            old_status=old_status,
            new_status=new_status,
            changed_by=current_user.id,
            details={
                "changed_at": datetime.utcnow().isoformat(),
                "notes": notes if notes else None
            }
        )
        
        db.session.add(history)
        db.session.commit()
        
        # Log action
        log_action(
            "service_request_status_changed",
            {
                "service_request_id": service_request.id,
                "old_status": old_status,
                "new_status": new_status,
                "changed_by": current_user.id
            }
        )
        
        logger.info(f"Service request {request_id} status changed from {old_status} to {new_status} by user {current_user.id}")
        
        # Send notification emails
        try:
            send_service_request_status_email(service_request, old_status, new_status, notes)
        except Exception as e:
            logger.error(f"Failed to send status email: {str(e)}")
        
        return api_response(data={
            "id": service_request.id,
            "status": service_request.status,
            "updated_at": service_request.updated_at.isoformat(),
        }, message="Service request status updated successfully")
    
    except Exception as e:
        logger.error(f"Error updating service request status: {str(e)}")
        return api_error("Failed to update service request status", 500)


@bp.route("/service-requests", methods=["GET"])
@login_required
@require_admin
def get_all_service_requests():
    """
    Get all service requests (Admin only).
    
    Query parameters:
        - page: Page number (default 1)
        - per_page: Items per page (default 20, max 100)
        - status: Filter by status
        - priority: Filter by priority
        - category: Filter by category
    """
    try:
        from app.models import ServiceRequest
        
        page, per_page = get_pagination_params(
            default_per_page=current_app.config.get("API_ITEMS_PER_PAGE", 20)
        )
        
        query = ServiceRequest.query
        
        # Status filter
        status_param = request.args.get('status', '').strip()
        if status_param and status_param in ServiceRequest.VALID_STATUSES:
            query = query.filter_by(status=status_param)
        
        # Priority filter
        priority_param = request.args.get('priority', '').strip()
        if priority_param and priority_param in ServiceRequest.VALID_PRIORITIES:
            query = query.filter_by(priority=priority_param)
        
        # Category filter
        category_param = request.args.get('category', '').strip()
        if category_param and category_param in ServiceRequest.VALID_CATEGORIES:
            query = query.filter_by(category=category_param)
        
        # Order by created_at descending
        query = query.order_by(ServiceRequest.created_at.desc())
        
        requests, pagination_info = paginate_query(query, page, per_page)
        
        requests_data = [
            {
                "id": sr.id,
                "title": sr.title,
                "description": sr.description,
                "category": sr.category,
                "priority": sr.priority,
                "status": sr.status,
                "created_by": sr.created_by,
                "creator_name": sr.creator.full_name if sr.creator else None,
                "assigned_to": sr.assigned_to,
                "assignee_name": sr.assignee.full_name if sr.assignee else None,
                "created_at": sr.created_at.isoformat(),
                "updated_at": sr.updated_at.isoformat(),
            }
            for sr in requests
        ]
        
        return api_response(data=requests_data, paginate=pagination_info)
    
    except Exception as e:
        logger.error(f"Error retrieving all service requests: {str(e)}")
        return api_error("Failed to retrieve service requests", 500)


@bp.route("/service-requests/<request_id>/assign", methods=["POST"])
@login_required
@require_admin
def assign_service_request(request_id):
    """
    Assign a service request to a staff member (Admin only).
    
    Request body:
        - assigned_to: int (required) - user_id of staff member
    """
    try:
        from app.models import ServiceRequest, ServiceRequestHistory
        from app.audit import log_action
        from app.email_service import send_service_request_assigned_email
        
        service_request = ServiceRequest.query.get(request_id)
        
        if not service_request:
            return api_error("Service request not found", 404)
        
        if not validate_request_json(request):
            return api_error("Invalid request format", 400)
        
        data = request.get_json()
        assigned_to_id = data.get('assigned_to')
        
        if not assigned_to_id:
            return api_error("Missing required field: assigned_to", 400)
        
        # Get the staff member
        staff_member = User.query.get(assigned_to_id)
        
        if not staff_member:
            return api_error("Staff member not found", 404)
        
        if not staff_member.role or staff_member.role.name != "staff":
            return api_error("Target user must have staff role", 400)
        
        # Assign
        old_assigned_to = service_request.assigned_to
        service_request.assigned_to = assigned_to_id
        
        # Record history
        history = ServiceRequestHistory(
            service_request_id=service_request.id,
            action="assigned",
            old_status=service_request.status,
            new_status=service_request.status,
            changed_by=current_user.id,
            details={
                "assigned_to": assigned_to_id,
                "assigned_from": old_assigned_to,
                "assigned_at": datetime.utcnow().isoformat()
            }
        )
        
        db.session.add(history)
        db.session.commit()
        
        # Log action
        log_action(
            "service_request_assigned",
            {
                "service_request_id": service_request.id,
                "assigned_to": assigned_to_id,
                "assigned_by": current_user.id
            }
        )
        
        logger.info(f"Service request {request_id} assigned to user {assigned_to_id} by admin {current_user.id}")
        
        # Send notification email
        try:
            send_service_request_assigned_email(service_request, staff_member)
        except Exception as e:
            logger.error(f"Failed to send assignment email: {str(e)}")
        
        return api_response(data={
            "id": service_request.id,
            "assigned_to": service_request.assigned_to,
            "assignee_name": staff_member.full_name,
            "updated_at": service_request.updated_at.isoformat(),
        }, message="Service request assigned successfully")
    
    except Exception as e:
        logger.error(f"Error assigning service request: {str(e)}")
        return api_error("Failed to assign service request", 500)


@bp.route("/service-requests/<request_id>", methods=["DELETE"])
@login_required
@require_admin
def delete_service_request(request_id):
    """
    Delete a service request (Admin only).
    """
    try:
        from app.models import ServiceRequest, ServiceRequestHistory
        from app.audit import log_action
        
        service_request = ServiceRequest.query.get(request_id)
        
        if not service_request:
            return api_error("Service request not found", 404)
        
        # Log action before deletion
        log_action(
            "service_request_deleted",
            {
                "service_request_id": service_request.id,
                "deleted_by": current_user.id,
                "title": service_request.title,
                "status": service_request.status
            }
        )
        
        logger.info(f"Service request {request_id} deleted by admin {current_user.id}")
        
        # Delete history first (foreign key constraint)
        ServiceRequestHistory.query.filter_by(service_request_id=request_id).delete()
        
        # Delete service request
        db.session.delete(service_request)
        db.session.commit()
        
        return api_response(message="Service request deleted successfully")
    
    except Exception as e:
        logger.error(f"Error deleting service request: {str(e)}")
        return api_error("Failed to delete service request", 500)

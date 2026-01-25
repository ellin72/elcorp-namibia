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

"""
app/api_v1/users_routes.py - User management endpoints for API v1
"""
import logging
from flask import request
from .auth_routes import token_required
from . import bp
from .utils import api_response, api_error, get_pagination_params, paginate_query
from app.models import User, UserProfile
from app.extensions import db

logger = logging.getLogger("app.api_v1.users")


@bp.route("/me", methods=["GET"])
@token_required
def get_current_user():
    """Get current authenticated user's information."""
    user = User.query.get(request.user_id)
    if not user:
        return api_error("User not found", 404)
    
    return api_response(
        data={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "phone": user.phone,
            "organization": user.organization,
            "role": user.role.name if user.role else "user",
            "is_admin": user.is_admin,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat(),
        }
    )


@bp.route("/me/profile", methods=["GET"])
@token_required
def get_current_user_profile():
    """Get current user's profile."""
    user = User.query.get(request.user_id)
    if not user:
        return api_error("User not found", 404)
    
    profile = UserProfile.query.filter_by(user_id=request.user_id).first()
    if not profile:
        profile = UserProfile(user_id=request.user_id)
        db.session.add(profile)
        db.session.commit()
    
    return api_response(
        data={
            "user_id": profile.user_id,
            "bio": profile.bio,
            "profile_picture_url": profile.profile_picture_url,
            "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
            "country": profile.country,
            "city": profile.city,
            "phone_verified": profile.phone_verified,
            "email_verified": profile.email_verified,
            "created_at": profile.created_at.isoformat(),
            "updated_at": profile.last_updated.isoformat(),
        }
    )


@bp.route("/me/profile", methods=["PUT"])
@token_required
def update_current_user_profile():
    """Update current user's profile."""
    try:
        data = request.get_json()
        if not data:
            return api_error("Request body is required", 400)
        
        profile = UserProfile.query.filter_by(user_id=request.user_id).first()
        if not profile:
            profile = UserProfile(user_id=request.user_id)
            db.session.add(profile)
        
        # Update allowed fields
        if "bio" in data:
            profile.bio = data["bio"]
        if "date_of_birth" in data:
            profile.date_of_birth = data["date_of_birth"]
        if "country" in data:
            profile.country = data["country"]
        if "city" in data:
            profile.city = data["city"]
        
        db.session.commit()
        logger.info(f"Profile updated for user {request.user_id}")
        
        return api_response(
            data={
                "user_id": profile.user_id,
                "bio": profile.bio,
                "date_of_birth": profile.date_of_birth.isoformat() if profile.date_of_birth else None,
                "country": profile.country,
                "city": profile.city,
                "updated_at": profile.last_updated.isoformat(),
            },
            message="Profile updated successfully",
        )
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating profile: {str(e)}")
        return api_error("An error occurred while updating profile", 500)

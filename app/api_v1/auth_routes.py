"""
app/api_v1/auth_routes.py - JWT Authentication endpoints for API v1
"""
import logging
from datetime import datetime, timedelta
from functools import wraps

from flask import request, current_app, jsonify
from flask_login import login_required, current_user
from werkzeug.security import check_password_hash
import jwt

from app.extensions import db, limiter
from app.models import User, Role, DeviceToken
from app.audit import log_action
from . import bp
from .utils import api_response, api_error

logger = logging.getLogger("app.api_v1.auth")


def generate_tokens(user: User, device_id: str = None):
    """Generate access and refresh tokens for a user."""
    secret_key = current_app.config.get("SECRET_KEY")
    
    # Access token (15 minutes)
    access_payload = {
        "user_id": user.id,
        "role": user.role.name if user.role else "user",
        "type": "access",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(minutes=15),
    }
    access_token = jwt.encode(access_payload, secret_key, algorithm="HS256")
    
    # Refresh token (7 days)
    refresh_payload = {
        "user_id": user.id,
        "type": "refresh",
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(days=7),
    }
    refresh_token = jwt.encode(refresh_payload, secret_key, algorithm="HS256")
    
    # Store device token if device_id provided
    if device_id:
        device_token = DeviceToken(
            user_id=user.id,
            device_id=device_id,
            refresh_token=refresh_token,
            user_agent=request.headers.get("User-Agent", ""),
            ip_address=request.remote_addr,
            expires_at=datetime.utcnow() + timedelta(days=7),
        )
        db.session.add(device_token)
        db.session.commit()
        logger.info(f"Created device token for user {user.id} on device {device_id}")
    
    return access_token, refresh_token


def verify_token(token: str, token_type: str = "access"):
    """Verify a JWT token and return the payload."""
    secret_key = current_app.config.get("SECRET_KEY")
    try:
        payload = jwt.decode(token, secret_key, algorithms=["HS256"])
        if payload.get("type") != token_type:
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator to require valid JWT token in Authorization header."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        if "Authorization" in request.headers:
            try:
                token = request.headers["Authorization"].split(" ")[1]
            except IndexError:
                return api_error("Invalid authorization header", 401)
        
        if not token:
            return api_error("Authorization token is missing", 401)
        
        payload = verify_token(token, "access")
        if not payload:
            return api_error("Invalid or expired token", 401)
        
        # Attach user info to request
        request.user_id = payload.get("user_id")
        request.user_role = payload.get("role")
        
        return f(*args, **kwargs)
    
    return decorated_function


# ============================================================================
# Authentication Endpoints
# ============================================================================
@bp.route("/auth/login", methods=["POST"])
@limiter.limit("5/minute")
def login():
    """
    User login endpoint.
    
    Request body:
        - email (str): User email
        - password (str): User password
        - device_id (str, optional): Device identifier for mobile apps
    
    Returns:
        - access_token (str): JWT access token (15 minutes)
        - refresh_token (str): JWT refresh token (7 days)
        - user (dict): User object
    """
    try:
        data = request.get_json()
        if not data:
            return api_error("Request body is required", 400)
        
        email = data.get("email", "").strip().lower()
        password = data.get("password", "")
        device_id = data.get("device_id", "")
        
        if not email or not password:
            return api_error("Email and password are required", 400)
        
        # Find user
        user = User.query.filter_by(email=email).first()
        if not user or not user.check_password(password):
            logger.warning(f"Failed login attempt for email: {email}")
            return api_error("Invalid email or password", 401)
        
        if not user.is_active:
            return api_error("Account is inactive", 403)
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Generate tokens
        access_token, refresh_token = generate_tokens(user, device_id)
        
        # Log audit event
        log_action(
            user_id=user.id,
            action="login",
            resource="user",
            resource_id=user.id,
            details={"device_id": device_id, "ip": request.remote_addr},
        )
        
        return api_response(
            data={
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role.name if user.role else "user",
                    "is_admin": user.is_admin,
                },
            },
            message="Login successful",
        )
    
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return api_error("An error occurred during login", 500)


@bp.route("/auth/register", methods=["POST"])
@limiter.limit("3/minute")
def register():
    """
    User registration endpoint.
    
    Request body:
        - full_name (str): User's full name
        - username (str): Unique username
        - email (str): Unique email
        - phone (str): Phone number
        - password (str): Password
        - organization (str, optional): Organization name
    
    Returns:
        - user (dict): Created user object
    """
    try:
        data = request.get_json()
        if not data:
            return api_error("Request body is required", 400)
        
        # Validate required fields
        required = ["full_name", "username", "email", "phone", "password"]
        for field in required:
            if not data.get(field):
                return api_error(f"{field} is required", 400)
        
        # Check if email already exists
        if User.query.filter_by(email=data["email"].lower()).first():
            return api_error("Email already registered", 409)
        
        # Check if username already exists
        if User.query.filter_by(username=data["username"].lower()).first():
            return api_error("Username already taken", 409)
        
        # Create user
        user = User(
            full_name=data["full_name"].strip(),
            username=data["username"].strip().lower(),
            email=data["email"].strip().lower(),
            phone=data["phone"].strip(),
            organization=data.get("organization", "").strip() or None,
            role_id=Role.query.filter_by(name="user").first().id,
        )
        user.set_password(data["password"])
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"New user registered: {user.email}")
        log_action(
            user_id=user.id,
            action="register",
            resource="user",
            resource_id=user.id,
            details={"ip": request.remote_addr},
        )
        
        return api_response(
            data={
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "full_name": user.full_name,
                    "role": user.role.name if user.role else "user",
                }
            },
            message="Registration successful. Please log in.",
        )
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {str(e)}")
        return api_error("An error occurred during registration", 500)


@bp.route("/auth/refresh", methods=["POST"])
@limiter.limit("10/minute")
def refresh():
    """
    Refresh access token using refresh token.
    
    Request body:
        - refresh_token (str): Valid refresh token
    
    Returns:
        - access_token (str): New JWT access token
    """
    try:
        data = request.get_json()
        if not data:
            return api_error("Request body is required", 400)
        
        refresh_token = data.get("refresh_token", "")
        if not refresh_token:
            return api_error("Refresh token is required", 400)
        
        # Verify refresh token
        payload = verify_token(refresh_token, "refresh")
        if not payload:
            return api_error("Invalid or expired refresh token", 401)
        
        user_id = payload.get("user_id")
        user = User.query.get(user_id)
        if not user or not user.is_active:
            return api_error("User not found or inactive", 401)
        
        # Generate new access token
        access_payload = {
            "user_id": user.id,
            "role": user.role.name if user.role else "user",
            "type": "access",
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(minutes=15),
        }
        secret_key = current_app.config.get("SECRET_KEY")
        access_token = jwt.encode(access_payload, secret_key, algorithm="HS256")
        
        logger.info(f"Token refreshed for user {user.id}")
        
        return api_response(
            data={"access_token": access_token},
            message="Token refreshed successfully",
        )
    
    except Exception as e:
        logger.error(f"Token refresh error: {str(e)}")
        return api_error("An error occurred during token refresh", 500)


@bp.route("/auth/logout", methods=["POST"])
@limiter.limit("10/minute")
@token_required
def logout():
    """
    Logout the current user (invalidate device token).
    
    Headers:
        - Authorization: Bearer <access_token>
    """
    try:
        user_id = request.user_id
        device_id = request.headers.get("X-Device-ID", "")
        
        # Invalidate device token
        if device_id:
            DeviceToken.query.filter_by(
                user_id=user_id, device_id=device_id
            ).delete()
            db.session.commit()
            logger.info(f"Logged out user {user_id} from device {device_id}")
        
        log_action(
            user_id=user_id,
            action="logout",
            resource="user",
            resource_id=user_id,
            details={"device_id": device_id},
        )
        
        return api_response(
            data={},
            message="Logout successful",
        )
    
    except Exception as e:
        logger.error(f"Logout error: {str(e)}")
        return api_error("An error occurred during logout", 500)


@bp.route("/auth/logout-everywhere", methods=["POST"])
@limiter.limit("5/minute")
@token_required
def logout_everywhere():
    """
    Logout from all devices (invalidate all device tokens for user).
    
    Headers:
        - Authorization: Bearer <access_token>
    """
    try:
        user_id = request.user_id
        
        # Invalidate all device tokens
        DeviceToken.query.filter_by(user_id=user_id).delete()
        db.session.commit()
        
        logger.info(f"Logged out user {user_id} from all devices")
        log_action(
            user_id=user_id,
            action="logout_everywhere",
            resource="user",
            resource_id=user_id,
            details={},
        )
        
        return api_response(
            data={},
            message="Logged out from all devices successfully",
        )
    
    except Exception as e:
        logger.error(f"Logout everywhere error: {str(e)}")
        return api_error("An error occurred during logout", 500)


@bp.route("/auth/validate", methods=["GET"])
@token_required
def validate_token():
    """
    Validate the current JWT token.
    
    Headers:
        - Authorization: Bearer <access_token>
    
    Returns:
        - valid (bool): Token validity status
        - user_id (int): Authenticated user ID
        - role (str): User role
    """
    return api_response(
        data={
            "valid": True,
            "user_id": request.user_id,
            "role": request.user_role,
        },
        message="Token is valid",
    )

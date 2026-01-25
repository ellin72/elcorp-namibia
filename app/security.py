"""
app/security.py - Security utilities including token generation, email confirmation, 
and role-based access control (RBAC) decorators.
"""
import logging
from functools import wraps
from itsdangerous import URLSafeTimedSerializer
from flask import current_app, abort, request
from flask_login import current_user

logger = logging.getLogger("app.api")


def generate_token(email):
    """Generate an email confirmation token."""
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return s.dumps(email, salt='email-confirm')


def confirm_token(token, expiration=3600):
    """Verify an email confirmation token."""
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        return s.loads(token, salt='email-confirm', max_age=expiration)
    except Exception:
        return False


def require_role(*roles):
    """
    Decorator to require specific roles for endpoint access.
    
    Usage:
        @app.route('/admin')
        @require_role('admin')
        def admin_only():
            return "Admin area"
        
        @app.route('/staff-or-admin')
        @require_role('staff', 'admin')
        def staff_or_admin():
            return "Staff or admin area"
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                logger.warning(f"Unauthenticated access attempt to {request.path}")
                abort(401)  # Unauthorized
            
            if not current_user.is_active:
                logger.warning(f"Inactive user {current_user.id} access attempt to {request.path}")
                abort(403)  # Forbidden - account inactive
            
            if not current_user.role or current_user.role.name not in roles:
                logger.warning(
                    f"Access denied for user {current_user.id} with role {current_user.role.name if current_user.role else 'None'} "
                    f"to {request.path}. Required roles: {roles}"
                )
                abort(403)  # Forbidden
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_admin(f):
    """Convenience decorator to require admin role."""
    return require_role('admin')(f)


def require_any_role(*roles):
    """
    Alternative name for require_role - require at least one of the given roles.
    """
    return require_role(*roles)


def is_admin(user=None):
    """Check if a user (or current_user) has admin role."""
    if user is None:
        user = current_user
    return user and user.is_authenticated and user.role and user.role.name == 'admin'


def is_staff(user=None):
    """Check if a user (or current_user) has staff role."""
    if user is None:
        user = current_user
    return user and user.is_authenticated and user.role and user.role.name == 'staff'


def can_access_user(target_user_id, current_user_obj=None):
    """
    Check if current user can access another user's data.
    Admin can access anyone. Regular users can only access their own.
    """
    if current_user_obj is None:
        current_user_obj = current_user
    
    if not current_user_obj.is_authenticated:
        return False
    
    if is_admin(current_user_obj):
        return True
    
    return current_user_obj.id == target_user_id


# Legacy support
def role_required(*roles):
    """Legacy decorator name for role-based access control."""
    return require_role(*roles)


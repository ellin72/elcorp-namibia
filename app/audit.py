from .extensions import db
from .models import AuditLog
from flask_login import current_user

def log_action(action, details=None):
    entry = AuditLog(
        user_id=current_user.id if current_user.is_authenticated else None,
        action=action,
        details=details or {}
    )
    db.session.add(entry)
    db.session.commit()
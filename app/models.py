# app/models.py
from datetime import datetime
from .extensions import db
from flask_login import UserMixin

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    otp_secret = db.Column(db.String(32), nullable=True)  # for 2FA
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class VinRecord(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), nullable=False, index=True)
    meta = db.Column(db.JSON, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.JSON, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class PasswordHistory(db.Model):
    __tablename__ = "password_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


# app/__init__.py (add after db.init_app)
from .extensions import login_manager
from .models import User

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


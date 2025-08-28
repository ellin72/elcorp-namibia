"""
app/models.py

Database models for users, VIN records, audit logs, vehicles, transactions,
and password-reset history with audit trails.
"""
import uuid
import logging
from datetime import datetime, timedelta

from flask import current_app, request
from flask_login import UserMixin
from itsdangerous import URLSafeSerializer, BadData
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import event

from .extensions import db, login_manager

# custom salt for password-reset tokens
RESET_PASSWORD_SALT = "password-reset-salt"


class Role(db.Model):
    """Role model for defining user roles and permissions."""
    __tablename__ = 'role'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))

    # One-to-many: one role has many users
    users = db.relationship('User', back_populates='role', lazy='dynamic')

    def __repr__(self):
        return f"<Role {self.name}>"


class User(UserMixin, db.Model):
    """User model for storing user details and authentication info."""
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    organization = db.Column(db.String(100), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    is_admin = db.Column(db.Boolean, default=False)
    otp_secret = db.Column(db.String(32), nullable=True)
    agreed_terms = db.Column(db.Boolean, default=False)
    wallet_address = db.Column(db.String(36), unique=True, nullable=False)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Single role assignment (non-nullable)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    role = db.relationship('Role', back_populates='users')

    def __repr__(self):
        return f"<User {self.email} Role: {self.role.name if self.role else 'None'}>"

    def set_password(self, password: str):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name: str) -> bool:
        """Check if the user has a given role."""
        return self.role and self.role.name == role_name

    def generate_wallet_address(self) -> str:
        """Generate a new UUID4 wallet address."""
        return str(uuid.uuid4())
############################################################################################

    def get_reset_password_token(self, expires_sec: int = None) -> str:
        """
        Return a URL-safe token with:
          - user_id (int)
          - iat     (issued-at timestamp)
          - optional exp (expiry timestamp) if expires_sec passed
        Raises RuntimeError if neither expires_sec nor config is a valid positive int.
        """
        now_ts = int(datetime.utcnow().timestamp())

        # Determine expiry
        if expires_sec is not None:
            if not isinstance(expires_sec, int) or expires_sec <= 0:
                raise RuntimeError(f"Invalid TOKEN_EXPIRY: {expires_sec!r}")
            exp_ts = now_ts + expires_sec
        else:
            cfg = current_app.config.get("PASSWORD_RESET_TOKEN_EXPIRY")
            if not isinstance(cfg, int) or cfg <= 0:
                raise RuntimeError(f"Invalid TOKEN_EXPIRY: {cfg!r}")
            exp_ts = None

        # Build payload
        payload = {"user_id": self.id, "iat": now_ts}
        if exp_ts is not None:
            payload["exp"] = exp_ts

        serializer = URLSafeSerializer(
            secret_key=current_app.config["SECRET_KEY"],
            salt=RESET_PASSWORD_SALT
        )
        return serializer.dumps(payload)


    @staticmethod
    def verify_reset_password_token(token: str):
        """
        Verify a password-reset token by:
          1. checking its signature
          2. reading payload["exp"] if set, else using payload["iat"] + config
        Logs the attempt and returns the User on success, or None on failure.
        """
        serializer = URLSafeSerializer(
            secret_key=current_app.config["SECRET_KEY"],
            salt=RESET_PASSWORD_SALT
        )
        logger = logging.getLogger("app.password_reset_audit")

        succeeded = False
        user_id = None
        reason = "unknown"
        now_ts = int(datetime.utcnow().timestamp())

        try:
            data = serializer.loads(token)
            user_id = data.get("user_id")
            iat = data.get("iat", 0)
            exp_ts = data.get("exp", None)

            if exp_ts is not None:
                # explicit expiry embedded
                if now_ts > exp_ts:
                    reason = "expired"
                else:
                    succeeded = True
                    reason = "valid"
            else:
                # fallback to config expiry
                cfg = current_app.config.get("PASSWORD_RESET_TOKEN_EXPIRY")
                if not isinstance(cfg, int) or cfg <= 0:
                    reason = "invalid_config"
                elif (now_ts - iat) > cfg:
                    reason = "expired"
                else:
                    succeeded = True
                    reason = "valid"

        except BadData:
            reason = "invalid_token"

        # record audit
        audit = PasswordResetAudit(
            user_id=user_id,
            succeeded=succeeded,
            reason=reason,
            ip_address=request.remote_addr,
            token=token
        )
        db.session.add(audit)
        db.session.commit()

        if succeeded:
            return User.query.get(user_id)

        logger.info(
            f"Password reset failed: user_id={user_id} "
            f"reason={reason} ip={request.remote_addr}"
        )
        return None
    
######################################################################################################

@event.listens_for(User, "before_insert")
def assign_default_role(mapper, connection, target):
    if not target.role:
        # use the connection to run a SELECT without touching db.session
        role_id = connection.execute(
            Role.__table__.select().where(Role.name == "user")
        ).scalar()
        if role_id:
            target.role_id = role_id
        else:
            # create a default role in a separate, controlled setup step
            raise RuntimeError("Default role 'user' missing in DB — seed roles first")



@db.event.listens_for(User, "before_insert")
def _assign_wallet_address(mapper, connection, target):
    """Automatically assign a UUID wallet address before inserting a new user."""
    if not target.wallet_address:
        target.wallet_address = target.generate_wallet_address()


class VinRecord(db.Model):
    __tablename__ = "vin_record"

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), nullable=False, index=True)
    meta = db.Column(db.JSON, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    __tablename__ = "audit_log"

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


class PasswordResetAudit(db.Model):
    __tablename__ = "password_reset_audit"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    succeeded = db.Column(db.Boolean, nullable=False)
    reason = db.Column(db.String(64), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    token = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Vehicle(db.Model):
    __tablename__ = "vehicles"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    plate_number = db.Column(db.String(20), unique=True, nullable=False)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    owner = db.relationship("User", backref="vehicles")


class Transaction(db.Model):
    __tablename__ = "transactions"

    id = db.Column(db.Integer, primary_key=True)
    from_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    to_user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    sender = db.relationship("User", foreign_keys=[from_user_id])
    receiver = db.relationship("User", foreign_keys=[to_user_id])


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

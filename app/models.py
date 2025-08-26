"""app/models.py

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

from .extensions import db, login_manager

# custom salt for password-reset tokens
RESET_PASSWORD_SALT = "password-reset-salt"


# association table for many-to-many User <→ Role
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)


class Role(db.Model):
    """Role model for defining user roles and permissions."""
    __tablename__ = 'role'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)
    description = db.Column(db.String(255))

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

    roles = db.relationship(
        'Role',
        secondary=user_roles,
        backref=db.backref('users', lazy='dynamic')
    )

    def __repr__(self):
        role_names = [r.name for r in self.roles] or ['None']
        return f"<User {self.email} Roles: {', '.join(role_names)}>"

    def set_password(self, password: str):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Verify a plaintext password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def has_role(self, role_name: str) -> bool:
        """Check if the user has a given role."""
        return any(r.name == role_name for r in self.roles)

    def generate_wallet_address(self) -> str:
        """Generate a new UUID4 wallet address."""
        return str(uuid.uuid4())

    def get_reset_password_token(self, expires_sec: int = None) -> str:
        """
        Create a URL-safe token for password reset containing:
          - user_id
          - exp  (expiration timestamp)
        """
        expires = expires_sec or current_app.config.get("PASSWORD_RESET_TOKEN_EXPIRY", 600)
        if not isinstance(expires, int) or expires <= 0:
            raise RuntimeError(f"Invalid TOKEN_EXPIRY: {expires!r}")

        serializer = URLSafeSerializer(
            secret_key=current_app.config["SECRET_KEY"],
            salt=RESET_PASSWORD_SALT
        )
        exp_time = datetime.utcnow() + timedelta(seconds=expires)
        payload = {"user_id": self.id, "exp": int(exp_time.timestamp())}
        return serializer.dumps(payload)

    @staticmethod
    def verify_reset_password_token(token: str):
        """
        Validate a password-reset token:
          - rejects malformed or bad signatures
          - rejects expired tokens
          - logs each attempt in PasswordResetAudit
        Returns the User on success, or None on failure.
        """
        serializer = URLSafeSerializer(
            secret_key=current_app.config["SECRET_KEY"],
            salt=RESET_PASSWORD_SALT
        )
        logger = logging.getLogger("app.password_reset_audit")

        succeeded = False
        user_id = None
        reason = "unknown"

        try:
            data = serializer.loads(token)
            user_id = data.get("user_id")
            if data.get("exp", 0) < int(datetime.utcnow().timestamp()):
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
        logger.info(f"Password reset failed: user_id={user_id} reason={reason} ip={request.remote_addr}")
        return None


@db.event.listens_for(User, "before_insert")
def _assign_wallet_address(mapper, connection, target):
    """
    Automatically assign a UUID wallet address before inserting a new user.
    """
    if not target.wallet_address:
        target.wallet_address = target.generate_wallet_address()


class VinRecord(db.Model):
    """Vehicle Identification Number records."""
    __tablename__ = "vin_record"

    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), nullable=False, index=True)
    meta = db.Column(db.JSON, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class AuditLog(db.Model):
    """General-purpose audit log of user actions."""
    __tablename__ = "audit_log"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.JSON, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)


class PasswordHistory(db.Model):
    """Keeps historical password hashes to prevent reuse."""
    __tablename__ = "password_history"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class PasswordResetAudit(db.Model):
    """Logs each password-reset attempt and outcome."""
    __tablename__ = "password_reset_audit"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=True)
    succeeded = db.Column(db.Boolean, nullable=False)
    reason = db.Column(db.String(64), nullable=False)
    ip_address = db.Column(db.String(45), nullable=True)
    token = db.Column(db.Text, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Vehicle(db.Model):
    """User-owned vehicle records."""
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
    """Elcoin transfer transactions between users."""
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
    """Flask-Login user loader callback."""
    return User.query.get(int(user_id))

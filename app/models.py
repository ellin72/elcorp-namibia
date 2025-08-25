# app/models.py
"""Database models for users, VIN records, audit logs, and password history."""
from datetime import datetime, timedelta
from flask_login import UserMixin
from itsdangerous import URLSafeSerializer, BadSignature, BadData
from .extensions import login_manager

from flask import current_app, request
import logging
from werkzeug.security import generate_password_hash, check_password_hash
from .extensions import db

# use a custom salt so URLSafeTimedSerializer can distinguish token types
RESET_PASSWORD_SALT = "password-reset-salt"

# 1️⃣ Association table — put this near the top of models.py, after imports
user_roles = db.Table(
    'user_roles',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('role_id', db.Integer, db.ForeignKey('role.id'), primary_key=True)
)

# 2️⃣ Role model — place this before the User class
class Role(db.Model):
    """Role model for defining user roles and permissions."""
    __tablename__ = 'role'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True, nullable=False)  # e.g. 'admin', 'verifier', 'user'
    description = db.Column(db.String(255))

    def __repr__(self):
        return f"<Role {self.name}>"

# 3️⃣ Updated User model — replace your current version with this

class User(UserMixin, db.Model):
    """User model for storing user details and authentication information."""
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
    otp_secret = db.Column(db.String(32), nullable=True)  # for 2FA
    agreed_terms = db.Column(db.Boolean, default=False)
    wallet_address = db.Column(db.String(42), unique=True, nullable=True)
    last_login = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 🔹 New many-to-many relationship with Role
    roles = db.relationship(
        'Role',
        secondary=user_roles,
        backref=db.backref('users', lazy='dynamic')
    )

    def has_role(self, role_name):
        """Check if the user has a specific role."""
        return any(role.name == role_name for role in self.roles)
    
    def set_password(self, password):
        """Hash and set the user's password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check the user's password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.email} — {self.role}>"
    

    def get_reset_password_token(self):
        """
        Generate a URL-safe token including:
          - user_id
          - exp: Unix timestamp when this token expires

        Reads `PASSWORD_RESET_TOKEN_EXPIRES` from Flask config and
        raises RuntimeError if it’s not a positive integer.
        """
        # 1. Pull from config
        expires_sec = current_app.config.get("PASSWORD_RESET_TOKEN_EXPIRES")

        # 2. Validate
        if not isinstance(expires_sec, int) or expires_sec <= 0:
            raise RuntimeError(
                "Invalid PASSWORD_RESET_TOKEN_EXPIRES: must be a positive integer"
            )

        # 3. Build the serializer and payload
        s = URLSafeSerializer(
            secret_key=current_app.config["SECRET_KEY"],
            salt=RESET_PASSWORD_SALT
        )
        expire_time = datetime.utcnow() + timedelta(seconds=expires_sec)
        payload = {
            "user_id": self.id,
            "exp":      int(expire_time.timestamp())
        }

        # 4. Return the token
        return s.dumps(payload)

    
 #################################################################################
    @staticmethod
    def verify_reset_password_token(token):
        serializer = URLSafeSerializer(
            secret_key=current_app.config['SECRET_KEY'],
            salt=RESET_PASSWORD_SALT
        )
        logger = logging.getLogger("app.password_reset_audit")

        try:
            data = serializer.loads(token)
        except BadData:
            reason = 'bad_signature_or_malformed'
            user_id = None
        else:
            user_id = data.get('user_id')
            exp_ts  = data.get('exp', 0)
            # check expiration
            if exp_ts < int(datetime.utcnow().timestamp()):
                reason = 'expired'
            else:
                # successful verification
                PasswordResetAudit(
                    user_id    = user_id,
                    succeeded  = True,
                    reason     = 'valid',
                    ip_address = request.remote_addr,
                    token      = token
                ).save()  # Or session.add() + commit
                return User.query.get(user_id)

        # on failure (expired or bad_data), record audit + log
        audit = PasswordResetAudit(
            user_id    = user_id,
            succeeded  = False,
            reason     = reason,
            ip_address = request.remote_addr,
            token      = token
        )
        db.session.add(audit)
        db.session.commit()

        # write to file/logger
        logger.info(
            f"password-reset failure: user_id={user_id!r} reason={reason} "
            f"ip={request.remote_addr} token={token}"
        )
        return None


##################################################################################################
class VinRecord(db.Model):
    """Model to store Vehicle Identification Number (VIN) records."""
    __tablename__ = "vin_record"
    id = db.Column(db.Integer, primary_key=True)
    vin = db.Column(db.String(17), nullable=False, index=True)
    meta = db.Column(db.JSON, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey("user.id"))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class AuditLog(db.Model):
    """Model to log user actions for auditing purposes."""
    __tablename__ = "audit_log"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    action = db.Column(db.String(50), nullable=False)
    details = db.Column(db.JSON, nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class PasswordHistory(db.Model):
    """Model to store historical passwords for users to prevent reuse."""
    __tablename__ = "password_history"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class PasswordResetAudit(db.Model):
    """Model to log password reset attempts and their outcomes."""
    __tablename__ = 'password_reset_audit'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, nullable=True)     # who tried
    succeeded  = db.Column(db.Boolean, nullable=False)    # True on success
    reason     = db.Column(db.String(64), nullable=False) # 'expired', 'bad_signature', etc.
    ip_address = db.Column(db.String(45), nullable=True)  # IPv4 or v6
    token      = db.Column(db.Text, nullable=True)        # consider hashing if sensitive
    timestamp  = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


##########################################################################
@login_manager.user_loader
def load_user(user_id):
    """Load user by ID for Flask-Login."""
    return User.query.get(int(user_id))


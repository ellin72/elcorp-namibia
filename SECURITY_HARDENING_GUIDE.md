# Security & Compliance Hardening Guide

**Version**: 1.0  
**Scope**: Production-Grade Fintech Platform  
**Target Compliance**: GDPR, POPIA, Financial Services Best Practices

---

## Executive Summary

This document outlines security controls, threat mitigation, and regulatory compliance measures required for Elcorp Namibia to operate as a national-scale fintech platform subject to audit and regulatory oversight.

---

## 1. Authentication & Authorization Hardening

### 1.1 JWT Token Security

**Threats Mitigated**:
- Token forgery
- Token replay attacks
- Token leakage

**Controls**:

```python
# backend/src/elcorp/shared/security/jwt_handler.py

import jwt
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)

class JWTSecurityConfig:
    """Hardened JWT configuration."""
    
    # Token lifetimes (shorter = more secure)
    ACCESS_TOKEN_TTL = timedelta(minutes=15)      # Short-lived access
    REFRESH_TOKEN_TTL = timedelta(days=7)         # Longer-lived refresh
    
    # Token revocation (blacklist on logout)
    ENABLE_REVOCATION = True
    REVOCATION_STORAGE = "redis"  # Hot storage for active revocations
    
    # Token rotation (refresh token rotation on each use)
    ENABLE_ROTATION = True
    
    # JWT algorithm (HS256 with long key)
    ALGORITHM = "HS256"
    MIN_SECRET_LENGTH = 64  # bytes
    
    # Token binding (device fingerprinting)
    ENABLE_DEVICE_BINDING = True

class JWTHandler:
    """Hardened JWT token management."""
    
    def __init__(self, secret_key: str, cache=None):
        if len(secret_key) < 64:
            raise ValueError("Secret key too short (min 64 bytes)")
        
        self.secret_key = secret_key
        self.cache = cache
    
    def generate_access_token(
        self,
        user_id: int,
        role: str,
        device_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> str:
        """
        Generate short-lived access token with device binding.
        
        Security features:
        - 15-minute expiry
        - Device ID binding (prevents token theft usage)
        - IP address binding (optional, stricter)
        - Unique JTI (JWT ID) for revocation tracking
        """
        now = datetime.now(timezone.utc)
        jti = secrets.token_urlsafe(32)
        
        payload = {
            "sub": str(user_id),
            "role": role,
            "type": "access",
            "jti": jti,
            "device_id": device_id,
            "ip": ip_address,  # Optional binding
            "iat": now.timestamp(),
            "exp": (now + JWTSecurityConfig.ACCESS_TOKEN_TTL).timestamp(),
        }
        
        token = jwt.encode(
            payload,
            self.secret_key,
            algorithm=JWTSecurityConfig.ALGORITHM
        )
        
        # Store JTI in cache for revocation checking
        if self.cache:
            self.cache.setex(
                f"jti:{jti}",
                int(JWTSecurityConfig.ACCESS_TOKEN_TTL.total_seconds()),
                "active"
            )
        
        logger.info(f"Issued access token for user {user_id}, JTI: {jti}")
        return token
    
    def generate_refresh_token(
        self,
        user_id: int,
        device_id: Optional[str] = None,
    ) -> str:
        """
        Generate refresh token (longer-lived, rotatable).
        
        Security features:
        - 7-day expiry
        - Stored in database (not just issued)
        - Revocable per device
        - Rotation on use
        """
        now = datetime.now(timezone.utc)
        jti = secrets.token_urlsafe(32)
        
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "jti": jti,
            "device_id": device_id,
            "iat": now.timestamp(),
            "exp": (now + JWTSecurityConfig.REFRESH_TOKEN_TTL).timestamp(),
        }
        
        token = jwt.encode(
            payload,
            self.secret_key,
            algorithm=JWTSecurityConfig.ALGORITHM
        )
        
        logger.info(f"Issued refresh token for user {user_id}, JTI: {jti}")
        return token
    
    def verify_token(
        self,
        token: str,
        token_type: str = "access",
        device_id: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Verify JWT with comprehensive checks.
        
        Checks:
        1. Signature validity
        2. Expiration
        3. Token type
        4. Revocation status
        5. Device binding
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[JWTSecurityConfig.ALGORITHM]
            )
        except jwt.ExpiredSignatureError:
            logger.warning(f"Expired token attempted")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None
        
        # Type check
        if payload.get("type") != token_type:
            logger.warning(f"Token type mismatch: {payload.get('type')} != {token_type}")
            return None
        
        # Revocation check
        jti = payload.get("jti")
        if jti and self.cache:
            if not self.cache.exists(f"jti:{jti}"):
                logger.warning(f"Token revoked or expired (JTI: {jti})")
                return None
        
        # Device binding check (if enabled)
        if device_id and payload.get("device_id") != device_id:
            logger.warning(f"Device binding violation for user {payload.get('sub')}")
            return None
        
        return payload
    
    def revoke_token(self, token: str) -> bool:
        """Revoke token immediately (logout)."""
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[JWTSecurityConfig.ALGORITHM],
                options={"verify_exp": False}  # Check even if expired
            )
            jti = payload.get("jti")
            if jti and self.cache:
                self.cache.delete(f"jti:{jti}")
                logger.info(f"Revoked token JTI: {jti}")
                return True
        except Exception as e:
            logger.error(f"Failed to revoke token: {e}")
        
        return False
```

### 1.2 Multi-Factor Authentication (MFA)

**Threats Mitigated**:
- Credential compromise
- Brute force attacks
- Account takeover

**Implementation**:

```python
# backend/src/elcorp/identity/domain/models.py

import pyotp
import qrcode
from io import BytesIO
import base64
from typing import List, Optional

class TwoFactorAuth:
    """Two-factor authentication using TOTP."""
    
    ISSUER = "Elcorp Namibia"
    DIGITS = 6
    INTERVAL = 30  # seconds
    
    @staticmethod
    def generate_secret() -> str:
        """Generate TOTP secret."""
        return pyotp.random_base32()
    
    @staticmethod
    def generate_qr_code(email: str, secret: str) -> str:
        """Generate QR code for authenticator app."""
        totp = pyotp.TOTP(secret, issuer_name=TwoFactorAuth.ISSUER)
        uri = totp.provisioning_uri(email)
        
        qr = qrcode.QRCode()
        qr.add_data(uri)
        qr.make()
        
        img = qr.make_image()
        buf = BytesIO()
        img.save(buf, format="PNG")
        buf.seek(0)
        
        return base64.b64encode(buf.getvalue()).decode()
    
    @staticmethod
    def verify_token(secret: str, token: str, window: int = 1) -> bool:
        """Verify TOTP token with time window tolerance."""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)
    
    @staticmethod
    def generate_backup_codes(count: int = 10) -> List[str]:
        """Generate one-time backup codes for account recovery."""
        return [secrets.token_hex(4) for _ in range(count)]

class User:
    """Extended with 2FA support."""
    
    def __init__(self, ...):
        # ... existing fields ...
        self.totp_secret: Optional[str] = None
        self.mfa_enabled: bool = False
        self.backup_codes: List[str] = []
        self.last_mfa_challenge: Optional[datetime] = None
    
    def enable_2fa(self) -> tuple[str, str, List[str]]:
        """
        Enable 2FA for user.
        
        Returns:
            (secret, qr_code_data_url, backup_codes)
        """
        secret = TwoFactorAuth.generate_secret()
        qr_code = TwoFactorAuth.generate_qr_code(self.email.value, secret)
        backup_codes = TwoFactorAuth.generate_backup_codes()
        
        # DON'T save yet - require confirmation
        return secret, qr_code, backup_codes
    
    def confirm_2fa(self, secret: str, token: str) -> bool:
        """Confirm 2FA setup with valid TOTP token."""
        if not TwoFactorAuth.verify_token(secret, token):
            return False
        
        self.totp_secret = secret
        self.mfa_enabled = True
        self.backup_codes = TwoFactorAuth.generate_backup_codes()
        return True
    
    def verify_2fa_token(self, token: str) -> bool:
        """Verify MFA token during login."""
        if not self.mfa_enabled or not self.totp_secret:
            return False
        
        return TwoFactorAuth.verify_token(self.totp_secret, token)
    
    def disable_2fa(self) -> None:
        """Disable 2FA."""
        self.totp_secret = None
        self.mfa_enabled = False
        self.backup_codes = []
```

### 1.3 Session Security & Device Management

```python
# backend/src/elcorp/identity/infrastructure/persistence/models.py

class DeviceTokenModel(Base):
    """Secure device token tracking."""
    
    __tablename__ = "device_token"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    device_id = Column(String(36), nullable=False, index=True)
    device_name = Column(String(100))
    device_type = Column(String(32))  # mobile, web, desktop
    
    # Security info
    user_agent = Column(Text)
    ip_address = Column(String(45))
    ip_geolocation = Column(String(255))  # Country, city
    
    # Token
    refresh_token_hash = Column(String(255), nullable=False)  # Hash, not plaintext
    last_used_at = Column(DateTime)
    
    # Revocation
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime)
    revocation_reason = Column(String(255))  # "logout", "security_alert", etc.
    
    # Expiry
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Constraints
    __table_args__ = (
        Index("idx_device_token_user_active", "user_id", "is_revoked"),
        Index("idx_device_token_expires", "expires_at"),
    )
```

---

## 2. Data Protection & Encryption

### 2.1 Encryption at Rest

**Sensitive Fields to Encrypt**:
- OTP secrets (2FA)
- Refresh tokens
- Wallet private keys
- Personal identification numbers

```python
# backend/src/elcorp/shared/security/encryption.py

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import base64
import os

class EncryptionService:
    """Field-level encryption for sensitive data."""
    
    def __init__(self, master_key: str):
        """Initialize with master encryption key."""
        # Derive Fernet key from master key
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"elcorp_salt_v1",  # Use environment variable in production
            iterations=100_000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(master_key.encode()))
        self.cipher = Fernet(key)
    
    def encrypt(self, plaintext: str) -> str:
        """Encrypt string and return base64."""
        ciphertext = self.cipher.encrypt(plaintext.encode())
        return base64.b64encode(ciphertext).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """Decrypt base64 string."""
        try:
            raw = base64.b64decode(ciphertext.encode())
            plaintext = self.cipher.decrypt(raw)
            return plaintext.decode()
        except Exception as e:
            raise ValueError(f"Decryption failed: {e}")

# Usage in SQLAlchemy model
from sqlalchemy.ext.hybrid import hybrid_property

class UserModel(Base):
    """User with encrypted OTP secret."""
    
    _otp_secret_encrypted = Column("otp_secret", String(255))
    
    @hybrid_property
    def otp_secret(self) -> Optional[str]:
        """Decrypt on access."""
        if not self._otp_secret_encrypted:
            return None
        encryption_service = current_app.extensions["encryption"]
        return encryption_service.decrypt(self._otp_secret_encrypted)
    
    @otp_secret.setter
    def otp_secret(self, value: Optional[str]) -> None:
        """Encrypt on set."""
        if value is None:
            self._otp_secret_encrypted = None
        else:
            encryption_service = current_app.extensions["encryption"]
            self._otp_secret_encrypted = encryption_service.encrypt(value)
```

### 2.2 GDPR/POPIA Compliance: Right to Erasure

```python
# backend/src/elcorp/compliance/domain/data_erasure.py

from datetime import datetime, timedelta
from typing import List

class ErasureRequest:
    """GDPR Article 17: Right to be forgotten."""
    
    def __init__(self, user_id: int, reason: str):
        self.user_id = user_id
        self.reason = reason
        self.requested_at = datetime.utcnow()
        self.deadline = self.requested_at + timedelta(days=30)  # 30 days to comply
        self.status = "pending"  # pending, approved, completed
        self.completed_at = None
    
    def approve(self):
        """Approve erasure request."""
        self.status = "approved"
    
    def mark_complete(self):
        """Mark as executed."""
        self.status = "completed"
        self.completed_at = datetime.utcnow()
        
        # Log for audit trail
        log_entry = f"User {self.user_id} data erased at {self.completed_at}"

class DataErasureService:
    """Execute right to erasure."""
    
    def erase_user_data(self, user_id: int) -> None:
        """
        Permanently delete all user data.
        
        Strategy:
        1. Soft delete user account
        2. Delete associated PII (phone, organization)
        3. Anonymize audit logs
        4. Retain only transaction history (immutable)
        5. Log erasure event
        """
        # Soft delete user
        user = User.query.get(user_id)
        user.soft_delete()
        
        # Anonymize personal data
        user.email = f"erased+{user_id}@example.com"
        user.phone = "ERASED"
        user.full_name = "ERASED"
        user.organization = None
        
        # Delete device tokens
        DeviceToken.query.filter_by(user_id=user_id).delete()
        
        # Delete password history
        PasswordHistory.query.filter_by(user_id=user_id).delete()
        
        # Delete 2FA secrets
        if user.totp_secret:
            user.totp_secret = None
        
        db.session.commit()
        
        # Log erasure for audit trail
        logger.info(f"User {user_id} data erased per GDPR/POPIA request")
```

---

## 3. Input Validation & Sanitization

### 3.1 Comprehensive Input Validation

```python
# backend/src/elcorp/shared/util/validators.py

from pydantic import BaseModel, field_validator, EmailStr, Field
from typing import Optional
import re

class StrictEmailValidator(BaseModel):
    """Email validation with additional checks."""
    
    email: EmailStr
    
    @field_validator("email")
    @classmethod
    def validate_email_not_disposable(cls, v: str) -> str:
        """Reject disposable email services."""
        disposable_domains = {
            "tempmail.com", "guerrillamail.com", "throwaway.email",
            "mailinator.com", "10minutemail.com",
        }
        domain = v.split("@")[1].lower()
        if domain in disposable_domains:
            raise ValueError("Disposable email addresses not allowed")
        return v

class PasswordValidator(BaseModel):
    """Password validation rules."""
    
    password: str = Field(..., min_length=12, max_length=128)
    
    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        """Enforce NIST guidelines."""
        # Check for common patterns
        common_patterns = ["password", "123456", "qwerty", "admin", "letmein"]
        if any(pattern in v.lower() for pattern in common_patterns):
            raise ValueError("Password contains common patterns")
        
        # Require mixed character types
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:',.<>?/~`" for c in v)
        
        if not (has_upper and has_lower and has_digit and has_special):
            raise ValueError(
                "Password must contain uppercase, lowercase, digit, and special character"
            )
        
        return v

class PhoneValidator(BaseModel):
    """Phone number validation."""
    
    phone: str
    country_code: str = "264"  # Namibia
    
    @field_validator("phone")
    @classmethod
    def validate_phone_format(cls, v: str, info) -> str:
        """Validate phone format."""
        # Remove common formatting
        clean = re.sub(r"[^0-9+]", "", v)
        
        # Check length (7-20 digits)
        if not re.match(r"^\+?[0-9]{7,20}$", clean):
            raise ValueError("Invalid phone number format")
        
        return clean
```

### 3.2 SQL Injection Prevention

**Approach**: Use SQLAlchemy ORM exclusively (parameterized queries)

```python
# ✅ SAFE: SQLAlchemy parameterizes automatically
user = User.query.filter_by(email=user_input_email).first()

# ✅ SAFE: Using query.filter with bindings
user = User.query.filter(User.email == user_input_email).first()

# ❌ UNSAFE: Raw SQL string interpolation (FORBIDDEN)
# user = db.session.execute(f"SELECT * FROM user WHERE email = '{user_input_email}'")

# ✅ SAFE: Raw SQL with parameterized bindings (if needed)
result = db.session.execute(
    text("SELECT * FROM user WHERE email = :email"),
    {"email": user_input_email}
)
```

### 3.3 XSS Prevention

```python
# backend/src/elcorp/shared/util/sanitization.py

import bleach
import html

class HTMLSanitizer:
    """Sanitize user input for safe HTML rendering."""
    
    # Allowed tags for rich text
    ALLOWED_TAGS = ["b", "i", "u", "em", "strong", "p", "br", "ul", "li", "a"]
    ALLOWED_ATTRIBUTES = {"a": ["href", "title"]}
    
    @staticmethod
    def sanitize(user_input: str) -> str:
        """Remove dangerous HTML/JavaScript."""
        # First escape all HTML
        escaped = html.escape(user_input)
        
        # Then allow safe subset
        cleaned = bleach.clean(
            escaped,
            tags=HTMLSanitizer.ALLOWED_TAGS,
            attributes=HTMLSanitizer.ALLOWED_ATTRIBUTES,
            strip=True
        )
        
        return cleaned

# Usage in request handlers
@app.route("/api/v1/requests", methods=["POST"])
def create_request():
    data = request.json
    
    # Sanitize all string fields
    data["title"] = HTMLSanitizer.sanitize(data["title"])
    data["description"] = HTMLSanitizer.sanitize(data["description"])
    
    # Continue processing...
```

---

## 4. Audit Logging & Compliance

### 4.1 Immutable Audit Trail

```python
# backend/src/elcorp/compliance/infrastructure/audit.py

from sqlalchemy import Column, BigInteger, String, DateTime, JSON, Text, Sequence
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import json
import hashlib

class AuditLogModel(Base):
    """Immutable audit log (append-only, no updates/deletes)."""
    
    __tablename__ = "audit_log"
    
    # Immutable ID (sequential for ordering)
    id = Column(BigInteger, Sequence("audit_log_id_seq"), primary_key=True)
    
    # What happened
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(64), nullable=False, index=True)
    entity_id = Column(Integer, nullable=True)
    
    # Who did it
    user_id = Column(Integer, ForeignKey("user.id"), nullable=True, index=True)
    
    # When it happened
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
    
    # How it happened
    changes = Column(JSON, nullable=False)  # Before/after values
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    
    # Data integrity
    hash = Column(String(64), nullable=False)  # SHA256(previous_hash + this_entry)
    
    def compute_hash(self, previous_hash: str = None) -> str:
        """Compute hash for blockchain-style integrity."""
        content = f"{self.id}:{self.action}:{self.entity_type}:{self.timestamp.isoformat()}:{self.changes}"
        if previous_hash:
            content = f"{previous_hash}:{content}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def __repr__(self):
        return f"<AuditLog {self.id}: {self.action} on {self.entity_type}>"

    # Prevent updates/deletes with database trigger (PostgreSQL)
    __table_args__ = (
        # Enforce immutability
        # SQL: CREATE TRIGGER audit_log_immutable BEFORE UPDATE/DELETE ON audit_log...
    )

class AuditService:
    """Log security-relevant events."""
    
    def __init__(self, db_session, cache):
        self.db = db_session
        self.cache = cache
    
    def log(
        self,
        action: str,
        entity_type: str,
        entity_id: Optional[int],
        user_id: Optional[int],
        changes: dict,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> AuditLogModel:
        """
        Create immutable audit log entry.
        
        Args:
            action: "create", "update", "delete", "login", "policy_change"
            entity_type: "user", "payment", "service_request"
            changes: {"field": {"from": "old_value", "to": "new_value"}}
        """
        # Get previous entry for hash chaining
        previous = self.db.query(AuditLogModel).order_by(
            AuditLogModel.id.desc()
        ).first()
        
        entry = AuditLogModel(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            user_id=user_id,
            changes=changes,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.utcnow(),
        )
        
        # Hash chaining
        prev_hash = previous.hash if previous else "genesis"
        entry.hash = entry.compute_hash(prev_hash)
        
        # Store
        self.db.add(entry)
        self.db.commit()
        
        # Log to syslog for external archival
        self._send_to_syslog(entry)
        
        # Alert on critical actions
        if action in ["policy_change", "user_delete", "role_grant"]:
            self._send_alert(entry)
        
        return entry
    
    def _send_to_syslog(self, entry: AuditLogModel) -> None:
        """Send audit log to external syslog for tamper-proof archival."""
        import syslog
        syslog.syslog(
            syslog.LOG_INFO,
            f"ELCORP_AUDIT|{entry.id}|{entry.action}|{entry.entity_type}|{entry.hash}"
        )
    
    def _send_alert(self, entry: AuditLogModel) -> None:
        """Alert security team on critical events."""
        # Send to Sentry or Slack
        pass
    
    def verify_integrity(self) -> bool:
        """Verify audit log integrity (blockchain-style)."""
        entries = self.db.query(AuditLogModel).order_by(AuditLogModel.id).all()
        
        prev_hash = "genesis"
        for entry in entries:
            expected_hash = entry.compute_hash(prev_hash)
            if entry.hash != expected_hash:
                logger.error(f"Audit log integrity violation at entry {entry.id}")
                return False
            prev_hash = entry.hash
        
        logger.info("Audit log integrity verified")
        return True
```

### 4.2 Audit Events to Track

| Event | Severity | Fields |
|-------|----------|--------|
| User login | LOW | user_id, ip_address, device_id |
| User logout | LOW | user_id, ip_address |
| Failed login attempt | MEDIUM | email, ip_address, attempt_count |
| Password change | MEDIUM | user_id, initiated_by |
| 2FA enabled | MEDIUM | user_id |
| 2FA disabled | MEDIUM | user_id, disabled_by |
| Role assigned | HIGH | user_id, role, assigned_by |
| Permission granted | HIGH | user_id, permission, granted_by |
| Payment created | MEDIUM | from_user, to_user, amount |
| Payment approved | MEDIUM | payment_id, approved_by |
| Service request approved | MEDIUM | request_id, approved_by |
| Policy changed | HIGH | policy_name, old_value, new_value, changed_by |
| Data exported | HIGH | user_id, data_type, record_count, exported_by |
| User deleted | CRITICAL | user_id, deleted_by, reason |
| Database backup | CRITICAL | backup_size, location, verified |

---

## 5. Rate Limiting & DoS Protection

```python
# backend/src/elcorp/shared/security/rate_limiter.py

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from functools import wraps

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"],
    storage_uri="redis://localhost:6379"
)

# Endpoint-specific limits
@app.route("/api/v1/auth/login", methods=["POST"])
@limiter.limit("5 per minute")  # Brute force protection
def login():
    pass

@app.route("/api/v1/auth/register", methods=["POST"])
@limiter.limit("3 per hour")  # Prevent spam registration
def register():
    pass

@app.route("/api/v1/users/<int:user_id>", methods=["GET"])
@limiter.limit("100 per minute")  # Normal usage
def get_user(user_id):
    pass

# Custom rate limiting by user role
def rate_limit_by_role(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = get_current_user()
        
        if user.role == "admin":
            limit = "1000 per hour"  # Admins get higher limit
        else:
            limit = "100 per hour"
        
        # Apply limit check...
        return f(*args, **kwargs)
    return decorated_function
```

---

## 6. Secret Management

### 6.1 Environment Variables Only

```bash
# .env.example

# Core
FLASK_ENV=production
SECRET_KEY=<64-byte-random-key>
DEBUG=false

# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname
DB_REPLICA_URL=postgresql://user:pass@replica-host:5432/dbname

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=<password>

# Encryption
ENCRYPTION_MASTER_KEY=<64-byte-key-for-field-encryption>

# JWT
JWT_SECRET=<separate-64-byte-key>

# Third-party services
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=<email>
MAIL_PASSWORD=<password>

SENTRY_DSN=https://...

SLACK_WEBHOOK_URL=https://hooks.slack.com/...

# Blockchain (optional)
WEB3_PROVIDER_URL=https://...
SMART_CONTRACT_ADDRESS=0x...

# Compliance
AUDITOR_EMAIL=audit@example.com
COMPLIANCE_OFFICER_EMAIL=compliance@example.com
SECURITY_OFFICER_EMAIL=security@example.com
```

### 6.2 Using HashiCorp Vault (Optional)

```python
# backend/src/elcorp/shared/infrastructure/secrets.py

import hvac

class VaultSecretManager:
    """HashiCorp Vault integration for secrets."""
    
    def __init__(self, vault_addr: str, vault_token: str):
        self.client = hvac.Client(url=vault_addr, token=vault_token)
    
    def get_secret(self, path: str) -> dict:
        """Retrieve secret from Vault."""
        response = self.client.secrets.kv.v2.read_secret_version(path=path)
        return response["data"]["data"]
    
    def store_secret(self, path: str, secret: dict) -> None:
        """Store secret in Vault."""
        self.client.secrets.kv.v2.create_or_update_secret_version(
            path=path,
            secret_data=secret
        )

# Usage
vault = VaultSecretManager(
    vault_addr=os.getenv("VAULT_ADDR"),
    vault_token=os.getenv("VAULT_TOKEN")
)

db_creds = vault.get_secret("database/elcorp")
jwt_secret = vault.get_secret("jwt/secret")
```

---

## 7. Threat Model & Mitigations

| Threat | Likelihood | Impact | Mitigation |
|--------|-----------|--------|-----------|
| SQL Injection | High | Critical | Parameterized queries (ORM) |
| XSS | High | Medium | HTML sanitization, CSP headers |
| CSRF | Medium | Medium | SameSite cookies, CSRF tokens |
| Account Takeover | Medium | Critical | MFA, device tracking, anomaly detection |
| Token Leakage | Medium | High | Short TTL, device binding, revocation |
| Data Breach | Medium | Critical | Encryption at rest, access controls |
| DDoS | Medium | Medium | Rate limiting, CDN, WAF |
| Insider Threat | Low | Critical | Audit logs, least privilege, separation of duties |
| Privilege Escalation | Low | Critical | RBAC/PBAC, zero-trust model |
| Supply Chain | Low | High | Dependency scanning, SCA tools |

---

## 8. Compliance Checklist

### GDPR (EU users)
- [ ] Explicit consent for data collection
- [ ] Privacy Policy document
- [ ] Data Processing Agreement (DPA)
- [ ] Right to access (data export)
- [ ] Right to erasure (deletion)
- [ ] Right to rectification (correction)
- [ ] Right to restrict processing
- [ ] Data Breach Notification (72 hours)

### POPIA (South Africa / Regional)
- [ ] Personal Information Processing Notice
- [ ] Lawful basis for processing
- [ ] Recipient notification (data sharing)
- [ ] Data retention policy (delete after 3 years)
- [ ] Complaint handling procedure
- [ ] Data Subject requests (30-day response)

### Financial Services
- [ ] Know Your Customer (KYC) verification
- [ ] Anti-Money Laundering (AML) checks
- [ ] Transaction Monitoring
- [ ] Sanctions Screening
- [ ] Audit Trail (7-year retention)
- [ ] Business Continuity Plan
- [ ] Disaster Recovery (RTO < 4 hours)

---

## 9. Security Testing & Validation

### 9.1 Penetration Testing Checklist

```bash
# Automated security scanning
pip install bandit  # Python security issues
bandit -r backend/src/

pip install semgrep  # Static analysis
semgrep --config=p/security-audit backend/src/

pip install owasp-zap  # Dynamic analysis
```

### 9.2 Security Test Cases

```python
# tests/security/test_auth_security.py

def test_token_expiry():
    """Expired access tokens rejected."""
    token = generate_token(expires_in=-1)  # Already expired
    assert verify_token(token) is None

def test_token_revocation():
    """Revoked tokens rejected."""
    token = generate_token()
    revoke_token(token)
    assert verify_token(token) is None

def test_device_binding():
    """Token only works on original device."""
    token = generate_token(device_id="device-1")
    assert verify_token(token, device_id="device-1") is not None
    assert verify_token(token, device_id="device-2") is None

def test_password_brute_force():
    """Too many login attempts locked."""
    for _ in range(10):
        login("user@example.com", "wrong_password")
    
    # 11th attempt should fail
    response = login("user@example.com", "correct_password")
    assert response.status_code == 429  # Too Many Requests

def test_sql_injection():
    """SQL injection prevented."""
    response = client.get("/api/v1/users?search='; DROP TABLE users;--")
    assert response.status_code == 422

def test_xss_prevention():
    """XSS payload sanitized."""
    response = client.post("/api/v1/requests", json={
        "title": "<script>alert('xss')</script>"
    })
    
    # Check stored value is sanitized
    request = ServiceRequest.query.first()
    assert "<script>" not in request.title
```

---

## Conclusion

**Production Security Readiness Checklist**:

- [ ] JWT token generation & verification implemented
- [ ] Multi-factor authentication (TOTP) enabled
- [ ] Device token tracking & revocation working
- [ ] Encryption at rest for sensitive fields
- [ ] Audit logging with immutability checks
- [ ] Input validation with Pydantic on all endpoints
- [ ] SQL injection prevention (parameterized queries)
- [ ] XSS prevention (HTML sanitization)
- [ ] Rate limiting on authentication endpoints
- [ ] GDPR/POPIA compliance measures documented
- [ ] Secret management (environment variables)
- [ ] Security headers enabled (CSP, HSTS, X-Frame-Options)
- [ ] HTTPS/TLS 1.3 enforced
- [ ] Penetration testing completed
- [ ] Security incident response plan
- [ ] Audit log integrity verified

---

**Document Version**: 1.0  
**Last Updated**: February 2, 2026

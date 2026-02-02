# Elcorp Namibia: Production-Grade Architecture Document

**Version**: 2.0  
**Status**: Architectural Review & Refactoring Plan  
**Target**: National-Scale Fintech Platform  
**Last Updated**: February 2, 2026

---

## Executive Summary

This document outlines the transformation of Elcorp Namibia into a production-grade, scalable fintech platform suitable for national deployment and regulatory audit. The architecture follows **Domain-Driven Design (DDD)** principles with a **Hexagonal (Ports & Adapters)** pattern to ensure:

- **Separation of Concerns**: Domain logic decoupled from framework, database, and presentation
- **Testability**: Unit tests without database or Flask context
- **Scalability**: Stateless services, background jobs, caching, and horizontal scaling
- **Auditability**: Immutable audit trails, compliance tracking, soft deletes
- **Security**: JWT authentication, RBAC/PBAC, input validation, encrypted secrets
- **Compliance**: Financial regulatory alignment, tamper-proof logging, SOC 2 readiness

---

## Part 1: Architecture Overview

### 1.1 Design Paradigm: Domain-Driven Design (DDD)

Elcorp Namibia operates across **four bounded contexts**:

```
┌─────────────────────────────────────────────────────────────┐
│                    API Gateway / Load Balancer               │
└────────────┬────────────────────────┬───────────────────────┘
             │                        │
        ┌────▼────────┐   ┌──────────▼──────┐
        │   Identity   │   │    Payments     │
        │  Bounded     │   │   Bounded       │
        │  Context     │   │   Context       │
        └────┬────────┘   └────────┬────────┘
             │                     │
        ┌────▼──────────┐   ┌──────▼─────────┐
        │ Governance    │   │  Compliance    │
        │ Bounded       │   │  Bounded       │
        │ Context       │   │  Context       │
        └───────────────┘   └────────────────┘

       ┌─────────────────────────────────────┐
       │  Shared Kernel (Audit, Events, etc) │
       └─────────────────────────────────────┘

       ┌─────────────────────────────────────┐
       │  Infrastructure (DB, Cache, Jobs)   │
       └─────────────────────────────────────┘
```

### 1.2 Bounded Contexts

#### **Identity Context** (elcorp.identity)
- User registration, authentication, profile management
- Device tracking and session management
- 2FA/MFA flows
- Password reset and recovery
- Wallet address generation and management

#### **Payments Context** (elcorp.payments)
- VIN registry and vehicle ownership tracking
- Token transfers and balances
- Payment processing and reconciliation
- Invoice and receipt generation
- Transaction history and settlement

#### **Governance Context** (elcorp.governance)
- Role and permission management (RBAC)
- Policy-based access control (PBAC)
- Service request workflows
- Approval hierarchies
- Team and organization management

#### **Compliance Context** (elcorp.compliance)
- Audit log generation and archival
- Data retention and purging policies
- Regulatory reporting
- Service-Level Agreement (SLA) tracking
- Incident and risk management

### 1.3 Hexagonal Architecture (Ports & Adapters)

Each bounded context follows this layered structure:

```
┌───────────────────────────────────────────────────────────┐
│                   PRESENTATION LAYER                      │
│  (REST Controllers / FastAPI Endpoints / GraphQL)         │
│  Responsibility: Route requests, serialize responses      │
└──────────────────┬────────────────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────────────────┐
│              APPLICATION SERVICE LAYER                    │
│  (Use Cases / Orchestration / Request Handling)           │
│  Responsibility: Coordinate domain logic, transaction mgmt│
└──────────────────┬────────────────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────────────────┐
│                DOMAIN LOGIC LAYER (Core)                  │
│  (Entities / Aggregates / Domain Services / Value Objects)│
│  Responsibility: Business rules, validation, invariants   │
└──────────────────┬────────────────────────────────────────┘
                   │
┌──────────────────▼────────────────────────────────────────┐
│          INFRASTRUCTURE & PERSISTENCE LAYER               │
│  (Repositories / Ports / Adapters)                        │
│  Responsibility: Database, cache, external APIs, events   │
└───────────────────────────────────────────────────────────┘
```

**Key Principle**: Domain layer MUST NOT import Flask, SQLAlchemy, or HTTP libraries.

---

## Part 2: Project Structure

### 2.1 Recommended Folder Hierarchy

```
elcorp-namibia/
│
├── README.md                          # Technical product overview
├── CONTRIBUTING.md                    # Contribution guidelines
├── SECURITY.md                        # Security policy
├── LICENSE                            # Open source license
│
├── infrastructure/                    # IaC and deployment
│   ├── docker/
│   │   ├── Dockerfile.backend
│   │   ├── Dockerfile.frontend
│   │   └── docker-compose.yml
│   ├── kubernetes/                    # K8s manifests (optional)
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   └── ingress.yaml
│   ├── terraform/                     # Or Bicep for Azure
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── github/
│       └── workflows/
│           ├── ci.yml
│           ├── cd.yml
│           └── security-scan.yml
│
├── backend/                           # Python Flask API
│   ├── pyproject.toml                 # Modern Python project definition
│   ├── requirements.txt
│   ├── setup.py
│   ├── pytest.ini
│   ├── .env.example
│   │
│   ├── src/
│   │   └── elcorp/
│   │       │
│   │       ├── __init__.py
│   │       ├── config.py              # App configuration
│   │       ├── main.py                # App factory
│   │       │
│   │       ├── shared/                # Shared kernel
│   │       │   ├── __init__.py
│   │       │   ├── domain/
│   │       │   │   ├── events.py      # Domain events
│   │       │   │   ├── value_objects.py
│   │       │   │   └── exceptions.py  # Domain-level exceptions
│   │       │   ├── infrastructure/
│   │       │   │   ├── database.py    # DB setup
│   │       │   │   ├── cache.py       # Redis client
│   │       │   │   ├── messaging.py   # Event publisher
│   │       │   │   └── secrets.py     # Secret management
│   │       │   ├── security/
│   │       │   │   ├── jwt_handler.py
│   │       │   │   ├── password.py
│   │       │   │   ├── encryption.py
│   │       │   │   └── rate_limiter.py
│   │       │   └── util/
│   │       │       ├── logger.py
│   │       │       ├── validators.py
│   │       │       └── pagination.py
│   │       │
│   │       ├── identity/              # Bounded Context 1
│   │       │   ├── __init__.py
│   │       │   ├── domain/            # Domain layer (no frameworks)
│   │       │   │   ├── models.py      # User aggregate, entities
│   │       │   │   ├── repositories.py # Repository interfaces
│   │       │   │   ├── services.py    # Domain services
│   │       │   │   ├── events.py      # Identity-specific events
│   │       │   │   └── exceptions.py  # Identity-specific exceptions
│   │       │   ├── application/       # Use cases / orchestration
│   │       │   │   ├── __init__.py
│   │       │   │   ├── dto.py         # Data Transfer Objects
│   │       │   │   ├── commands.py    # Command handlers
│   │       │   │   ├── queries.py     # Query handlers
│   │       │   │   ├── services.py    # Application services
│   │       │   │   └── mappers.py     # Domain ↔ DTO mappers
│   │       │   ├── infrastructure/    # Adapters
│   │       │   │   ├── __init__.py
│   │       │   │   ├── persistence/
│   │       │   │   │   ├── models.py  # SQLAlchemy models
│   │       │   │   │   ├── repositories.py
│   │       │   │   │   └── migrations/
│   │       │   │   └── external/
│   │       │   │       └── services.py # Email, SMS, etc
│   │       │   └── interfaces/        # API layer
│   │       │       ├── __init__.py
│   │       │       ├── http/
│   │       │   │   ├── routes.py      # Flask blueprints
│   │       │   │   ├── handlers.py    # HTTP request handlers
│   │       │   │   ├── validators.py  # Pydantic request validators
│   │       │   │   └── openapi.py     # OpenAPI specs
│   │       │       └── ws/            # WebSocket routes (optional)
│   │       │           └── handlers.py
│   │       │
│   │       ├── payments/              # Bounded Context 2
│   │       │   └── [same structure as identity]
│   │       │
│   │       ├── governance/            # Bounded Context 3
│   │       │   └── [same structure as identity]
│   │       │
│   │       ├── compliance/            # Bounded Context 4
│   │       │   └── [same structure as identity]
│   │       │
│   │       └── jobs/                  # Background jobs
│   │           ├── __init__.py
│   │           ├── celery_app.py
│   │           ├── tasks.py
│   │           └── handlers.py
│   │
│   ├── migrations/                    # Alembic migration versions
│   │   ├── alembic.ini
│   │   └── versions/
│   │
│   └── tests/
│       ├── conftest.py
│       ├── unit/                      # Unit tests (no DB)
│       │   ├── test_identity_domain.py
│       │   ├── test_payment_domain.py
│       │   └── ...
│       ├── integration/               # Integration tests (with DB)
│       │   ├── test_identity_api.py
│       │   ├── test_payment_api.py
│       │   └── ...
│       ├── security/                  # Security tests
│       │   ├── test_auth.py
│       │   ├── test_injection.py
│       │   └── ...
│       └── fixtures/
│           ├── conftest.py
│           └── factories.py            # Test data factories
│
├── frontend/                          # React + TypeScript (existing)
│   ├── src/
│   ├── package.json
│   └── ...
│
├── docs/                              # Documentation
│   ├── API.md                         # OpenAPI specification (manual or Swagger)
│   ├── ARCHITECTURE.md                # High-level design
│   ├── DATABASE_SCHEMA.md             # ER diagram and normalization
│   ├── SECURITY.md                    # Threat model, controls
│   ├── DEPLOYMENT.md                  # Deployment procedures
│   ├── OPERATIONS.md                  # Runbooks, monitoring
│   └── COMPLIANCE.md                  # Regulatory alignment
│
└── scripts/
    ├── init_db.py                     # Database initialization
    ├── seed_roles.py                  # Seed RBAC roles
    ├── create_admin.py                # Create admin user
    └── backup_db.sh                   # Database backup script
```

### 2.2 Key Principles

1. **No Framework Leakage**: Domain layer imports ONLY from `shared.domain` and Python stdlib
2. **Dependency Inversion**: Domain → Application → Infrastructure (never reverse)
3. **Interface-Based Design**: Infrastructure implements domain repository interfaces
4. **Separation of Models**: SQLAlchemy models ≠ Domain models (use mappers)
5. **Clear Naming**: Suffixes indicate layer (e.g., `UserRepository` interface, `UserSQLAlchemyRepository` implementation)

---

## Part 3: Backend Hardening Strategy

### 3.1 Authentication & Authorization

#### **JWT + Refresh Token Pattern**

```python
# src/elcorp/shared/security/jwt_handler.py

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
import uuid

@dataclass
class TokenPair:
    access_token: str
    refresh_token: str
    expires_in: int

class JWTHandler:
    """Centralized JWT token management."""
    
    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_ttl = timedelta(minutes=15)
        self.refresh_token_ttl = timedelta(days=7)
    
    def generate_access_token(
        self,
        user_id: int,
        role: str,
        device_id: Optional[str] = None,
    ) -> str:
        """Generate 15-minute access token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "role": role,
            "type": "access",
            "device_id": device_id,
            "iat": now,
            "exp": now + self.access_token_ttl,
            "jti": str(uuid.uuid4()),  # JWT ID for revocation
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def generate_refresh_token(
        self,
        user_id: int,
        device_id: Optional[str] = None,
    ) -> str:
        """Generate 7-day refresh token."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(user_id),
            "type": "refresh",
            "device_id": device_id,
            "iat": now,
            "exp": now + self.refresh_token_ttl,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
    
    def verify_token(self, token: str, token_type: str = "access") -> dict:
        """
        Verify JWT and return payload.
        
        Raises:
            jwt.ExpiredSignatureError
            jwt.InvalidTokenError
        """
        payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
        
        if payload.get("type") != token_type:
            raise jwt.InvalidTokenError("Invalid token type")
        
        return payload
    
    def revoke_token(self, jti: str) -> None:
        """Add token to revocation blacklist (Redis)."""
        # Implementation uses Redis with TTL
        pass
```

#### **Role-Based Access Control (RBAC)**

```python
# src/elcorp/shared/domain/exceptions.py

class AccessDeniedException(Exception):
    """Raised when user lacks required permission."""
    pass

# src/elcorp/shared/infrastructure/rbac.py

from enum import Enum
from typing import Callable, Set

class Role(Enum):
    ADMIN = "admin"
    STAFF = "staff"
    USER = "user"
    GUEST = "guest"

class Permission(Enum):
    # Identity permissions
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    
    # Payment permissions
    PAYMENT_CREATE = "payment:create"
    PAYMENT_APPROVE = "payment:approve"
    PAYMENT_RECONCILE = "payment:reconcile"
    
    # Governance permissions
    ROLE_MANAGE = "role:manage"
    POLICY_MANAGE = "policy:manage"
    
    # Compliance permissions
    AUDIT_VIEW = "audit:view"
    AUDIT_EXPORT = "audit:export"
    REPORT_GENERATE = "report:generate"

# Role → Permission mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.ADMIN: set(Permission),  # All permissions
    Role.STAFF: {
        Permission.USER_READ,
        Permission.PAYMENT_CREATE,
        Permission.PAYMENT_APPROVE,
        Permission.AUDIT_VIEW,
    },
    Role.USER: {
        Permission.USER_READ,
        Permission.PAYMENT_CREATE,
    },
    Role.GUEST: set(),
}

def require_permission(permission: Permission) -> Callable:
    """Flask decorator to enforce permission."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated(*args, **kwargs):
            user = get_current_user()  # From Flask context
            if not has_permission(user.role, permission):
                raise AccessDeniedException(f"Missing {permission.value}")
            return f(*args, **kwargs)
        return decorated
    return decorator
```

#### **Policy-Based Access Control (PBAC)**

```python
# src/elcorp/compliance/domain/policies.py

from abc import ABC, abstractmethod
from dataclasses import dataclass

@dataclass
class PolicyContext:
    """Context for policy evaluation."""
    user_id: int
    resource_type: str
    resource_id: int
    action: str
    timestamp: datetime

class AccessPolicy(ABC):
    """Base class for access policies."""
    
    @abstractmethod
    def evaluate(self, context: PolicyContext) -> bool:
        """Return True if access is allowed."""
        pass

class TimeBasedPolicy(AccessPolicy):
    """Only allow access during business hours."""
    
    def evaluate(self, context: PolicyContext) -> bool:
        hour = context.timestamp.hour
        return 9 <= hour < 17  # 9 AM to 5 PM

class DataClassificationPolicy(AccessPolicy):
    """Only admins can view classified data."""
    
    def evaluate(self, context: PolicyContext) -> bool:
        if context.action == "view" and context.resource_type == "classified_document":
            # Fetch user role from database
            user = User.query.get(context.user_id)
            return user.role.name == "admin"
        return True
```

### 3.2 Input Validation Using Pydantic

```python
# src/elcorp/identity/application/dto.py

from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional
from datetime import datetime

class CreateUserRequest(BaseModel):
    """DTO for user creation endpoint."""
    
    full_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=12)
    phone: str = Field(..., pattern=r"^\+?[0-9]{7,20}$")
    organization: Optional[str] = Field(None, max_length=100)
    agreed_terms: bool
    
    @validator("password")
    def validate_password_strength(cls, v: str) -> str:
        """Enforce password complexity requirements."""
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        if not any(c in "!@#$%^&*" for c in v):
            raise ValueError("Password must contain special character")
        return v
    
    @validator("agreed_terms")
    def validate_terms(cls, v: bool) -> bool:
        if not v:
            raise ValueError("Must agree to terms and conditions")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "full_name": "John Doe",
                "email": "john@example.com",
                "password": "SecurePass123!",
                "phone": "+264811234567",
                "organization": "Example Corp",
                "agreed_terms": True,
            }
        }

class UserResponse(BaseModel):
    """DTO for user response (no password)."""
    
    id: int
    full_name: str
    email: EmailStr
    phone: str
    organization: Optional[str]
    role: str
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True  # For SQLAlchemy compatibility
```

### 3.3 Centralized Error Handling

```python
# src/elcorp/shared/infrastructure/error_handler.py

from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)

class ErrorCode(Enum):
    """Standardized error codes for API responses."""
    AUTH_INVALID_CREDENTIALS = "AUTH_001"
    AUTH_EXPIRED_TOKEN = "AUTH_002"
    AUTH_INVALID_TOKEN = "AUTH_003"
    AUTH_MISSING_TOKEN = "AUTH_004"
    
    VALIDATION_ERROR = "VAL_001"
    
    RESOURCE_NOT_FOUND = "RES_001"
    RESOURCE_ALREADY_EXISTS = "RES_002"
    
    ACCESS_DENIED = "ACC_001"
    
    INTERNAL_SERVER_ERROR = "SRV_001"

@dataclass
class APIError:
    """Standardized error response."""
    code: ErrorCode
    message: str
    details: Optional[Any] = None
    status_code: int = 400
    
    def to_dict(self) -> dict:
        return {
            "error": {
                "code": self.code.value,
                "message": self.message,
                "details": self.details,
            }
        }

class ErrorHandler:
    """Centralized error handling and logging."""
    
    @staticmethod
    def handle_exception(exc: Exception, context: dict = None) -> APIError:
        """Convert exception to standardized API error."""
        
        if isinstance(exc, ValidationError):  # Pydantic
            logger.warning(f"Validation error: {exc.errors()}")
            return APIError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Validation failed",
                details=exc.errors(),
                status_code=422,
            )
        
        if isinstance(exc, AccessDeniedException):
            logger.warning(f"Access denied for context: {context}")
            return APIError(
                code=ErrorCode.ACCESS_DENIED,
                message="Access denied",
                status_code=403,
            )
        
        # Log unexpected errors
        logger.exception(f"Unhandled exception: {exc}")
        return APIError(
            code=ErrorCode.INTERNAL_SERVER_ERROR,
            message="Internal server error",
            status_code=500,
        )
```

### 3.4 Audit Logging & Compliance

```python
# src/elcorp/shared/infrastructure/audit.py

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Optional
import json
from sqlalchemy import Column, Integer, String, DateTime, Text

class AuditAction(Enum):
    """Actions subject to audit logging."""
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    PASSWORD_CHANGE = "password_change"
    PAYMENT_CREATE = "payment_create"
    PAYMENT_APPROVE = "payment_approve"
    POLICY_CHANGE = "policy_change"
    REPORT_GENERATE = "report_generate"

@dataclass
class AuditLog:
    """Immutable audit log entry."""
    action: AuditAction
    user_id: int
    resource_type: str
    resource_id: Optional[int]
    changes: dict  # Before/after values
    timestamp: datetime
    ip_address: str
    user_agent: str
    
    def to_json(self) -> str:
        """Serialize to JSON for tamper-proof storage."""
        return json.dumps({
            "action": self.action.value,
            "user_id": self.user_id,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "changes": self.changes,
            "timestamp": self.timestamp.isoformat(),
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
        })

class AuditLogger:
    """Service for logging security-relevant events."""
    
    def __init__(self, db_session, cache):
        self.db = db_session
        self.cache = cache
    
    def log(self, log_entry: AuditLog) -> None:
        """
        Persist audit log entry.
        
        Strategy:
        1. Write to database (immutable append)
        2. Write to cache for real-time monitoring
        3. Periodically sync to immutable storage (S3, blockchain, etc.)
        """
        # Store in DB
        audit_record = AuditLogModel(
            action=log_entry.action.value,
            user_id=log_entry.user_id,
            resource_type=log_entry.resource_type,
            resource_id=log_entry.resource_id,
            changes=log_entry.to_json(),
            timestamp=log_entry.timestamp,
            ip_address=log_entry.ip_address,
        )
        self.db.add(audit_record)
        self.db.commit()
        
        # Store in cache for alerting
        key = f"audit:{log_entry.action.value}:{log_entry.timestamp.timestamp()}"
        self.cache.setex(key, 86400, log_entry.to_json())
        
        # Alert on suspicious activity
        if self._is_suspicious(log_entry):
            self._trigger_alert(log_entry)
    
    def _is_suspicious(self, log_entry: AuditLog) -> bool:
        """Detect anomalies."""
        # Example: Multiple failed logins from same IP
        return False  # Implement threat detection
    
    def _trigger_alert(self, log_entry: AuditLog) -> None:
        """Send alert to security team."""
        # Send to Sentry, Slack, email, etc.
        pass
```

---

## Part 4: Database & Data Integrity

### 4.1 Normalized PostgreSQL Schema

#### **Identity Context Schema**

```sql
-- Users and authentication
CREATE TABLE "user" (
    id SERIAL PRIMARY KEY,
    username VARCHAR(64) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(100) NOT NULL,
    organization_id INTEGER REFERENCES organization(id),
    wallet_address UUID UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP, -- Soft delete
    -- Indexes
    CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}$'),
    CHECK (length(password_hash) > 0)
);

CREATE INDEX idx_user_email ON "user"(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_user_username ON "user"(username) WHERE deleted_at IS NULL;
CREATE INDEX idx_user_wallet ON "user"(wallet_address);
CREATE INDEX idx_user_organization ON "user"(organization_id);

-- Device tracking for multi-device auth
CREATE TABLE device_token (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    device_id UUID NOT NULL,
    device_name VARCHAR(100),
    refresh_token TEXT NOT NULL,
    user_agent TEXT,
    ip_address INET,
    last_used_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL,
    is_revoked BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, device_id)
);

CREATE INDEX idx_device_token_user ON device_token(user_id);
CREATE INDEX idx_device_token_expires ON device_token(expires_at) WHERE NOT is_revoked;

-- Password history to prevent reuse
CREATE TABLE password_history (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    password_hash VARCHAR(255) NOT NULL,
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_password_history_user ON password_history(user_id);

-- Two-factor authentication
CREATE TABLE two_factor_auth (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    secret_key VARCHAR(32), -- Encrypted in production
    enabled BOOLEAN DEFAULT FALSE,
    backup_codes TEXT[],     -- Encrypted in production
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### **Payments Context Schema**

```sql
CREATE TABLE vin_registry (
    id SERIAL PRIMARY KEY,
    vin VARCHAR(17) UNIQUE NOT NULL,
    owner_id INTEGER NOT NULL REFERENCES "user"(id),
    vehicle_data JSONB,  -- Make, model, year, etc.
    token_balance NUMERIC(20, 8) NOT NULL DEFAULT 0,
    registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    deleted_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_vin_registry_vin ON vin_registry(vin) WHERE deleted_at IS NULL;
CREATE INDEX idx_vin_registry_owner ON vin_registry(owner_id);
CREATE INDEX idx_vin_registry_active ON vin_registry(is_active) WHERE deleted_at IS NULL;

CREATE TABLE transaction (
    id SERIAL PRIMARY KEY,
    from_user_id INTEGER REFERENCES "user"(id),
    to_user_id INTEGER NOT NULL REFERENCES "user"(id),
    amount NUMERIC(20, 8) NOT NULL,
    currency VARCHAR(3) DEFAULT 'XOF', -- West African CFA franc or NAD
    status VARCHAR(32) NOT NULL DEFAULT 'pending', -- pending, completed, failed
    transaction_hash VARCHAR(255), -- Blockchain reference
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSONB
);

CREATE INDEX idx_transaction_from ON transaction(from_user_id);
CREATE INDEX idx_transaction_to ON transaction(to_user_id);
CREATE INDEX idx_transaction_status ON transaction(status);
CREATE INDEX idx_transaction_created ON transaction(created_at DESC);
```

#### **Governance Context Schema**

```sql
CREATE TABLE role (
    id SERIAL PRIMARY KEY,
    name VARCHAR(64) UNIQUE NOT NULL,
    description TEXT,
    is_system_role BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO role (name, description, is_system_role) VALUES
('admin', 'System administrator', TRUE),
('staff', 'Compliance officer or support staff', TRUE),
('user', 'Regular user', TRUE),
('guest', 'Unauthenticated visitor', TRUE);

CREATE TABLE user_role (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES role(id) ON DELETE RESTRICT,
    assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    assigned_by INTEGER REFERENCES "user"(id),
    UNIQUE(user_id, role_id)
);

CREATE TABLE permission (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    category VARCHAR(32), -- auth, payment, governance, compliance
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE role_permission (
    id SERIAL PRIMARY KEY,
    role_id INTEGER NOT NULL REFERENCES role(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permission(id) ON DELETE CASCADE,
    UNIQUE(role_id, permission_id)
);

CREATE TABLE service_request (
    id SERIAL PRIMARY KEY,
    requester_id INTEGER NOT NULL REFERENCES "user"(id),
    assigned_to INTEGER REFERENCES "user"(id),
    category VARCHAR(64) NOT NULL,
    status VARCHAR(32) DEFAULT 'draft',
    priority VARCHAR(32) DEFAULT 'normal',
    title VARCHAR(255) NOT NULL,
    description TEXT,
    sla_deadline TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    deleted_at TIMESTAMP
);

CREATE INDEX idx_service_request_requester ON service_request(requester_id);
CREATE INDEX idx_service_request_assigned ON service_request(assigned_to);
CREATE INDEX idx_service_request_status ON service_request(status);
CREATE INDEX idx_service_request_priority ON service_request(priority);
```

#### **Compliance Context Schema**

```sql
CREATE TABLE audit_log (
    id BIGSERIAL PRIMARY KEY,
    action VARCHAR(100) NOT NULL,
    user_id INTEGER REFERENCES "user"(id),
    resource_type VARCHAR(64),
    resource_id INTEGER,
    changes JSONB NOT NULL, -- Before/after values
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    -- Immutable: no UPDATE or DELETE allowed
    CHECK (timestamp <= CURRENT_TIMESTAMP)
);

CREATE INDEX idx_audit_log_user ON audit_log(user_id);
CREATE INDEX idx_audit_log_action ON audit_log(action);
CREATE INDEX idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp DESC);

-- Prevent updates/deletes on audit logs
CREATE OR REPLACE FUNCTION audit_log_immutable() RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Audit logs are immutable';
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER audit_log_update_trigger
BEFORE UPDATE ON audit_log
FOR EACH ROW
EXECUTE FUNCTION audit_log_immutable();

CREATE TRIGGER audit_log_delete_trigger
BEFORE DELETE ON audit_log
FOR EACH ROW
EXECUTE FUNCTION audit_log_immutable();

CREATE TABLE sla_policy (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    category VARCHAR(64),
    priority VARCHAR(32),
    response_time_hours INTEGER,
    resolution_time_hours INTEGER,
    escalation_after_hours INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE incident_log (
    id SERIAL PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    severity VARCHAR(32), -- low, medium, high, critical
    status VARCHAR(32) DEFAULT 'open', -- open, investigating, resolved
    reported_by INTEGER REFERENCES "user"(id),
    assigned_to INTEGER REFERENCES "user"(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP,
    root_cause TEXT,
    remediation TEXT
);

CREATE INDEX idx_incident_log_severity ON incident_log(severity);
CREATE INDEX idx_incident_log_status ON incident_log(status);
CREATE INDEX idx_incident_log_created ON incident_log(created_at DESC);
```

### 4.2 Alembic Migration Strategy

```python
# migrations/versions/0001_init_schema.py

"""Initial schema for identity, payments, governance, compliance contexts.

Revision ID: 0001
Create Date: 2026-02-01 10:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    # Create all tables (see above SQL)
    pass

def downgrade():
    # Drop all tables
    pass

# Naming convention for constraints
naming_convention = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s"
}
```

### 4.3 Soft Deletes & Data Retention

```python
# src/elcorp/shared/domain/base.py

from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property

Base = declarative_base()

class SoftDeleteMixin:
    """Mixin for soft-deletable entities."""
    
    deleted_at = Column(DateTime, nullable=True, default=None)
    
    @hybrid_property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None
    
    def soft_delete(self) -> None:
        """Mark as deleted without removing data."""
        self.deleted_at = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore a soft-deleted record."""
        self.deleted_at = None

class AuditMixin:
    """Mixin for audit timestamps."""
    
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
```

---

## Part 5: API Design Standards

### 5.1 RESTful Conventions

**Endpoint Patterns**:

```
GET    /api/v1/users              → List users (paginated)
GET    /api/v1/users/:id          → Get user details
POST   /api/v1/users              → Create user
PUT    /api/v1/users/:id          → Full update user
PATCH  /api/v1/users/:id          → Partial update user
DELETE /api/v1/users/:id          → Delete (soft) user

GET    /api/v1/users/:id/profile  → Get user profile
PATCH  /api/v1/users/:id/password → Change password

POST   /api/v1/auth/login         → Login
POST   /api/v1/auth/logout        → Logout
POST   /api/v1/auth/refresh       → Refresh token
POST   /api/v1/auth/register      → Register
```

### 5.2 Response Format

```python
# src/elcorp/shared/infrastructure/response.py

from dataclasses import dataclass
from typing import Optional, Any, List
from enum import Enum

class HTTPStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    VALIDATION_ERROR = "validation_error"

@dataclass
class APIResponse:
    """Standardized API response wrapper."""
    status: HTTPStatus
    data: Optional[Any] = None
    error: Optional[str] = None
    errors: Optional[List[dict]] = None  # For validation
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "data": self.data,
            "error": self.error,
            "errors": self.errors,
            "timestamp": self.timestamp,
        }

# Success response
{
    "status": "success",
    "data": {
        "id": 1,
        "email": "john@example.com",
        "role": "user"
    },
    "timestamp": "2026-02-01T10:00:00Z"
}

# Error response
{
    "status": "error",
    "error": "User not found",
    "timestamp": "2026-02-01T10:00:00Z"
}

# Validation error response
{
    "status": "validation_error",
    "errors": [
        {
            "field": "email",
            "message": "Invalid email format"
        }
    ],
    "timestamp": "2026-02-01T10:00:00Z"
}
```

### 5.3 OpenAPI/Swagger Specification

```yaml
# docs/openapi.yaml

openapi: 3.0.0
info:
  title: Elcorp Namibia API
  description: Fintech platform for identity, payments, and governance
  version: 1.0.0
  license:
    name: Apache 2.0

servers:
  - url: https://api.elcorp.na/api/v1
    description: Production
  - url: https://staging-api.elcorp.na/api/v1
    description: Staging
  - url: http://localhost:8000/api/v1
    description: Development

components:
  securitySchemes:
    BearerToken:
      type: http
      scheme: bearer
      bearerFormat: JWT

  schemas:
    User:
      type: object
      properties:
        id:
          type: integer
        email:
          type: string
          format: email
        full_name:
          type: string
        role:
          type: string
          enum: [admin, staff, user]
        created_at:
          type: string
          format: date-time
    
    LoginRequest:
      type: object
      required: [email, password, device_id]
      properties:
        email:
          type: string
          format: email
        password:
          type: string
        device_id:
          type: string
          format: uuid

paths:
  /auth/login:
    post:
      tags: [Authentication]
      summary: Authenticate user and return tokens
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/LoginRequest'
      responses:
        '200':
          description: Login successful
          content:
            application/json:
              schema:
                type: object
                properties:
                  access_token:
                    type: string
                  refresh_token:
                    type: string
                  expires_in:
                    type: integer
        '401':
          description: Invalid credentials
        '422':
          description: Validation error

  /users:
    get:
      tags: [Users]
      summary: List users
      security:
        - BearerToken: []
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            default: 1
        - name: per_page
          in: query
          schema:
            type: integer
            default: 20
      responses:
        '200':
          description: User list
        '401':
          description: Unauthorized

    post:
      tags: [Users]
      summary: Create new user
      requestBody:
        required: true
        content:
          application/json:
            schema:
              $ref: '#/components/schemas/User'
      responses:
        '201':
          description: User created
        '422':
          description: Validation error
```

---

## Part 6: Scalability & Performance

### 6.1 Caching Strategy (Redis)

```python
# src/elcorp/shared/infrastructure/cache.py

import redis
from functools import wraps
from typing import Optional, Any, Callable
import json

class CacheManager:
    """Centralized cache management using Redis."""
    
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.default_ttl = 3600  # 1 hour
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        value = self.redis.get(key)
        if value:
            return json.loads(value)
        return None
    
    def set(self, key: str, value: Any, ttl: int = None) -> None:
        """Set value in cache with TTL."""
        ttl = ttl or self.default_ttl
        self.redis.setex(key, ttl, json.dumps(value))
    
    def delete(self, key: str) -> None:
        """Delete key from cache."""
        self.redis.delete(key)
    
    def cache_result(self, ttl: int = None) -> Callable:
        """Decorator to cache function results."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                # Generate cache key from function name and args
                cache_key = f"{func.__module__}:{func.__name__}:{hash(str(args) + str(kwargs))}"
                
                # Try cache first
                cached = self.get(cache_key)
                if cached is not None:
                    return cached
                
                # Compute and cache result
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl)
                return result
            
            return wrapper
        return decorator

# Usage
@cache_manager.cache_result(ttl=3600)
def get_user_by_id(user_id: int) -> dict:
    user = User.query.get(user_id)
    return user.to_dict()
```

### 6.2 Background Jobs (Celery)

```python
# src/elcorp/jobs/celery_app.py

from celery import Celery
from celery.schedules import crontab
from flask import current_app

celery = Celery(__name__)

def init_celery(app):
    """Initialize Celery with Flask app."""
    celery.conf.update(app.config)
    
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)
    
    celery.Task = ContextTask
    return celery

# src/elcorp/jobs/tasks.py

from celery import shared_task
from datetime import datetime, timedelta
from app.models import ServiceRequest, User
from app.email_service import send_email

@shared_task
def send_approval_reminder():
    """Send reminders for pending approvals (runs every 4 hours)."""
    pending = ServiceRequest.query.filter_by(status='pending').all()
    
    for request in pending:
        if (datetime.utcnow() - request.created_at) > timedelta(hours=24):
            send_email(
                recipient=request.assigned_to.email,
                subject=f"Pending Request: {request.title}",
                body=f"Request {request.id} needs your review."
            )
    
    return f"Sent {len(pending)} reminders"

@shared_task
def archive_old_audit_logs():
    """Archive audit logs older than 90 days to cold storage."""
    cutoff = datetime.utcnow() - timedelta(days=90)
    old_logs = AuditLog.query.filter(AuditLog.timestamp < cutoff).all()
    
    # Export to S3 or SFTP
    for batch in chunks(old_logs, 1000):
        export_to_archive(batch)
    
    # Delete from hot storage
    AuditLog.query.filter(AuditLog.timestamp < cutoff).delete()
    
    return f"Archived {len(old_logs)} records"

# Schedule in config
celery.conf.beat_schedule = {
    'send-approval-reminders': {
        'task': 'app.jobs.tasks.send_approval_reminder',
        'schedule': crontab(minute=0, hour='*/4'),  # Every 4 hours
    },
    'archive-audit-logs': {
        'task': 'app.jobs.tasks.archive_old_audit_logs',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
    },
}
```

### 6.3 Horizontal Scaling

**Stateless Design Principles**:

1. ✅ Store sessions in Redis (not in-memory)
2. ✅ Use database for state (not application memory)
3. ✅ Externalize configuration (environment variables)
4. ✅ Use distributed locks for critical sections (Redis)
5. ✅ Cache expensive queries (read-only data)

```python
# src/elcorp/shared/infrastructure/distributed_lock.py

import redis
import time
from contextlib import contextmanager
import uuid

class DistributedLock:
    """Redis-based distributed lock for multiple instances."""
    
    def __init__(self, redis_client: redis.Redis, key: str, timeout: int = 10):
        self.redis = redis_client
        self.key = f"lock:{key}"
        self.token = str(uuid.uuid4())
        self.timeout = timeout
    
    def acquire(self) -> bool:
        """Acquire lock (non-blocking)."""
        return self.redis.set(self.key, self.token, nx=True, ex=self.timeout)
    
    def release(self) -> bool:
        """Release lock only if we still hold it."""
        # Lua script ensures atomic check-and-delete
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        return self.redis.eval(script, 1, self.key, self.token)
    
    @contextmanager
    def __enter__(self):
        while not self.acquire():
            time.sleep(0.1)
        return self
    
    def __exit__(self, *args):
        self.release()

# Usage
lock = DistributedLock(redis_client, "payment_processing")
with lock:
    # Only one service instance processes this payment
    process_payment(payment_id)
```

---

## Part 7: Testing & Quality Assurance

### 7.1 Testing Strategy

```python
# tests/unit/test_identity_domain.py

"""Unit tests for identity domain (no database, no Flask)."""

import pytest
from datetime import datetime
from elcorp.identity.domain.models import User
from elcorp.identity.domain.exceptions import InvalidPasswordException

class TestUserAggregate:
    """Test User aggregate root."""
    
    def test_create_user_valid(self):
        """Valid user creation."""
        user = User(
            id=1,
            username="john_doe",
            email="john@example.com",
            full_name="John Doe"
        )
        assert user.username == "john_doe"
        assert not user.is_deleted
    
    def test_set_password_valid(self):
        """Password validation and hashing."""
        user = User(id=1, username="test", email="test@test.com", full_name="Test")
        user.set_password("SecurePass123!")
        
        assert user.check_password("SecurePass123!")
        assert not user.check_password("WrongPassword")
    
    def test_set_password_weak_fails(self):
        """Weak password rejected."""
        user = User(id=1, username="test", email="test@test.com", full_name="Test")
        
        with pytest.raises(InvalidPasswordException):
            user.set_password("weak")  # Too short

# tests/integration/test_identity_api.py

"""Integration tests with Flask and database."""

import pytest
from flask import Flask
from app import create_app
from app.extensions import db
from app.models import User, Role

@pytest.fixture
def app():
    app = create_app({"TESTING": True, "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:"})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    return app.test_client()

def test_login_endpoint(client):
    """Test POST /api/v1/auth/login."""
    # Create test user
    user = User(
        username="testuser",
        email="test@example.com",
        phone="+264811234567",
        full_name="Test User",
        password_hash="hashed_password"
    )
    db.session.add(user)
    db.session.commit()
    
    # Login
    response = client.post("/api/v1/auth/login", json={
        "email": "test@example.com",
        "password": "testpass",
        "device_id": "device-123"
    })
    
    assert response.status_code == 200
    assert "access_token" in response.json
    assert "refresh_token" in response.json

# tests/security/test_injection.py

"""Security tests: SQL injection, XSS, CSRF, etc."""

def test_sql_injection_prevention(client):
    """Ensure SQL injection is prevented."""
    # Attempt SQL injection in search
    response = client.get("/api/v1/users?search='; DROP TABLE users;--")
    
    assert response.status_code == 422  # Validation error
    assert "Invalid" in response.json["error"]

def test_xss_prevention(client):
    """Ensure XSS is sanitized."""
    response = client.post("/api/v1/users", json={
        "username": "<script>alert('xss')</script>",
        "email": "test@example.com",
        "password": "Pass123!@#",
        "full_name": "Test"
    })
    
    # Should either sanitize or reject
    assert response.status_code in [422, 400]
```

### 7.2 Code Quality Tools

```bash
# .github/workflows/ci.yml

name: CI

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: elcorp_test
          POSTGRES_PASSWORD: testpass
      redis:
        image: redis:7

    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov black flake8 mypy
      
      - name: Lint with Black
        run: black --check src/ tests/
      
      - name: Type check with mypy
        run: mypy src/
      
      - name: Lint with flake8
        run: flake8 src/ tests/
      
      - name: Run tests
        run: pytest tests/ --cov=src/elcorp --cov-report=xml
        env:
          DATABASE_URL: postgresql://postgres:testpass@localhost/elcorp_test
          REDIS_URL: redis://localhost:6379
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./coverage.xml
```

---

## Part 8: DevOps & Deployment

### 8.1 Docker Configuration

```dockerfile
# infrastructure/docker/Dockerfile.backend

FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY backend/src ./src
COPY migrations ./migrations

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run with gunicorn
CMD ["gunicorn", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "wsgi:app"]
```

```yaml
# infrastructure/docker/docker-compose.yml

version: '3.9'

services:
  postgres:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: elcorp
      POSTGRES_USER: elcorp
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U elcorp"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  backend:
    build:
      context: .
      dockerfile: infrastructure/docker/Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      FLASK_ENV: production
      DATABASE_URL: postgresql://elcorp:${DB_PASSWORD}@postgres:5432/elcorp
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - ./logs:/app/logs

  frontend:
    build:
      context: frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      VITE_API_URL: http://localhost:8000/api/v1

  celery-worker:
    build:
      context: .
      dockerfile: infrastructure/docker/Dockerfile.backend
    command: celery -A src.elcorp.jobs.celery_app worker --loglevel=info
    environment:
      FLASK_ENV: production
      DATABASE_URL: postgresql://elcorp:${DB_PASSWORD}@postgres:5432/elcorp
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

  celery-beat:
    build:
      context: .
      dockerfile: infrastructure/docker/Dockerfile.backend
    command: celery -A src.elcorp.jobs.celery_app beat --loglevel=info
    environment:
      FLASK_ENV: production
      DATABASE_URL: postgresql://elcorp:${DB_PASSWORD}@postgres:5432/elcorp
      REDIS_URL: redis://redis:6379/0
    depends_on:
      - postgres
      - redis

volumes:
  postgres_data:
```

### 8.2 GitHub Actions CI/CD

```yaml
# infrastructure/github/workflows/cd.yml

name: Deploy to Production

on:
  push:
    branches: [main]
    paths:
      - 'backend/**'
      - 'frontend/**'
      - 'infrastructure/**'

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Login to GitHub Container Registry
        uses: docker/login-action@v2
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v4
        with:
          context: .
          file: infrastructure/docker/Dockerfile.backend
          push: true
          tags: ghcr.io/${{ github.repository }}/backend:latest
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Deploy to Supabase/Railway/Render
        env:
          DEPLOY_TOKEN: ${{ secrets.DEPLOY_TOKEN }}
        run: |
          # Example: Deploy to Render
          curl -X POST \
            "https://api.render.com/deploy/srv-${SERVICE_ID}?key=${DEPLOY_TOKEN}"
```

---

## Part 9: Security & Compliance Framework

### 9.1 Security Controls Checklist

| Control | Implementation | Priority |
|---------|---|---|
| **Authentication** | JWT + Refresh Tokens | CRITICAL |
| **Authorization** | RBAC + PBAC | CRITICAL |
| **Input Validation** | Pydantic schemas | CRITICAL |
| **Encryption at Rest** | AES-256 for sensitive fields | CRITICAL |
| **Encryption in Transit** | TLS 1.3, HTTPS only | CRITICAL |
| **Password Policy** | Min 12 chars, complexity rules | CRITICAL |
| **Session Management** | Device tracking, automatic logout | HIGH |
| **Rate Limiting** | 100 req/min per IP, 10 login attempts/hour | HIGH |
| **CSRF Protection** | SameSite cookies, CSRF tokens | HIGH |
| **SQL Injection Prevention** | Parameterized queries, ORM | CRITICAL |
| **XSS Prevention** | HTML escaping, CSP headers | HIGH |
| **Logging & Monitoring** | Audit logs, Sentry integration | HIGH |
| **Secret Management** | Environment variables + Vault | CRITICAL |
| **Dependency Scanning** | OWASP Dependabot, Snyk | MEDIUM |

### 9.2 Compliance Alignment (Financial Services)

**Key Requirements**:

1. **Auditability**: Every state-changing action logged with who, what, when, where, why
2. **Traceability**: Complete transaction chain from initiation to settlement
3. **Data Protection**: GDPR/POPIA compliance, right to erasure (soft deletes)
4. **Non-Repudiation**: Digital signatures for critical transactions
5. **Availability**: 99.9% uptime SLA
6. **Disaster Recovery**: RTO < 4 hours, RPO < 1 hour

---

## Part 10: Production Readiness Roadmap

### Phase 1: MVP → Production (Weeks 1-4)

**Week 1**: Architecture & Foundation
- [ ] Establish DDD folder structure
- [ ] Create shared kernel (exceptions, value objects, events)
- [ ] Set up Pydantic validators
- [ ] Implement centralized error handler

**Week 2**: Authentication & Authorization
- [ ] Implement JWT + refresh token system
- [ ] Build RBAC permissions model
- [ ] Create device token tracking
- [ ] Add 2FA/MFA support

**Week 3**: Database & Persistence
- [ ] Design normalized schema
- [ ] Create Alembic migrations
- [ ] Implement soft deletes
- [ ] Set up audit logging

**Week 4**: Testing & Quality
- [ ] Unit tests for domain layer
- [ ] Integration tests for APIs
- [ ] Security tests (injection, XSS, CSRF)
- [ ] Performance benchmarks

### Phase 2: Scaling (Weeks 5-8)

**Week 5**: Caching & Background Jobs
- [ ] Redis caching layer
- [ ] Celery setup with Beat
- [ ] Async task handlers
- [ ] Job monitoring

**Week 6**: DevOps & Deployment
- [ ] Docker containerization
- [ ] Docker Compose orchestration
- [ ] GitHub Actions CI/CD
- [ ] Health checks & monitoring

**Week 7**: Observability
- [ ] Prometheus metrics
- [ ] Sentry error tracking
- [ ] Structured logging (JSON)
- [ ] Dashboards (Grafana)

**Week 8**: Documentation & Hardening
- [ ] OpenAPI/Swagger specs
- [ ] Security audit
- [ ] Compliance review
- [ ] Disaster recovery plan

### Phase 3: National Scale (Weeks 9-12)

**Week 9**: Multi-Tenancy (Optional)
- [ ] Tenant isolation layer
- [ ] Per-tenant data segregation
- [ ] Custom branding support

**Week 10**: Blockchain Integration
- [ ] VIN registry on blockchain
- [ ] Token issuance & transfer
- [ ] Smart contract audit trails

**Week 11**: Advanced Compliance
- [ ] Regulatory reporting
- [ ] SLA tracking & enforcement
- [ ] Incident management
- [ ] Risk register

**Week 12**: Performance Optimization
- [ ] Query optimization
- [ ] Caching strategies
- [ ] Database tuning
- [ ] Load testing

---

## Conclusion

This architecture positions Elcorp Namibia as a **production-grade fintech platform** ready for:

✅ National deployment  
✅ Regulatory audit  
✅ Horizontal scaling (multi-instance)  
✅ High availability (99.9% uptime)  
✅ Financial compliance (audit trails, traceability)  
✅ Future blockchain integration  

**Next Steps**:
1. Review this architecture with stakeholders
2. Approve the new folder structure
3. Begin Phase 1 implementation
4. Establish code review standards
5. Set up CI/CD pipeline

**Key Contacts**:
- Architecture Lead: [Your role]
- Security Officer: [Name]
- Database Admin: [Name]
- DevOps Engineer: [Name]

---

**Document Version**: 2.0  
**Last Updated**: February 2, 2026  
**Status**: Ready for Implementation Review

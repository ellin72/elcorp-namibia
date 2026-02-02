# Refactored Project Structure: Implementation Guide

**Version**: 1.0  
**Purpose**: Transform from monolithic to modular DDD architecture  
**Scope**: Backend only (frontend structure is already clean)

---

## 1. New Directory Structure

Execute this command to create the structure:

```bash
mkdir -p backend/src/elcorp/{shared,identity,payments,governance,compliance}/\
         {domain,application,infrastructure,interfaces}
mkdir -p backend/src/elcorp/shared/{domain,infrastructure,security,util}
mkdir -p backend/src/elcorp/jobs
mkdir -p backend/migrations/versions
mkdir -p backend/tests/{unit,integration,security,fixtures}
mkdir -p infrastructure/{docker,kubernetes,terraform,github/workflows}
mkdir -p docs
```

---

## 2. File Migration Map

### From Current → To New Structure

```
CURRENT STRUCTURE                    NEW STRUCTURE (DDD)
═══════════════════════════════════════════════════════════════════

app/__init__.py                      → backend/src/elcorp/main.py
app/models.py                        → backend/src/elcorp/{context}/infrastructure/persistence/models.py
app/security.py                      → backend/src/elcorp/shared/security/
app/extensions.py                    → backend/src/elcorp/config.py
app/audit.py                         → backend/src/elcorp/shared/infrastructure/audit.py
app/email_service.py                 → backend/src/elcorp/identity/infrastructure/external/email.py
app/email.py                         → backend/src/elcorp/identity/infrastructure/external/email_templates.py
app/celery_app.py                    → backend/src/elcorp/jobs/celery_app.py
app/tasks.py                         → backend/src/elcorp/jobs/tasks.py
app/utils.py                         → backend/src/elcorp/shared/util/

app/auth/routes.py                   → backend/src/elcorp/identity/interfaces/http/routes.py
app/auth/forms.py                    → backend/src/elcorp/identity/interfaces/http/validators.py

app/api_v1/auth_routes.py            → backend/src/elcorp/identity/interfaces/http/handlers.py
app/api_v1/service_requests_routes.py → backend/src/elcorp/governance/interfaces/http/handlers.py
app/api_v1/users_routes.py           → backend/src/elcorp/identity/interfaces/http/handlers.py

app/services/analytics_service.py    → backend/src/elcorp/compliance/application/services.py
app/services/export_service.py       → backend/src/elcorp/compliance/infrastructure/export.py
app/services/sla_service.py          → backend/src/elcorp/compliance/domain/services.py

tests/*                              → backend/tests/{unit,integration,security}/*

requirements.txt                     → backend/requirements.txt
pytest.ini                           → backend/pytest.ini
alembic.ini                          → backend/alembic.ini
```

---

## 3. Module-by-Module Migration

### 3.1 Shared Kernel

#### `backend/src/elcorp/shared/domain/exceptions.py`

```python
"""Domain-level exceptions (no framework dependencies)."""

class DomainException(Exception):
    """Base exception for domain logic."""
    pass

class ValidationException(DomainException):
    """Validation error (input data)."""
    pass

class InvalidPasswordException(ValidationException):
    """Password validation failed."""
    pass

class InvalidEmailException(ValidationException):
    """Email validation failed."""
    pass

class UserAlreadyExistsException(DomainException):
    """User with email/username already registered."""
    pass

class UserNotFoundException(DomainException):
    """User not found."""
    pass

class AccessDeniedException(DomainException):
    """User lacks required permission."""
    pass

class TokenExpiredException(DomainException):
    """JWT token expired."""
    pass

class InvalidTokenException(DomainException):
    """JWT token invalid."""
    pass

class InsufficientBalanceException(DomainException):
    """Payment insufficient funds."""
    pass

class SLAViolationException(DomainException):
    """Service level agreement violated."""
    pass
```

#### `backend/src/elcorp/shared/domain/value_objects.py`

```python
"""Value objects (immutable, equatable by value)."""

from dataclasses import dataclass
from typing import Optional
import re

@dataclass(frozen=True)
class Email:
    """Email value object with validation."""
    value: str
    
    def __post_init__(self):
        if not re.match(r"^[^@]+@[^@]+\.[^@]+$", self.value):
            from .exceptions import InvalidEmailException
            raise InvalidEmailException(f"Invalid email: {self.value}")
    
    def __str__(self):
        return self.value

@dataclass(frozen=True)
class PhoneNumber:
    """Phone number value object."""
    country_code: str
    number: str
    
    def full_number(self) -> str:
        return f"{self.country_code}{self.number}"

@dataclass(frozen=True)
class Money:
    """Money value object for currency amounts."""
    amount: float
    currency: str  # ISO 4217: NAD, USD, etc.
    
    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(self.amount + other.amount, self.currency)
    
    def __sub__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot subtract different currencies")
        return Money(self.amount - other.amount, self.currency)

@dataclass(frozen=True)
class WalletAddress:
    """Wallet address value object (UUID)."""
    value: str
    
    def __post_init__(self):
        import uuid
        try:
            uuid.UUID(self.value)
        except ValueError:
            raise ValueError(f"Invalid UUID: {self.value}")
```

#### `backend/src/elcorp/shared/domain/events.py`

```python
"""Domain events for event-driven architecture."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
import uuid

@dataclass
class DomainEvent:
    """Base class for domain events."""
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_id: int = None
    aggregate_type: str = None

@dataclass
class UserCreatedEvent(DomainEvent):
    """Fired when user created."""
    user_id: int
    email: str
    username: str

@dataclass
class UserPasswordChangedEvent(DomainEvent):
    """Fired when password changed."""
    user_id: int
    timestamp: datetime

@dataclass
class PaymentInitiatedEvent(DomainEvent):
    """Fired when payment initiated."""
    payment_id: int
    from_user_id: int
    to_user_id: int
    amount: float
    currency: str

@dataclass
class ServiceRequestApprovedEvent(DomainEvent):
    """Fired when service request approved."""
    request_id: int
    approved_by: int
```

### 3.2 Identity Context - Domain Layer

#### `backend/src/elcorp/identity/domain/models.py`

```python
"""Domain models for Identity context (NO SQLAlchemy, NO Flask)."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, List
from enum import Enum
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

from elcorp.shared.domain.exceptions import (
    InvalidPasswordException,
    InvalidEmailException,
)
from elcorp.shared.domain.value_objects import Email, PhoneNumber, WalletAddress
from elcorp.shared.domain.events import UserCreatedEvent, DomainEvent

class UserRole(Enum):
    ADMIN = "admin"
    STAFF = "staff"
    USER = "user"
    GUEST = "guest"

@dataclass
class User:
    """User aggregate root (Domain Model)."""
    
    id: int
    username: str
    email: Email
    phone: PhoneNumber
    full_name: str
    password_hash: str
    role: UserRole
    wallet_address: WalletAddress
    
    # State
    is_active: bool = True
    agreed_terms: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    deleted_at: Optional[datetime] = None
    
    # Domain events (not persisted)
    _events: List[DomainEvent] = field(default_factory=list, init=False)
    
    # Password history (prevent reuse)
    _password_history: List[str] = field(default_factory=list, init=False)
    
    def __post_init__(self):
        """Validate on creation."""
        if len(self.username) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(self.full_name) < 2:
            raise ValueError("Full name must be at least 2 characters")
    
    def set_password(self, plaintext: str) -> None:
        """Hash and set password with validation."""
        # Validate password strength
        if len(plaintext) < 12:
            raise InvalidPasswordException("Password must be at least 12 characters")
        if not any(c.isupper() for c in plaintext):
            raise InvalidPasswordException("Password must contain uppercase letter")
        if not any(c.islower() for c in plaintext):
            raise InvalidPasswordException("Password must contain lowercase letter")
        if not any(c.isdigit() for c in plaintext):
            raise InvalidPasswordException("Password must contain digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:',.<>?/~`" for c in plaintext):
            raise InvalidPasswordException("Password must contain special character")
        
        # Check password history
        new_hash = generate_password_hash(plaintext)
        for old_hash in self._password_history[-5:]:  # Last 5 passwords
            if check_password_hash(old_hash, plaintext):
                raise InvalidPasswordException("Password was recently used")
        
        # Update password
        self._password_history.append(self.password_hash)
        self.password_hash = new_hash
    
    def check_password(self, plaintext: str) -> bool:
        """Verify password."""
        return check_password_hash(self.password_hash, plaintext)
    
    def can_access_resource(self, resource_type: str) -> bool:
        """Check if user has permission for resource."""
        # TODO: Implement RBAC logic
        return self.role in [UserRole.ADMIN, UserRole.STAFF]
    
    def mark_deleted(self) -> None:
        """Soft delete user."""
        self.deleted_at = datetime.utcnow()
    
    def restore(self) -> None:
        """Restore soft-deleted user."""
        self.deleted_at = None
    
    def record_login(self) -> None:
        """Record login timestamp."""
        self.last_login = datetime.utcnow()
    
    def add_event(self, event: DomainEvent) -> None:
        """Add domain event (for event sourcing)."""
        self._events.append(event)
    
    def get_uncommitted_events(self) -> List[DomainEvent]:
        """Get events to be published."""
        return self._events
    
    def clear_events(self) -> None:
        """Clear after publishing."""
        self._events.clear()

@dataclass
class DeviceToken:
    """Multi-device session tracking."""
    
    id: int
    user_id: int
    device_id: str
    device_name: Optional[str]
    refresh_token: str
    user_agent: str
    ip_address: str
    expires_at: datetime
    is_revoked: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    
    def is_valid(self) -> bool:
        """Check if token is still valid."""
        return not self.is_revoked and datetime.utcnow() < self.expires_at
    
    def revoke(self) -> None:
        """Revoke this device token."""
        self.is_revoked = True
```

#### `backend/src/elcorp/identity/domain/repositories.py`

```python
"""Repository interfaces (dependency inversion)."""

from abc import ABC, abstractmethod
from typing import Optional, List
from .models import User, DeviceToken

class UserRepository(ABC):
    """Interface for user persistence."""
    
    @abstractmethod
    def save(self, user: User) -> None:
        """Save user (create or update)."""
        pass
    
    @abstractmethod
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Fetch user by ID."""
        pass
    
    @abstractmethod
    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email."""
        pass
    
    @abstractmethod
    def get_by_username(self, username: str) -> Optional[User]:
        """Fetch user by username."""
        pass
    
    @abstractmethod
    def exists_email(self, email: str) -> bool:
        """Check if email exists."""
        pass
    
    @abstractmethod
    def exists_username(self, username: str) -> bool:
        """Check if username exists."""
        pass
    
    @abstractmethod
    def delete(self, user_id: int) -> None:
        """Soft delete user."""
        pass
    
    @abstractmethod
    def list_active(self, offset: int, limit: int) -> List[User]:
        """List active users with pagination."""
        pass

class DeviceTokenRepository(ABC):
    """Interface for device token persistence."""
    
    @abstractmethod
    def save(self, token: DeviceToken) -> None:
        """Save device token."""
        pass
    
    @abstractmethod
    def get_by_device_id(self, user_id: int, device_id: str) -> Optional[DeviceToken]:
        """Get token by device ID."""
        pass
    
    @abstractmethod
    def list_user_devices(self, user_id: int) -> List[DeviceToken]:
        """List all devices for user."""
        pass
```

#### `backend/src/elcorp/identity/domain/services.py`

```python
"""Domain services (stateless, pure business logic)."""

from typing import Tuple, Optional
from datetime import datetime, timedelta
from .models import User, UserRole
from .repositories import UserRepository
from .exceptions import (
    UserAlreadyExistsException,
    InvalidPasswordException,
)
from elcorp.shared.domain.value_objects import Email, PhoneNumber, WalletAddress

class UserRegistrationService:
    """Handles user registration business logic."""
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
    
    def register_user(
        self,
        username: str,
        email: str,
        password: str,
        phone: str,
        full_name: str,
    ) -> User:
        """
        Register new user with validation.
        
        Raises:
            UserAlreadyExistsException
            InvalidPasswordException
            ValueError (email/phone format)
        """
        # Check duplicates
        if self.user_repo.exists_email(email):
            raise UserAlreadyExistsException(f"Email already registered: {email}")
        
        if self.user_repo.exists_username(username):
            raise UserAlreadyExistsException(f"Username already taken: {username}")
        
        # Create user with validation
        email_vo = Email(email)  # Validates email format
        phone_vo = PhoneNumber("+264", phone)  # Namibia default
        wallet = WalletAddress(str(uuid.uuid4()))
        
        user = User(
            id=None,  # Will be assigned by repository
            username=username,
            email=email_vo,
            phone=phone_vo,
            full_name=full_name,
            password_hash="",
            role=UserRole.USER,
            wallet_address=wallet,
        )
        
        # Set password (validates complexity)
        user.set_password(password)
        
        # Save
        self.user_repo.save(user)
        
        return user
```

### 3.3 Identity Context - Application Layer

#### `backend/src/elcorp/identity/application/dto.py`

```python
"""Data Transfer Objects (request/response contracts)."""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime

class CreateUserRequest(BaseModel):
    """Request to create user."""
    
    username: str = Field(..., min_length=3, max_length=64)
    email: EmailStr
    password: str = Field(..., min_length=12)
    phone: str = Field(..., pattern=r"^[0-9]{7,20}$")
    full_name: str = Field(..., min_length=2, max_length=100)
    organization: Optional[str] = Field(None, max_length=100)
    agreed_terms: bool = True
    
    @field_validator("password")
    def validate_password_strength(cls, v: str) -> str:
        """Enforce password complexity."""
        if not any(c.isupper() for c in v):
            raise ValueError("Must contain uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Must contain lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Must contain digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:',.<>?/~`" for c in v):
            raise ValueError("Must contain special character")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "username": "johndoe",
                "email": "john@example.com",
                "password": "SecurePass123!",
                "phone": "811234567",
                "full_name": "John Doe",
                "agreed_terms": True,
            }
        }

class UserResponse(BaseModel):
    """Response with user data (no password)."""
    
    id: int
    username: str
    email: str
    full_name: str
    phone: str
    role: str
    wallet_address: str
    created_at: datetime
    last_login: Optional[datetime]
    
    class Config:
        from_attributes = True

class LoginRequest(BaseModel):
    """Login request."""
    
    email: EmailStr
    password: str
    device_id: Optional[str] = None
    device_name: Optional[str] = None

class TokenResponse(BaseModel):
    """Token response."""
    
    access_token: str
    refresh_token: str
    expires_in: int
    user: UserResponse
```

#### `backend/src/elcorp/identity/application/commands.py`

```python
"""Command handlers (use cases)."""

from dataclasses import dataclass
from typing import Optional
from ..domain.models import User
from ..domain.services import UserRegistrationService
from ..infrastructure.persistence.repositories import UserSQLAlchemyRepository
from .dto import CreateUserRequest

@dataclass
class CreateUserCommand:
    """Command to create user."""
    username: str
    email: str
    password: str
    phone: str
    full_name: str

class CreateUserCommandHandler:
    """Execute user creation."""
    
    def __init__(self, user_repo: UserSQLAlchemyRepository):
        self.registration_service = UserRegistrationService(user_repo)
    
    def execute(self, command: CreateUserCommand) -> User:
        """Handle create user command."""
        user = self.registration_service.register_user(
            username=command.username,
            email=command.email,
            password=command.password,
            phone=command.phone,
            full_name=command.full_name,
        )
        return user
```

### 3.4 Identity Context - Infrastructure (Persistence)

#### `backend/src/elcorp/identity/infrastructure/persistence/models.py`

```python
"""SQLAlchemy models (NOT domain models)."""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from elcorp.shared.infrastructure.database import Base

class UserModel(Base):
    """SQLAlchemy user table."""
    
    __tablename__ = "user"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    phone = Column(String(20), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(100), nullable=False)
    organization = Column(String(100), nullable=True)
    wallet_address = Column(String(36), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    agreed_terms = Column(Boolean, default=False)
    role = Column(String(32), default="user")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    
    # Relations
    device_tokens = relationship("DeviceTokenModel", back_populates="user", cascade="all, delete-orphan")
    password_history = relationship("PasswordHistoryModel", back_populates="user", cascade="all, delete-orphan")

class DeviceTokenModel(Base):
    """SQLAlchemy device token table."""
    
    __tablename__ = "device_token"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("user.id"), nullable=False)
    device_id = Column(String(36), nullable=False)
    device_name = Column(String(100), nullable=True)
    refresh_token = Column(Text, nullable=False)
    user_agent = Column(Text)
    ip_address = Column(String(45))
    is_revoked = Column(Boolean, default=False)
    last_used_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relations
    user = relationship("UserModel", back_populates="device_tokens")
```

#### `backend/src/elcorp/identity/infrastructure/persistence/repositories.py`

```python
"""Repository implementations (adapters)."""

from typing import Optional, List
from sqlalchemy.orm import Session
from elcorp.identity.domain.models import User
from elcorp.identity.domain.repositories import UserRepository
from .models import UserModel
from .mappers import UserMapper

class UserSQLAlchemyRepository(UserRepository):
    """PostgreSQL implementation of UserRepository."""
    
    def __init__(self, session: Session):
        self.session = session
        self.mapper = UserMapper()
    
    def save(self, user: User) -> None:
        """Save user to database."""
        model = self.mapper.to_persistence_model(user)
        self.session.merge(model)
        self.session.commit()
    
    def get_by_id(self, user_id: int) -> Optional[User]:
        """Fetch active user by ID."""
        model = self.session.query(UserModel).filter(
            UserModel.id == user_id,
            UserModel.deleted_at.is_(None)
        ).first()
        return self.mapper.to_domain_model(model) if model else None
    
    def get_by_email(self, email: str) -> Optional[User]:
        """Fetch user by email."""
        model = self.session.query(UserModel).filter(
            UserModel.email == email,
            UserModel.deleted_at.is_(None)
        ).first()
        return self.mapper.to_domain_model(model) if model else None
    
    def exists_email(self, email: str) -> bool:
        """Check if email exists."""
        return self.session.query(UserModel).filter(
            UserModel.email == email,
            UserModel.deleted_at.is_(None)
        ).exists().scalar()
    
    # ... other methods ...
```

#### `backend/src/elcorp/identity/infrastructure/persistence/mappers.py`

```python
"""Mappers between domain and persistence models."""

from elcorp.identity.domain.models import User
from elcorp.identity.domain.value_objects import Email, PhoneNumber, WalletAddress
from .models import UserModel

class UserMapper:
    """Map between User domain model and UserModel persistence model."""
    
    @staticmethod
    def to_domain_model(model: UserModel) -> User:
        """Convert ORM model to domain model."""
        return User(
            id=model.id,
            username=model.username,
            email=Email(model.email),
            phone=PhoneNumber("+264", model.phone),
            full_name=model.full_name,
            password_hash=model.password_hash,
            role=model.role,
            wallet_address=WalletAddress(model.wallet_address),
            is_active=model.is_active,
            agreed_terms=model.agreed_terms,
            created_at=model.created_at,
            last_login=model.last_login,
            deleted_at=model.deleted_at,
        )
    
    @staticmethod
    def to_persistence_model(user: User) -> UserModel:
        """Convert domain model to ORM model."""
        return UserModel(
            id=user.id,
            username=user.username,
            email=str(user.email),
            phone=user.phone.number,
            full_name=user.full_name,
            password_hash=user.password_hash,
            role=user.role.value,
            wallet_address=user.wallet_address.value,
            is_active=user.is_active,
            agreed_terms=user.agreed_terms,
            created_at=user.created_at,
            last_login=user.last_login,
            deleted_at=user.deleted_at,
        )
```

### 3.5 Identity Context - Interfaces (HTTP API)

#### `backend/src/elcorp/identity/interfaces/http/handlers.py`

```python
"""HTTP request handlers (no Flask decorators in handlers themselves)."""

from flask import request, jsonify
from pydantic import ValidationError
from elcorp.identity.application.dto import CreateUserRequest, UserResponse, LoginRequest
from elcorp.identity.application.commands import CreateUserCommand, CreateUserCommandHandler
from elcorp.identity.infrastructure.persistence.repositories import UserSQLAlchemyRepository
from elcorp.shared.infrastructure.response import APIResponse, HTTPStatus
from elcorp.shared.security.jwt_handler import JWTHandler
from elcorp.extensions import db

class UserCreationHandler:
    """Handle POST /users."""
    
    def handle(self):
        """Create new user."""
        try:
            # Validate request
            dto = CreateUserRequest(**request.json)
            
            # Execute command
            handler = CreateUserCommandHandler(UserSQLAlchemyRepository(db.session))
            command = CreateUserCommand(
                username=dto.username,
                email=dto.email,
                password=dto.password,
                phone=dto.phone,
                full_name=dto.full_name,
            )
            user = handler.execute(command)
            
            # Map to response
            response = APIResponse(
                status=HTTPStatus.SUCCESS,
                data=UserResponse.from_orm(user).dict()
            )
            return jsonify(response.to_dict()), 201
        
        except ValidationError as e:
            response = APIResponse(
                status=HTTPStatus.VALIDATION_ERROR,
                errors=e.errors()
            )
            return jsonify(response.to_dict()), 422

class LoginHandler:
    """Handle POST /auth/login."""
    
    def handle(self):
        """Authenticate user and issue tokens."""
        try:
            dto = LoginRequest(**request.json)
            repo = UserSQLAlchemyRepository(db.session)
            user = repo.get_by_email(dto.email)
            
            if not user or not user.check_password(dto.password):
                response = APIResponse(
                    status=HTTPStatus.ERROR,
                    error="Invalid credentials"
                )
                return jsonify(response.to_dict()), 401
            
            # Generate tokens
            jwt_handler = JWTHandler(current_app.config["SECRET_KEY"])
            access_token = jwt_handler.generate_access_token(user.id, user.role.value)
            refresh_token = jwt_handler.generate_refresh_token(user.id)
            
            response = APIResponse(
                status=HTTPStatus.SUCCESS,
                data={
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_in": 900,
                    "user": UserResponse.from_orm(user).dict()
                }
            )
            return jsonify(response.to_dict()), 200
        
        except ValidationError as e:
            response = APIResponse(
                status=HTTPStatus.VALIDATION_ERROR,
                errors=e.errors()
            )
            return jsonify(response.to_dict()), 422
```

#### `backend/src/elcorp/identity/interfaces/http/routes.py`

```python
"""Flask blueprint for identity endpoints."""

from flask import Blueprint, request
from .handlers import UserCreationHandler, LoginHandler

bp = Blueprint("identity", __name__, url_prefix="/api/v1")

@bp.route("/auth/login", methods=["POST"])
def login():
    """Login endpoint."""
    handler = LoginHandler()
    return handler.handle()

@bp.route("/users", methods=["POST"])
def create_user():
    """User registration endpoint."""
    handler = UserCreationHandler()
    return handler.handle()

@bp.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    """Get user details."""
    # Implementation...
    pass
```

---

## 4. Configuration & Extensions

#### `backend/src/elcorp/config.py`

```python
"""Centralized configuration."""

import os
from datetime import timedelta

class Config:
    """Base configuration."""
    
    # Core
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-in-prod")
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = FLASK_ENV == "development"
    
    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql://elcorp:password@localhost:5432/elcorp"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    
    # JWT
    JWT_SECRET = os.getenv("JWT_SECRET", SECRET_KEY)
    JWT_ALGORITHM = "HS256"
    JWT_ACCESS_TOKEN_TTL = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_TTL = timedelta(days=7)
    
    # Password
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_HISTORY_COUNT = 5
    PASSWORD_RESET_TOKEN_TTL = 3600
    
    # Security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = not DEBUG
    
    # Pagination
    ITEMS_PER_PAGE = 20
    
    # Logging
    LOG_LEVEL = "INFO" if not DEBUG else "DEBUG"

class DevelopmentConfig(Config):
    """Development-specific config."""
    DEBUG = True

class ProductionConfig(Config):
    """Production config."""
    SESSION_COOKIE_SECURE = True

class TestConfig(Config):
    """Testing config."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"

def get_config():
    """Get config based on environment."""
    env = os.getenv("FLASK_ENV", "development")
    if env == "production":
        return ProductionConfig
    elif env == "testing":
        return TestConfig
    return DevelopmentConfig
```

#### `backend/src/elcorp/shared/infrastructure/database.py`

```python
"""Database initialization."""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

def init_db(app):
    """Initialize database with app."""
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
```

---

## 5. Testing Structure

#### `backend/tests/conftest.py`

```python
"""Pytest fixtures."""

import pytest
from flask import Flask
from elcorp.main import create_app
from elcorp.extensions import db

@pytest.fixture
def app():
    """Create app for testing."""
    app = create_app({"TESTING": True})
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()

@pytest.fixture
def runner(app):
    """CLI runner."""
    return app.test_cli_runner()
```

---

## 6. Migration from Current to New

### Step-by-Step Process

1. **Create new structure**
   ```bash
   cd backend && mkdir -p src/elcorp/{shared,identity,payments,governance,compliance}/{domain,application,infrastructure,interfaces}
   ```

2. **Move domain logic** (no breaking changes)
   - Copy `models.py` logic into domain layers
   - Create value objects and exceptions
   - Keep domain layer framework-agnostic

3. **Create repositories** (interfaces)
   - Define abstract base classes in domain
   - Implement using SQLAlchemy in infrastructure

4. **Refactor routes** (incrementally)
   - Create new blueprint with handlers
   - Keep old Flask routes working
   - Gradually migrate endpoint by endpoint

5. **Update imports** in application startup
6. **Run tests** after each change
7. **Delete old code** only after verification

---

## File Migration Checklist

- [ ] Create `backend/src/` structure
- [ ] Move `app/models.py` → domain/models, infrastructure/persistence/models
- [ ] Move `app/security.py` → shared/security
- [ ] Move `app/auth/*` → identity/interfaces/http
- [ ] Move `app/api_v1/*` → respective context interfaces
- [ ] Move `app/services/*` → respective context application/domain
- [ ] Create all repository interfaces
- [ ] Implement repository adapters
- [ ] Create DTOs (Pydantic models)
- [ ] Create command/query handlers
- [ ] Migrate Flask routes
- [ ] Update `__init__.py` / app factory
- [ ] Update tests to use new structure
- [ ] Update requirements.txt with new dependencies
- [ ] Update documentation
- [ ] Smoke test all endpoints

---

## Next: Implementation Priority

1. **Week 1**: Shared kernel + Identity domain
2. **Week 2**: Identity application + infrastructure
3. **Week 3**: Identity HTTP layer + migration
4. **Week 4**: Payment context (same pattern)
5. **Week 5+**: Governance & Compliance contexts

---

**Version**: 1.0  
**Last Updated**: February 2, 2026

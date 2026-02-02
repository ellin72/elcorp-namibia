"""
Command handlers - Business logic for processing commands.
Handlers orchestrate domain logic and repository operations.
"""

from typing import Optional, Tuple
from datetime import datetime, timedelta, timezone
import uuid

from ..domain import User, UserStatus, DeviceToken
from ..domain.user_repository import UserRepository
from ..domain.device_token_repository import DeviceTokenRepository
from ...shared.domain import (
    Email,
    PhoneNumber,
    ValidationException,
    ConflictError,
    UnauthorizedError,
)
from ...shared.security import JWTHandler
from .commands import RegisterUserCommand, LoginUserCommand
from .dtos import UserProfileDTO


class RegisterUserHandler:
    """Handler for user registration."""

    def __init__(self, user_repository: UserRepository, jwt_handler: JWTHandler):
        self.user_repository = user_repository
        self.jwt_handler = jwt_handler

    async def handle(self, command: RegisterUserCommand) -> User:
        """
        Process user registration.
        Invariants:
        - Email must be unique
        - Username must be unique
        - Password must be strong
        """
        # Check if email already exists
        if await self.user_repository.email_exists(command.email):
            raise ConflictError(
                f"Email {command.email} is already registered",
                conflict_field="email",
            )

        # Check if username already exists
        if await self.user_repository.username_exists(command.username):
            raise ConflictError(
                f"Username {command.username} is already taken",
                conflict_field="username",
            )

        # Create new user aggregate
        user = User(
            id=str(uuid.uuid4()),
            username=command.username,
            email=Email(command.email),
            phone=PhoneNumber(command.phone),
        )

        # Set password (validates strength and hashes)
        user.set_password(command.password)

        # Persist user
        await self.user_repository.add(user)

        return user


class LoginUserHandler:
    """Handler for user login."""

    def __init__(
        self,
        user_repository: UserRepository,
        device_token_repository: DeviceTokenRepository,
        jwt_handler: JWTHandler,
    ):
        self.user_repository = user_repository
        self.device_token_repository = device_token_repository
        self.jwt_handler = jwt_handler

    async def handle(
        self, command: LoginUserCommand
    ) -> Tuple[str, str, UserProfileDTO]:
        """
        Process user login.
        Returns: (access_token, refresh_token, user_profile)
        """
        # Find user by username
        user = await self.user_repository.get_by_username(command.username)
        if not user:
            raise UnauthorizedError("Invalid username or password")

        # Check if account is locked
        if user.status == UserStatus.LOCKED:
            raise UnauthorizedError("Account is locked. Please contact support.")

        # Verify password
        if not user.verify_password(command.password):
            user.record_failed_login()
            await self.user_repository.update(user)
            raise UnauthorizedError("Invalid username or password")

        # Check if MFA is enabled (additional flow would be needed)
        if user.mfa_enabled:
            # In production, would challenge for MFA code here
            raise UnauthorizedError("Multi-factor authentication required")

        # Record successful login
        user.record_successful_login()
        await self.user_repository.update(user)

        # Create device token
        device_token = DeviceToken(
            user_id=user.id,
            device_id=command.device_id,
            device_name=command.device_name or "Unknown Device",
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

        # Generate tokens with device binding
        access_token = self.jwt_handler.create_access_token(
            user_id=user.id,
            device_id=command.device_id,
        )
        refresh_token = self.jwt_handler.create_refresh_token(
            user_id=user.id,
            device_id=command.device_id,
        )

        # Store refresh token in device token repo
        device_token.refresh_token = refresh_token
        await self.device_token_repository.add(device_token)

        # Build profile response
        profile = UserProfileDTO(
            id=user.id,
            username=user.username,
            email=str(user.email),
            phone=str(user.phone),
            role=user.role,
            wallet_address=str(user.wallet_address) if user.wallet_address else None,
            mfa_enabled=user.mfa_enabled,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )

        return access_token, refresh_token, profile

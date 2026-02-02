"""
Repository implementations using SQLAlchemy.
Adapters that implement domain repository interfaces.
"""

from typing import Optional, List
from ..domain import User, UserStatus, DeviceToken
from ..domain.user_repository import UserRepository
from ..domain.device_token_repository import DeviceTokenRepository
from .sqlalchemy_models import UserModel, DeviceTokenModel, UserModelStatus
from ...shared.domain import Email, PhoneNumber, WalletAddress


class SQLAlchemyUserRepository(UserRepository):
    """SQLAlchemy implementation of UserRepository."""

    def __init__(self, db_session):
        self.db = db_session

    async def add(self, user: User) -> None:
        """Add a new user."""
        model = self._to_model(user)
        self.db.add(model)
        await self.db.commit()

    async def update(self, user: User) -> None:
        """Update an existing user."""
        model = self._to_model(user)
        await self.db.merge(model)
        await self.db.commit()

    async def delete(self, user_id: str) -> None:
        """Soft delete a user."""
        user = await self.get_by_id(user_id)
        if user:
            user.soft_delete()
            await self.update(user)

    async def get_by_id(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        model = await self.db.query(UserModel).filter(UserModel.id == user_id).first()
        return self._to_domain(model) if model else None

    async def get_by_email(self, email: str) -> Optional[User]:
        """Get user by email."""
        model = await self.db.query(UserModel).filter(UserModel.email == email.lower()).first()
        return self._to_domain(model) if model else None

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        model = await self.db.query(UserModel).filter(UserModel.username == username).first()
        return self._to_domain(model) if model else None

    async def get_by_wallet(self, wallet_address: str) -> Optional[User]:
        """Get user by wallet address."""
        model = await self.db.query(UserModel).filter(
            UserModel.wallet_address == wallet_address.lower()
        ).first()
        return self._to_domain(model) if model else None

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[User]:
        """Get all users with pagination."""
        models = await self.db.query(UserModel).offset(skip).limit(limit).all()
        return [self._to_domain(m) for m in models if m]

    async def exists(self, user_id: str) -> bool:
        """Check if user exists."""
        return await self.get_by_id(user_id) is not None

    async def email_exists(self, email: str) -> bool:
        """Check if email exists."""
        return await self.get_by_email(email) is not None

    async def username_exists(self, username: str) -> bool:
        """Check if username exists."""
        return await self.get_by_username(username) is not None

    def _to_model(self, user: User) -> UserModel:
        """Convert domain User to SQLAlchemy model."""
        return UserModel(
            id=user.id,
            username=user.username,
            email=str(user.email),
            phone=str(user.phone),
            password_hash=user.password_hash,
            role=user.role,
            status=UserModelStatus[user.status.value.upper()],
            wallet_address=str(user.wallet_address) if user.wallet_address else None,
            wallet_blockchain=user.wallet_address.blockchain if user.wallet_address else None,
            mfa_enabled=user.mfa_enabled,
            mfa_method=user.mfa_method,
            mfa_secret=user.mfa_secret,
            failed_login_attempts=user.failed_login_attempts,
            last_login_at=user.last_login_at,
            password_changed_at=user.password_changed_at,
            created_at=user.created_at,
            updated_at=user.updated_at,
            deleted_at=user.deleted_at,
        )

    def _to_domain(self, model: UserModel) -> User:
        """Convert SQLAlchemy model to domain User."""
        return User(
            id=model.id,
            username=model.username,
            email=Email(model.email),
            phone=PhoneNumber(model.phone),
            password_hash=model.password_hash,
            role=model.role,
            status=UserStatus[model.status.value.upper()],
            wallet_address=WalletAddress(model.wallet_address, model.wallet_blockchain)
            if model.wallet_address
            else None,
            mfa_enabled=model.mfa_enabled,
            mfa_method=model.mfa_method,
            mfa_secret=model.mfa_secret,
            failed_login_attempts=model.failed_login_attempts,
            last_login_at=model.last_login_at,
            password_changed_at=model.password_changed_at,
            created_at=model.created_at,
            updated_at=model.updated_at,
            deleted_at=model.deleted_at,
        )


class SQLAlchemyDeviceTokenRepository(DeviceTokenRepository):
    """SQLAlchemy implementation of DeviceTokenRepository."""

    def __init__(self, db_session):
        self.db = db_session

    async def add(self, token: DeviceToken) -> None:
        """Add a new device token."""
        model = self._to_model(token)
        self.db.add(model)
        await self.db.commit()

    async def update(self, token: DeviceToken) -> None:
        """Update a device token."""
        model = self._to_model(token)
        await self.db.merge(model)
        await self.db.commit()

    async def delete(self, token_id: str) -> None:
        """Delete a device token."""
        token = await self.get_by_id(token_id)
        if token:
            token.revoke()
            await self.update(token)

    async def get_by_id(self, token_id: str) -> Optional[DeviceToken]:
        """Get device token by ID."""
        model = await self.db.query(DeviceTokenModel).filter(
            DeviceTokenModel.id == token_id
        ).first()
        return self._to_domain(model) if model else None

    async def get_by_user_and_device(
        self, user_id: str, device_id: str
    ) -> Optional[DeviceToken]:
        """Get token for specific user and device."""
        model = await self.db.query(DeviceTokenModel).filter(
            DeviceTokenModel.user_id == user_id,
            DeviceTokenModel.device_id == device_id,
        ).first()
        return self._to_domain(model) if model else None

    async def get_all_by_user(self, user_id: str) -> List[DeviceToken]:
        """Get all device tokens for a user."""
        models = await self.db.query(DeviceTokenModel).filter(
            DeviceTokenModel.user_id == user_id
        ).all()
        return [self._to_domain(m) for m in models if m]

    async def get_all(self, skip: int = 0, limit: int = 100) -> List[DeviceToken]:
        """Get all device tokens."""
        models = await self.db.query(DeviceTokenModel).offset(skip).limit(limit).all()
        return [self._to_domain(m) for m in models if m]

    async def exists(self, token_id: str) -> bool:
        """Check if token exists."""
        return await self.get_by_id(token_id) is not None

    async def revoke_device(self, user_id: str, device_id: str) -> None:
        """Revoke token for a specific device."""
        token = await self.get_by_user_and_device(user_id, device_id)
        if token:
            token.revoke()
            await self.update(token)

    async def revoke_all_devices(self, user_id: str) -> None:
        """Revoke all tokens for a user."""
        tokens = await self.get_all_by_user(user_id)
        for token in tokens:
            token.revoke()
            await self.update(token)

    def _to_model(self, token: DeviceToken) -> DeviceTokenModel:
        """Convert domain DeviceToken to SQLAlchemy model."""
        return DeviceTokenModel(
            id=token.id,
            user_id=token.user_id,
            device_id=token.device_id,
            device_name=token.device_name,
            refresh_token=token.refresh_token,
            token_jti=token.token_jti,
            last_used_at=token.last_used_at,
            expires_at=token.expires_at,
            created_at=token.created_at,
            revoked_at=token.revoked_at,
        )

    def _to_domain(self, model: DeviceTokenModel) -> DeviceToken:
        """Convert SQLAlchemy model to domain DeviceToken."""
        return DeviceToken(
            id=model.id,
            user_id=model.user_id,
            device_id=model.device_id,
            device_name=model.device_name,
            refresh_token=model.refresh_token,
            token_jti=model.token_jti,
            last_used_at=model.last_used_at,
            expires_at=model.expires_at,
            created_at=model.created_at,
            revoked_at=model.revoked_at,
        )

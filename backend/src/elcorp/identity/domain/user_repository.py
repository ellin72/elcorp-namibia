"""
Repository interfaces for identity domain.
These define contracts that infrastructure must implement.
"""

from abc import abstractmethod
from typing import Optional

from ...shared.infrastructure import Repository
from .user import User


class UserRepository(Repository[User]):
    """Repository interface for User aggregate."""

    @abstractmethod
    async def get_by_email(self, email: str) -> Optional[User]:
        """Find user by email."""
        pass

    @abstractmethod
    async def get_by_username(self, username: str) -> Optional[User]:
        """Find user by username."""
        pass

    @abstractmethod
    async def get_by_wallet(self, wallet_address: str) -> Optional[User]:
        """Find user by wallet address."""
        pass

    @abstractmethod
    async def email_exists(self, email: str) -> bool:
        """Check if email is already registered."""
        pass

    @abstractmethod
    async def username_exists(self, username: str) -> bool:
        """Check if username is already taken."""
        pass

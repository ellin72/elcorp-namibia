"""
Repository interface for DeviceToken entity.
"""

from abc import abstractmethod
from typing import Optional, List

from ...shared.infrastructure import Repository
from .device_token import DeviceToken


class DeviceTokenRepository(Repository[DeviceToken]):
    """Repository interface for DeviceToken entity."""

    @abstractmethod
    async def get_by_user_and_device(self, user_id: str, device_id: str) -> Optional[DeviceToken]:
        """Get token for specific user and device."""
        pass

    @abstractmethod
    async def get_all_by_user(self, user_id: str) -> List[DeviceToken]:
        """Get all device tokens for a user."""
        pass

    @abstractmethod
    async def revoke_device(self, user_id: str, device_id: str) -> None:
        """Revoke all tokens for a specific device."""
        pass

    @abstractmethod
    async def revoke_all_devices(self, user_id: str) -> None:
        """Revoke all device tokens for a user (logout all devices)."""
        pass

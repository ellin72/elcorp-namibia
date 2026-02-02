"""
Repository pattern - Abstract interface for data persistence.
All domain repositories inherit from this base class.
"""

from abc import ABC, abstractmethod
from typing import Generic, List, Optional, TypeVar

T = TypeVar("T")


class Repository(ABC, Generic[T]):
    """
    Abstract repository for managing aggregates.
    Each bounded context implements domain-specific repositories.
    """

    @abstractmethod
    async def add(self, entity: T) -> None:
        """Add a new entity to the repository."""
        pass

    @abstractmethod
    async def update(self, entity: T) -> None:
        """Update an existing entity."""
        pass

    @abstractmethod
    async def delete(self, entity_id: str) -> None:
        """Delete an entity (soft delete if applicable)."""
        pass

    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """Retrieve an entity by ID."""
        pass

    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[T]:
        """Retrieve all entities with pagination."""
        pass

    @abstractmethod
    async def exists(self, entity_id: str) -> bool:
        """Check if an entity exists."""
        pass

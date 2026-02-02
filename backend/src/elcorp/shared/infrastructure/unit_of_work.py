"""
Unit of Work pattern - Manages transactions and coordinates repositories.
"""

from abc import ABC, abstractmethod


class UnitOfWork(ABC):
    """
    Unit of Work pattern for managing transactions.
    Coordinates multiple repositories and provides commit/rollback.
    """

    @abstractmethod
    async def __aenter__(self):
        """Enter context manager."""
        return self

    @abstractmethod
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager and handle rollback if needed."""
        await self.rollback()

    @abstractmethod
    async def commit(self) -> None:
        """Commit all changes."""
        pass

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback all changes."""
        pass

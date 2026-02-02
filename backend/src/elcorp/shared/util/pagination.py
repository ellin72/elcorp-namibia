"""
Pagination - Standard pagination parameters and response format.
"""

from dataclasses import dataclass
from typing import List, TypeVar, Generic

T = TypeVar("T")


@dataclass
class PaginationParams:
    """Standard pagination parameters."""

    skip: int = 0
    limit: int = 10
    sort_by: str = "created_at"
    sort_order: str = "desc"  # 'asc' or 'desc'

    def __post_init__(self):
        """Validate pagination parameters."""
        if self.skip < 0:
            self.skip = 0
        if self.limit < 1:
            self.limit = 10
        if self.limit > 100:
            self.limit = 100  # Max 100 items per page
        if self.sort_order not in ("asc", "desc"):
            self.sort_order = "desc"


@dataclass
class PaginatedResponse(Generic[T]):
    """Standard paginated response format."""

    items: List[T]
    total: int
    skip: int
    limit: int
    page: int
    pages: int

    def to_dict(self):
        """Convert to dictionary for JSON response."""
        return {
            "items": self.items,
            "total": self.total,
            "page": self.page,
            "pages": self.pages,
            "limit": self.limit,
        }

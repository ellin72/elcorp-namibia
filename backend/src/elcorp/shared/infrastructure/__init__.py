"""
Shared infrastructure module - Database, audit, caching, and persistence abstractions.
"""

from .audit_log import AuditLog, AuditLogRepository
from .repository import Repository
from .unit_of_work import UnitOfWork

__all__ = [
    "AuditLog",
    "AuditLogRepository",
    "Repository",
    "UnitOfWork",
]

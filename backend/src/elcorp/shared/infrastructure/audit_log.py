"""
Audit logging - Immutable append-only audit trail with hash chaining for integrity.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4
import json
import hashlib


@dataclass
class AuditLog:
    """
    Immutable audit log entry with blockchain-style integrity checking.
    Each entry includes a hash of the previous entry, creating a chain.
    """

    entry_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=datetime.utcnow)
    actor_id: str = ""  # User ID who performed the action
    action: str = ""  # 'create', 'update', 'delete', 'login', etc.
    resource_type: str = ""  # 'User', 'ServiceRequest', etc.
    resource_id: str = ""  # ID of the affected resource
    changes: Dict[str, Any] = field(default_factory=dict)  # Field-level changes
    ip_address: str = ""
    user_agent: str = ""
    status: str = "success"  # 'success' or 'failure'
    error_message: Optional[str] = None
    previous_hash: Optional[str] = None  # Hash of previous entry for chain integrity
    entry_hash: Optional[str] = None  # SHA256 hash of this entry

    def calculate_hash(self) -> str:
        """Calculate SHA256 hash of this entry."""
        data_to_hash = {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "actor_id": self.actor_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "changes": self.changes,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status,
            "previous_hash": self.previous_hash,
        }
        hash_input = json.dumps(data_to_hash, sort_keys=True, default=str)
        return hashlib.sha256(hash_input.encode()).hexdigest()

    def finalize(self):
        """Finalize the audit log entry by calculating its hash."""
        self.entry_hash = self.calculate_hash()

    def verify_integrity(self) -> bool:
        """Verify that the entry hash is correct."""
        return self.entry_hash == self.calculate_hash()

    def to_dict(self) -> Dict[str, Any]:
        """Convert audit log to dictionary for storage."""
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp.isoformat(),
            "actor_id": self.actor_id,
            "action": self.action,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "changes": self.changes,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "status": self.status,
            "error_message": self.error_message,
            "previous_hash": self.previous_hash,
            "entry_hash": self.entry_hash,
        }


class AuditLogRepository:
    """
    Repository for immutable audit logs.
    This is a shared infrastructure that all contexts use.
    """

    def __init__(self):
        self.logs: Dict[str, AuditLog] = {}

    async def append(self, log: AuditLog, previous_log: Optional[AuditLog] = None) -> None:
        """
        Append a new audit log entry (immutable).
        Links to previous entry for chain integrity.
        """
        if previous_log:
            log.previous_hash = previous_log.entry_hash

        log.finalize()
        self.logs[log.entry_id] = log

    async def get_by_resource(
        self, resource_type: str, resource_id: str, limit: int = 100
    ) -> list[AuditLog]:
        """Retrieve audit logs for a specific resource."""
        return [
            log
            for log in self.logs.values()
            if log.resource_type == resource_type and log.resource_id == resource_id
        ][-limit:]

    async def get_by_actor(
        self, actor_id: str, limit: int = 100
    ) -> list[AuditLog]:
        """Retrieve audit logs for a specific actor."""
        return [log for log in self.logs.values() if log.actor_id == actor_id][-limit:]

    async def verify_chain_integrity(self) -> bool:
        """
        Verify the integrity of the audit log chain.
        Checks that each entry's previous_hash matches the previous entry's hash.
        """
        log_list = sorted(self.logs.values(), key=lambda x: x.timestamp)
        for i, log in enumerate(log_list):
            if not log.verify_integrity():
                return False
            if i > 0 and log.previous_hash != log_list[i - 1].entry_hash:
                return False
        return True

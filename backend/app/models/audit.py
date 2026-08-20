from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AuditLogEntry(BaseModel):
    """
    Append-only Tamper-Evident Hash-Chained Audit Ledger Event.
    """
    event_id: str = Field(description="Unique UUID for this audit entry")
    sequence: int = Field(ge=0, description="Sequential index within the chain (0, 1, 2...)")
    timestamp: str = Field(description="ISO 8601 UTC timestamp string")
    chain_id: str = Field(description="Correlation chain ID")
    event_type: str = Field(description="Registered governance event type")
    actor: str = Field(description="Initiator / Delegator identity")
    target: str = Field(description="Target agent or tool gateway")
    task_id: Optional[str] = Field(default=None, description="Associated task ID")
    token_id: Optional[str] = Field(default=None, description="JTI of the active delegation token")
    parent_token_id: Optional[str] = Field(default=None, description="JTI of parent token")
    scopes: List[str] = Field(default_factory=list, description="Scopes evaluated")
    data_scope: Dict[str, Any] = Field(default_factory=dict, description="Customer / resource boundaries")
    decision: str = Field(description="Authorization decision: ALLOW | DENY")
    reason: str = Field(description="Human-readable decision explanation")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    previous_event_hash: str = Field(
        default="0" * 64,
        description="SHA-256 hash of the previous event (all zeroes for sequence 0)"
    )
    event_hash: str = Field(
        description="SHA-256(canonical_event_without_hash + previous_event_hash)"
    )


class ChainVerificationResult(BaseModel):
    """
    Tamper-evident verification result for an audit ledger chain.
    """
    chain_id: str
    valid: bool
    tampered: bool
    total_events: int
    verified_at: str
    broken_link_index: Optional[int] = None
    reason: Optional[str] = None
    events: Optional[List[AuditLogEntry]] = None

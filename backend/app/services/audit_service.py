import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.logging import logger
from app.core.security import compute_sha256, compute_canonical_json_hash
from app.db.session import DatabaseSession
from app.models.audit import AuditLogEntry, ChainVerificationResult

GENESIS_PREVIOUS_HASH = "0" * 64


class AuditService:
    """
    Tamper-Evident Hash-Chained Audit Ledger Service.
    Guarantees sequential event verification and complete lineage reconstructability.
    """
    # In-memory fallback buffer (keyed by chain_id) for fast testing and DB decoupling
    _in_memory_ledger: Dict[str, List[AuditLogEntry]] = {}

    @classmethod
    def compute_event_hash(cls, event_dict: Dict[str, Any], previous_hash: str) -> str:
        """
        Compute deterministic SHA-256 hash over canonical event fields + previous_hash:
        SHA-256(canonical_json(event_without_event_hash) + previous_hash)
        """
        data_copy = dict(event_dict)
        data_copy.pop("event_hash", None)
        data_copy.pop("_id", None)

        canonical_json = json.dumps(
            data_copy,
            sort_keys=True,
            separators=(",", ":"),
            default=str
        )
        combined = f"{canonical_json}{previous_hash}"
        return compute_sha256(combined)

    @classmethod
    async def record_event(
        cls,
        chain_id: str,
        event_type: str,
        actor: str,
        target: str,
        scopes: List[str],
        data_scope: Dict[str, Any],
        decision: str,
        reason: str,
        token_id: Optional[str] = None,
        parent_token_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLogEntry:
        """
        Append a new audit event to the tamper-evident hash-chained ledger.
        """
        return await cls.append_audit_event(
            chain_id=chain_id,
            event_type=event_type,
            actor=actor,
            target=target,
            scopes=scopes,
            data_scope=data_scope,
            decision=decision,
            reason=reason,
            token_id=token_id,
            parent_token_id=parent_token_id,
            task_id=task_id,
            metadata=metadata
        )

    @classmethod
    async def append_audit_event(
        cls,
        chain_id: str,
        event_type: str,
        actor: str,
        target: str,
        scopes: List[str],
        data_scope: Dict[str, Any],
        decision: str,
        reason: str,
        token_id: Optional[str] = None,
        parent_token_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AuditLogEntry:
        """
        Core append implementation ensuring cryptographic link to the previous event in the chain.
        """
        db = DatabaseSession.get_db()
        now_iso = datetime.now(timezone.utc).isoformat()
        event_uuid = f"evt_{uuid.uuid4().hex[:12]}"

        # 1. Determine Sequence & Previous Hash from DB or in-memory ledger
        last_event: Optional[Dict[str, Any]] = None
        if db is not None:
            try:
                last_event = await db["audit_logs"].find_one(
                    {"chain_id": chain_id},
                    sort=[("sequence", -1)]
                )
            except Exception as e:
                logger.error(f"Error querying last audit log in DB: {e}")

        if last_event is None and chain_id in cls._in_memory_ledger and cls._in_memory_ledger[chain_id]:
            last_entry = cls._in_memory_ledger[chain_id][-1]
            last_event = last_entry.model_dump()

        if last_event:
            sequence = last_event["sequence"] + 1
            previous_hash = last_event["event_hash"]
        else:
            sequence = 0
            previous_hash = GENESIS_PREVIOUS_HASH

        # 2. Build Event Dictionary without event_hash
        event_dict = {
            "event_id": event_uuid,
            "sequence": sequence,
            "timestamp": now_iso,
            "chain_id": chain_id,
            "event_type": event_type,
            "actor": actor,
            "target": target,
            "task_id": task_id,
            "token_id": token_id,
            "parent_token_id": parent_token_id,
            "scopes": scopes,
            "data_scope": data_scope,
            "decision": decision,
            "reason": reason,
            "metadata": metadata or {},
            "previous_event_hash": previous_hash
        }

        # 3. Compute SHA-256 Event Hash
        event_hash = cls.compute_event_hash(event_dict, previous_hash)
        event_dict["event_hash"] = event_hash

        entry = AuditLogEntry(**event_dict)

        # 4. Persist in memory buffer
        if chain_id not in cls._in_memory_ledger:
            cls._in_memory_ledger[chain_id] = []
        cls._in_memory_ledger[chain_id].append(entry)

        # 5. Persist in MongoDB
        if db is not None:
            try:
                await db["audit_logs"].insert_one(entry.model_dump())
            except Exception as e:
                logger.error(f"Failed to persist audit log entry [{event_uuid}] to MongoDB: {e}")

        logger.info(
            f"Audit [{event_type}] ({decision}): {actor} -> {target} | Seq: {sequence} | Reason: {reason}",
            extra={"extra_data": {"chain_id": chain_id, "token_id": token_id, "event_hash": event_hash[:12]}}
        )

        return entry

    @classmethod
    async def get_chain(cls, chain_id: str) -> List[AuditLogEntry]:
        """
        Retrieve complete chronological audit trail for a correlation chain.
        """
        db = DatabaseSession.get_db()
        if db is not None:
            try:
                cursor = db["audit_logs"].find({"chain_id": chain_id}).sort("sequence", 1)
                docs = await cursor.to_list(1000)
                if docs:
                    return [AuditLogEntry(**d) for d in docs]
            except Exception as e:
                logger.error(f"Error querying audit chain from MongoDB: {e}")

        # Fallback to in-memory ledger
        return cls._in_memory_ledger.get(chain_id, [])

    @classmethod
    async def verify_chain(cls, chain_id: str) -> ChainVerificationResult:
        """
        Verify the mathematical integrity and non-tampering of an audit ledger chain.
        Validates:
        1. Sequence continuity: 0, 1, 2, ..., N-1 with no missing steps.
        2. Cryptographic event hash matching: SHA-256(canonical_event + previous_hash) == event_hash.
        3. Backward hash link consistency: event[i].previous_event_hash == event[i-1].event_hash.
        """
        events = await cls.get_chain(chain_id)
        verified_at = datetime.now(timezone.utc).isoformat()

        if not events:
            return ChainVerificationResult(
                chain_id=chain_id,
                valid=False,
                tampered=False,
                total_events=0,
                verified_at=verified_at,
                reason=f"No audit records found for chain_id '{chain_id}'"
            )

        expected_prev_hash = GENESIS_PREVIOUS_HASH

        for idx, event in enumerate(events):
            # Check 1: Monotonic sequence
            if event.sequence != idx:
                reason = f"Broken sequence at position {idx}: expected sequence {idx}, found {event.sequence}."
                return ChainVerificationResult(
                    chain_id=chain_id,
                    valid=False,
                    tampered=True,
                    total_events=len(events),
                    verified_at=verified_at,
                    broken_link_index=idx,
                    reason=reason,
                    events=events
                )

            # Check 2: Backward link matching
            if event.previous_event_hash != expected_prev_hash:
                reason = (
                    f"Broken hash pointer at sequence {idx}: expected previous_event_hash "
                    f"'{expected_prev_hash[:12]}...', found '{event.previous_event_hash[:12]}...'."
                )
                return ChainVerificationResult(
                    chain_id=chain_id,
                    valid=False,
                    tampered=True,
                    total_events=len(events),
                    verified_at=verified_at,
                    broken_link_index=idx,
                    reason=reason,
                    events=events
                )

            # Check 3: Recompute SHA-256 hash over canonical payload
            recomputed_hash = cls.compute_event_hash(event.model_dump(), expected_prev_hash)
            if recomputed_hash != event.event_hash:
                reason = (
                    f"Tampered event data at sequence {idx} ({event.event_type}): "
                    f"stored hash '{event.event_hash[:12]}...' does not match recomputed hash '{recomputed_hash[:12]}...'."
                )
                return ChainVerificationResult(
                    chain_id=chain_id,
                    valid=False,
                    tampered=True,
                    total_events=len(events),
                    verified_at=verified_at,
                    broken_link_index=idx,
                    reason=reason,
                    events=events
                )

            expected_prev_hash = event.event_hash

        return ChainVerificationResult(
            chain_id=chain_id,
            valid=True,
            tampered=False,
            total_events=len(events),
            verified_at=verified_at,
            events=events
        )

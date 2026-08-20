import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from app.config import settings
from app.core.logging import logger
from app.core.exceptions import (
    GovernanceException,
    InvalidTokenSignatureException,
    TokenExpiredException,
    AudienceMismatchException,
    ScopeExpansionForbiddenException,
    DataScopeViolationException,
    InsufficientScopeException
)
from app.core.security import (
    sign_token_claims,
    decode_and_verify_token,
    compute_token_hash
)
from app.models.token import TokenClaims, DataScope
from app.services.scope_engine import (
    is_scope_subset,
    is_operation_allowed,
    is_data_scope_subset,
    is_customer_allowed,
    is_resource_allowed
)
from app.services.audit_service import AuditService
from app.db.session import DatabaseSession


# Server-Side Defined Root Authority Policies (Client cannot specify arbitrary root scopes)
ROOT_POLICIES: Dict[str, Dict[str, Any]] = {
    "financial_analysis_task": {
        "scopes": ["financials:read:all"],
        "resource": "customer_financials",
        "data_scope": {
            "customer_ids": ["*"]
        },
        "max_ttl": 300,
        "max_depth": 4
    },
    "single_customer_audit": {
        "scopes": ["financials:read:summary"],
        "resource": "customer_financials",
        "data_scope": {
            "customer_ids": ["*"]
        },
        "max_ttl": 180,
        "max_depth": 3
    },
    "metrics_overview_task": {
        "scopes": ["financials:read:metrics"],
        "resource": "customer_financials",
        "data_scope": {
            "customer_ids": ["*"]
        },
        "max_ttl": 120,
        "max_depth": 3
    }
}


class GovernorService:
    """
    Centralized Delegation Governor Service.
    Acts as the single authoritative Policy Decision Point (PDP) and Policy Enforcement Point (PEP).
    """

    @classmethod
    async def create_root_token(
        cls,
        task_name: str,
        target_agent: str = "agent_a",
        user_id: str = "user",
        ttl_seconds: Optional[int] = None
    ) -> Tuple[str, TokenClaims]:
        """
        Mint initial Root Delegation Token derived strictly from server-side ROOT_POLICIES.
        """
        if task_name not in ROOT_POLICIES:
            available_tasks = list(ROOT_POLICIES.keys())
            reason = f"Unknown task policy '{task_name}'. Available: {available_tasks}"
            # Record audit failure
            await AuditService.record_event(
                chain_id="UNKNOWN_CHAIN",
                event_type="DELEGATION_BLOCKED",
                actor=user_id,
                target=target_agent,
                scopes=[],
                data_scope={},
                decision="DENY",
                reason=reason
            )
            raise GovernanceException(
                message=reason,
                error_code="INVALID_TASK_POLICY",
                status_code=400,
                details={"requested_task": task_name, "available_tasks": available_tasks}
            )

        policy = ROOT_POLICIES[task_name]
        now = int(time.time())
        max_policy_ttl = policy.get("max_ttl", settings.DEFAULT_TOKEN_TTL_SECONDS)
        effective_ttl = min(ttl_seconds, max_policy_ttl) if ttl_seconds else max_policy_ttl
        exp = now + effective_ttl

        jti = f"urn:uuid:{uuid.uuid4()}"
        chain_id = f"urn:uuid:{uuid.uuid4()}"

        claims = TokenClaims(
            jti=jti,
            chain_id=chain_id,
            parent_jti=None,
            iss="delegation-governor",
            sub=user_id,
            aud=target_agent,
            scopes=policy["scopes"],
            resource=policy["resource"],
            data_scope=DataScope(**policy["data_scope"]),
            depth=0,
            max_depth=policy.get("max_depth", settings.MAX_DELEGATION_DEPTH),
            iat=now,
            exp=exp,
            parent_token_hash=None,
            nonce=uuid.uuid4().hex[:12]
        )

        signed_token = sign_token_claims(claims)
        token_hash = compute_token_hash(signed_token)

        # 1. Persist token metadata
        await cls._persist_token_record(
            token_id=jti,
            chain_id=chain_id,
            parent_token_id=None,
            delegator=user_id,
            delegatee=target_agent,
            scopes=claims.scopes,
            resource=claims.resource,
            data_scope=claims.data_scope.model_dump(),
            depth=0,
            max_depth=claims.max_depth,
            iat=now,
            exp=exp,
            token_hash=token_hash,
            parent_token_hash=None
        )

        # 2. Record audit log
        await AuditService.record_event(
            chain_id=chain_id,
            event_type="TOKEN_MINTED",
            actor=user_id,
            target=target_agent,
            scopes=claims.scopes,
            data_scope=claims.data_scope.model_dump(),
            decision="ALLOW",
            reason=f"Minted root token under server policy '{task_name}'",
            token_id=jti,
            parent_token_id=None
        )

        return signed_token, claims

    @classmethod
    async def derive_child_token(
        cls,
        parent_token: str,
        delegator_agent: str,
        delegatee_agent: str,
        requested_scopes: List[str],
        requested_data_scope: DataScope,
        ttl_seconds: Optional[int] = None
    ) -> Tuple[str, TokenClaims]:
        """
        Derive and sign a child delegation token.
        Executes all 12 validation checks; records audit event for any failure or success.
        """
        # Check 1, 2, 3: Verify parent signature, issuer, and expiration
        try:
            parent_claims = decode_and_verify_token(parent_token)
        except TokenExpiredException as e:
            await AuditService.record_event(
                chain_id="EXPIRED_CHAIN",
                event_type="TOKEN_EXPIRED",
                actor=delegator_agent,
                target=delegatee_agent,
                scopes=requested_scopes,
                data_scope=requested_data_scope.model_dump(),
                decision="DENY",
                reason=str(e)
            )
            raise e
        except Exception as e:
            await AuditService.record_event(
                chain_id="INVALID_CHAIN",
                event_type="TOKEN_INVALID",
                actor=delegator_agent,
                target=delegatee_agent,
                scopes=requested_scopes,
                data_scope=requested_data_scope.model_dump(),
                decision="DENY",
                reason=str(e)
            )
            raise e

        chain_id = parent_claims.chain_id

        # Check 4: Check audience (delegator must match parent.aud)
        if delegator_agent and parent_claims.aud != delegator_agent:
            reason = f"Audience mismatch: delegator '{delegator_agent}' is not parent token recipient '{parent_claims.aud}'."
            await AuditService.record_event(
                chain_id=chain_id,
                event_type="AUDIENCE_MISMATCH",
                actor=delegator_agent,
                target=delegatee_agent,
                scopes=requested_scopes,
                data_scope=requested_data_scope.model_dump(),
                decision="DENY",
                reason=reason,
                parent_token_id=parent_claims.jti
            )
            raise AudienceMismatchException(reason)

        # Check 5: Verify Depth Invariant
        child_depth = parent_claims.depth + 1
        if child_depth > parent_claims.max_depth:
            reason = f"Maximum delegation depth ({parent_claims.max_depth}) exceeded at hop {child_depth}."
            await AuditService.record_event(
                chain_id=chain_id,
                event_type="DELEGATION_BLOCKED",
                actor=delegator_agent,
                target=delegatee_agent,
                scopes=requested_scopes,
                data_scope=requested_data_scope.model_dump(),
                decision="DENY",
                reason=reason,
                parent_token_id=parent_claims.jti
            )
            raise GovernanceException(
                message=reason,
                error_code="MAX_DELEGATION_DEPTH_EXCEEDED",
                status_code=403,
                chain_id=chain_id
            )

        # Check 6: Verify Operational Scopes are subset
        scope_ok, scope_reason = is_scope_subset(parent_claims.scopes, requested_scopes)
        if not scope_ok:
            await AuditService.record_event(
                chain_id=chain_id,
                event_type="SCOPE_EXPANSION_BLOCKED",
                actor=delegator_agent,
                target=delegatee_agent,
                scopes=requested_scopes,
                data_scope=requested_data_scope.model_dump(),
                decision="DENY",
                reason=scope_reason,
                parent_token_id=parent_claims.jti
            )
            raise ScopeExpansionForbiddenException(
                message=scope_reason,
                details={"parent_scopes": parent_claims.scopes, "requested_scopes": requested_scopes},
                chain_id=chain_id
            )

        # Check 7: Verify Customer Data Scope is subset
        data_ok, data_reason = is_data_scope_subset(parent_claims.data_scope, requested_data_scope)
        if not data_ok:
            await AuditService.record_event(
                chain_id=chain_id,
                event_type="DATA_SCOPE_VIOLATION",
                actor=delegator_agent,
                target=delegatee_agent,
                scopes=requested_scopes,
                data_scope=requested_data_scope.model_dump(),
                decision="DENY",
                reason=data_reason,
                parent_token_id=parent_claims.jti
            )
            raise DataScopeViolationException(
                message=data_reason,
                details={"parent_customers": parent_claims.data_scope.customer_ids, "requested_customers": requested_data_scope.customer_ids},
                chain_id=chain_id
            )

        # Check 8: Time calculations
        now = int(time.time())
        remaining_parent_ttl = parent_claims.exp - now
        if remaining_parent_ttl <= 0:
            raise TokenExpiredException("Parent delegation token has expired.")

        effective_ttl = min(ttl_seconds, remaining_parent_ttl) if ttl_seconds else remaining_parent_ttl
        child_exp = now + effective_ttl

        parent_token_hash = compute_token_hash(parent_token)
        jti = f"urn:uuid:{uuid.uuid4()}"

        child_claims = TokenClaims(
            jti=jti,
            chain_id=chain_id,
            parent_jti=parent_claims.jti,
            iss="delegation-governor",
            sub=delegator_agent,
            aud=delegatee_agent,
            scopes=requested_scopes,
            resource=parent_claims.resource,
            data_scope=requested_data_scope,
            depth=child_depth,
            max_depth=parent_claims.max_depth,
            iat=now,
            exp=child_exp,
            parent_token_hash=parent_token_hash,
            nonce=uuid.uuid4().hex[:12]
        )

        signed_child_token = sign_token_claims(child_claims)
        child_token_hash = compute_token_hash(signed_child_token)

        # Persist child token metadata
        await cls._persist_token_record(
            token_id=jti,
            chain_id=chain_id,
            parent_token_id=parent_claims.jti,
            delegator=delegator_agent,
            delegatee=delegatee_agent,
            scopes=child_claims.scopes,
            resource=child_claims.resource,
            data_scope=child_claims.data_scope.model_dump(),
            depth=child_depth,
            max_depth=child_claims.max_depth,
            iat=now,
            exp=child_exp,
            token_hash=child_token_hash,
            parent_token_hash=parent_token_hash
        )

        # Record audit success
        await AuditService.record_event(
            chain_id=chain_id,
            event_type="DELEGATION_ALLOWED",
            actor=delegator_agent,
            target=delegatee_agent,
            scopes=child_claims.scopes,
            data_scope=child_claims.data_scope.model_dump(),
            decision="ALLOW",
            reason="Delegation passed all scope and data monotonicity checks",
            token_id=jti,
            parent_token_id=parent_claims.jti,
            metadata={"depth": child_depth}
        )

        return signed_child_token, child_claims

    @classmethod
    async def validate_token_full(
        cls,
        token: str,
        expected_audience: Optional[str] = None,
        required_operation: Optional[str] = None,
        target_customer_id: Optional[str] = None,
        target_resource: Optional[str] = None
    ) -> TokenClaims:
        """
        Comprehensive token evaluation against signature, expiry, audience, operation, customer, and resource.
        """
        claims = decode_and_verify_token(token, expected_audience=expected_audience)

        # 1. Resource check
        if target_resource:
            res_ok, res_reason = is_resource_allowed(claims.resource, target_resource)
            if not res_ok:
                raise GovernanceException(
                    message=res_reason,
                    error_code="RESOURCE_OUT_OF_SCOPE",
                    status_code=403,
                    chain_id=claims.chain_id
                )

        # 2. Operation scope check
        if required_operation:
            op_ok, op_reason = is_operation_allowed(claims.scopes, required_operation)
            if not op_ok:
                raise InsufficientScopeException(
                    message=op_reason,
                    details={"token_scopes": claims.scopes, "required_operation": required_operation},
                    chain_id=claims.chain_id
                )

        # 3. Customer data scope check
        if target_customer_id:
            cust_ok, cust_reason = is_customer_allowed(claims.data_scope, target_customer_id)
            if not cust_ok:
                raise DataScopeViolationException(
                    message=cust_reason,
                    details={"allowed_customers": claims.data_scope.customer_ids, "target_customer": target_customer_id},
                    chain_id=claims.chain_id
                )

        return claims

    @classmethod
    def verify_token(cls, token: str, expected_audience: Optional[str] = None) -> TokenClaims:
        """Verify token signature and claims."""
        return decode_and_verify_token(token, expected_audience=expected_audience)

    @classmethod
    def validate_token(cls, token: str, expected_audience: Optional[str] = None) -> TokenClaims:
        """Synchronous wrapper for signature & audience verification."""
        return cls.verify_token(token, expected_audience=expected_audience)

    @classmethod
    def hash_token(cls, token: str) -> str:
        """Compute SHA-256 hash of token string."""
        return compute_token_hash(token)

    @classmethod
    async def _persist_token_record(
        cls,
        token_id: str,
        chain_id: str,
        parent_token_id: Optional[str],
        delegator: str,
        delegatee: str,
        scopes: List[str],
        resource: str,
        data_scope: Dict[str, Any],
        depth: int,
        max_depth: int,
        iat: int,
        exp: int,
        token_hash: str,
        parent_token_hash: Optional[str]
    ) -> None:
        """Insert token record into MongoDB."""
        db = DatabaseSession.get_db()
        if db is None:
            return

        record = {
            "token_id": token_id,
            "chain_id": chain_id,
            "parent_token_id": parent_token_id,
            "delegator": delegator,
            "delegatee": delegatee,
            "scopes": scopes,
            "resource": resource,
            "data_scope": data_scope,
            "depth": depth,
            "max_depth": max_depth,
            "issued_at": datetime.fromtimestamp(iat, tz=timezone.utc),
            "expires_at": datetime.fromtimestamp(exp, tz=timezone.utc),
            "status": "ACTIVE",
            "token_hash": token_hash,
            "parent_token_hash": parent_token_hash,
            "created_at": datetime.now(timezone.utc)
        }

        try:
            await db["delegation_tokens"].insert_one(record)
        except Exception as e:
            logger.error(f"Failed to persist token record [{token_id}]: {e}")

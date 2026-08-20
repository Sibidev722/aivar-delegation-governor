from typing import Any, Dict
from fastapi import APIRouter, status

from app.core.exceptions import (
    GovernanceException,
    InsufficientScopeException,
    DataScopeViolationException,
    AudienceMismatchException,
    TokenExpiredException,
    InvalidTokenSignatureException
)
from app.core.security import decode_and_verify_token
from app.models.tool import ToolExecutionRequest, ToolExecutionResponse
from app.services.scope_engine import (
    is_scope_subset,
    is_operation_allowed,
    is_customer_allowed,
    is_resource_allowed,
    RejectionReason
)
from app.services.financial_tool import FinancialToolService
from app.services.audit_service import AuditService

router = APIRouter()

OPERATION_TO_SCOPE_MAP: Dict[str, str] = {
    "READ_SUMMARY": "financials:read:summary",
    "READ_METRICS": "financials:read:metrics",
    "READ_FINANCIALS": "financials:read:all",
    "WRITE_RECORD": "financials:write:record"
}


@router.post(
    "/execute",
    response_model=ToolExecutionResponse,
    status_code=status.HTTP_200_OK,
    summary="Governor-Gated Financial Tool Execution",
    description=(
        "Sole authorized gateway to execute financial tool operations. "
        "Validates Ed25519 token signature, expiration, agent audience, operational scope, "
        "and customer data scope prior to invoking the financial tool service."
    )
)
async def execute_gated_tool(request: ToolExecutionRequest) -> ToolExecutionResponse:
    op_upper = request.operation.strip().upper()
    cust_upper = request.customer_id.strip().upper()

    # 1. Validate operation existence
    if op_upper not in OPERATION_TO_SCOPE_MAP:
        raise GovernanceException(
            message=f"Unsupported tool operation '{request.operation}'. Supported: {list(OPERATION_TO_SCOPE_MAP.keys())}",
            error_code="UNSUPPORTED_TOOL_OPERATION",
            status_code=status.HTTP_400_BAD_REQUEST
        )

    required_scope = OPERATION_TO_SCOPE_MAP[op_upper]

    # 2. Decode & Verify Token Cryptographic Authenticity & Expiry
    try:
        claims = decode_and_verify_token(request.token)
    except TokenExpiredException as e:
        await AuditService.record_event(
            chain_id="EXPIRED_CHAIN",
            event_type="TOKEN_EXPIRED",
            actor=request.agent_id,
            target=f"financial_tool:{op_upper}",
            scopes=[required_scope],
            data_scope={"customer_id": cust_upper},
            decision="DENY",
            reason=str(e)
        )
        raise e
    except Exception as e:
        await AuditService.record_event(
            chain_id="INVALID_CHAIN",
            event_type="TOKEN_INVALID",
            actor=request.agent_id,
            target=f"financial_tool:{op_upper}",
            scopes=[required_scope],
            data_scope={"customer_id": cust_upper},
            decision="DENY",
            reason=str(e)
        )
        raise e

    chain_id = claims.chain_id

    # 3. Check Audience (Caller must be the designated agent audience)
    if claims.aud != request.agent_id:
        reason = f"Audience mismatch: caller '{request.agent_id}' is not the token delegatee '{claims.aud}'."
        await AuditService.record_event(
            chain_id=chain_id,
            event_type="AUDIENCE_MISMATCH",
            actor=request.agent_id,
            target=f"financial_tool:{op_upper}",
            scopes=claims.scopes,
            data_scope={"customer_id": cust_upper},
            decision="DENY",
            reason=reason,
            token_id=claims.jti
        )
        raise AudienceMismatchException(reason)

    # 4. Check Resource Domain
    res_ok, res_reason = is_resource_allowed(claims.resource, request.resource)
    if not res_ok:
        await AuditService.record_event(
            chain_id=chain_id,
            event_type="TOOL_BLOCKED",
            actor=request.agent_id,
            target=f"financial_tool:{op_upper}",
            scopes=claims.scopes,
            data_scope={"customer_id": cust_upper},
            decision="DENY",
            reason=res_reason,
            token_id=claims.jti
        )
        raise GovernanceException(
            message=res_reason,
            error_code=RejectionReason.RESOURCE_OUT_OF_SCOPE.value,
            status_code=status.HTTP_403_FORBIDDEN,
            chain_id=chain_id
        )

    # 5. Check Operational Scope Authorization
    op_ok, op_reason = is_operation_allowed(claims.scopes, required_scope)
    if not op_ok:
        await AuditService.record_event(
            chain_id=chain_id,
            event_type="TOOL_BLOCKED",
            actor=request.agent_id,
            target=f"financial_tool:{op_upper}",
            scopes=claims.scopes,
            data_scope={"customer_id": cust_upper},
            decision="DENY",
            reason=op_reason,
            token_id=claims.jti
        )
        raise InsufficientScopeException(
            message=op_reason,
            details={"token_scopes": claims.scopes, "required_scope": required_scope, "operation": op_upper},
            chain_id=chain_id
        )

    # 6. Check Customer Data Scope Authorization
    cust_ok, cust_reason = is_customer_allowed(claims.data_scope, cust_upper)
    if not cust_ok:
        await AuditService.record_event(
            chain_id=chain_id,
            event_type="DATA_SCOPE_VIOLATION",
            actor=request.agent_id,
            target=f"financial_tool:{op_upper}",
            scopes=claims.scopes,
            data_scope={"customer_id": cust_upper, "allowed": claims.data_scope.customer_ids},
            decision="DENY",
            reason=cust_reason,
            token_id=claims.jti
        )
        raise DataScopeViolationException(
            message=cust_reason,
            details={"allowed_customers": claims.data_scope.customer_ids, "target_customer": cust_upper},
            chain_id=chain_id
        )

    # 7. Execute Protected Tool Operation (Only reachable when all checks pass)
    tool_output = await FinancialToolService.execute_operation(
        operation=op_upper,
        customer_id=cust_upper,
        payload=request.payload
    )

    # 8. Record Audit Success Event
    audit_entry = await AuditService.record_event(
        chain_id=chain_id,
        event_type="TOOL_ALLOWED",
        actor=request.agent_id,
        target=f"financial_tool:{op_upper}",
        scopes=claims.scopes,
        data_scope={"customer_id": cust_upper},
        decision="ALLOW",
        reason=f"Operation '{op_upper}' successfully executed on customer '{cust_upper}'",
        token_id=claims.jti,
        metadata={"task_id": request.task_id}
    )

    return ToolExecutionResponse(
        status="SUCCESS",
        tool_name="financial_records_tool",
        operation=op_upper,
        resource=request.resource,
        customer_id=cust_upper,
        executed_by=request.agent_id,
        chain_id=chain_id,
        token_id=claims.jti,
        data=tool_output,
        audit_event_id=audit_entry.event_id
    )

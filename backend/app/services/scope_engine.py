from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from app.models.token import DataScope


class RejectionReason(str, Enum):
    INSUFFICIENT_OPERATION_SCOPE = "INSUFFICIENT_OPERATION_SCOPE"
    SCOPE_EXPANSION_FORBIDDEN = "SCOPE_EXPANSION_FORBIDDEN"
    DATA_SCOPE_VIOLATION = "DATA_SCOPE_VIOLATION"
    RESOURCE_OUT_OF_SCOPE = "RESOURCE_OUT_OF_SCOPE"
    AUDIENCE_MISMATCH = "AUDIENCE_MISMATCH"
    TOKEN_EXPIRED = "TOKEN_EXPIRED"
    INVALID_SIGNATURE = "INVALID_SIGNATURE"
    REVOKED_TOKEN = "REVOKED_TOKEN"
    DELEGATION_DEPTH_EXCEEDED = "DELEGATION_DEPTH_EXCEEDED"


READ_HIERARCHY = {
    "financials:read:all": 3,
    "financials:read:metrics": 2,
    "financials:read:summary": 1
}

WRITE_SCOPES = {
    "financials:write:record",
    "financials:write:all"
}


def normalize_customer_id(customer_id: str) -> str:
    """
    Normalizes customer IDs to consistent 4-digit padded format (CUST-0001 to CUST-0500).
    Maps CUST-101 -> CUST-0101, CUST-1 -> CUST-0001, CUST-0250 -> CUST-0250 seamlessly.
    """
    if not customer_id:
        return customer_id
    cid = customer_id.strip().upper()
    if cid.startswith("CUST-"):
        num_part = cid.replace("CUST-", "")
        if num_part.isdigit():
            val = int(num_part)
            if 1 <= val <= 500:
                return f"CUST-{val:04d}"
    return cid


def is_scope_subset(
    parent_scopes: List[str],
    child_scopes: List[str]
) -> Tuple[bool, Optional[str]]:
    """
    Verifies that child scopes form a strict subset of parent scopes.
    Rules:
    - Special root scope 'financials:read:all' can grant any 'financials:read:*' scope.
    - 'financials:read:summary' CANNOT grant 'financials:read:all' or 'financials:write:*'.
    - Child cannot request scopes not present in parent scope set.
    """
    p_set = set(p.strip().lower() for p in parent_scopes)
    c_set = set(c.strip().lower() for c in child_scopes)

    # Super-scope expansion handler
    if "financials:read:all" in p_set:
        unauthorized = set()
        for c in c_set:
            if not (c.startswith("financials:read:") or c == "financials:read:all"):
                unauthorized.add(c)
        if unauthorized:
            return (
                False,
                f"{RejectionReason.SCOPE_EXPANSION_FORBIDDEN.value}: Parent scope 'financials:read:all' "
                f"cannot grant write/admin scopes {list(unauthorized)}."
            )
        return True, None

    # Check direct subset
    unauthorized = c_set - p_set
    if unauthorized:
        return (
            False,
            f"{RejectionReason.SCOPE_EXPANSION_FORBIDDEN.value}: Requested scopes {list(unauthorized)} "
            f"exceed parent authority {list(p_set)}."
        )

    return True, None


def is_operation_allowed(
    token_scopes: List[str],
    required_scope: str
) -> Tuple[bool, Optional[str]]:
    """
    Verifies that token holds the required scope for a target operation.
    """
    t_set = set(s.strip().lower() for s in token_scopes)
    req = required_scope.strip().lower()

    if "financials:read:all" in t_set and req.startswith("financials:read:"):
        return True, None

    if req in t_set:
        return True, None

    return (
        False,
        f"{RejectionReason.INSUFFICIENT_OPERATION_SCOPE.value}: Operation requires scope '{required_scope}' "
        f"but token only holds scopes {list(t_set)}."
    )


def is_data_scope_subset(
    parent_data_scope: Union[DataScope, Dict[str, Any]],
    child_data_scope: Union[DataScope, Dict[str, Any]]
) -> Tuple[bool, Optional[str]]:
    """
    Verifies that child customer IDs form a subset of parent customer IDs.
    Normalizes customer IDs so CUST-101 and CUST-0101 match cleanly.
    """
    p_ids = (
        parent_data_scope.customer_ids
        if isinstance(parent_data_scope, DataScope)
        else parent_data_scope.get("customer_ids", [])
    )
    c_ids = (
        child_data_scope.customer_ids
        if isinstance(child_data_scope, DataScope)
        else child_data_scope.get("customer_ids", [])
    )

    parent_set = set(normalize_customer_id(p) for p in p_ids)
    child_set = set(normalize_customer_id(c) for c in c_ids)

    # Rule 1: If parent has wildcard (*), child is free to choose any customer IDs or wildcard
    if "*" in parent_set:
        return True, None

    # Rule 2: If child requests wildcard (*) but parent only has specific IDs -> REJECT
    if "*" in child_set and "*" not in parent_set:
        return (
            False,
            f"{RejectionReason.DATA_SCOPE_VIOLATION.value}: Child requested wildcard '*' "
            f"access but parent only holds bounded customer scope {list(parent_set)}."
        )

    # Rule 3: Child set must be a subset of parent set
    unauthorized_ids = child_set - parent_set
    if unauthorized_ids:
        return (
            False,
            f"{RejectionReason.DATA_SCOPE_VIOLATION.value}: Requested customer IDs {list(unauthorized_ids)} "
            f"exceed parent customer authority {list(parent_set)}."
        )

    return True, None


def is_customer_allowed(
    data_scope: Union[DataScope, Dict[str, Any]],
    customer_id: str
) -> Tuple[bool, Optional[str]]:
    """
    Validates whether a specific customer_id is accessible under the given data scope.
    Applies normalization so CUST-101 resolves to CUST-0101.
    """
    c_ids = (
        data_scope.customer_ids
        if isinstance(data_scope, DataScope)
        else data_scope.get("customer_ids", [])
    )
    allowed_set = set(normalize_customer_id(c) for c in c_ids)
    target = normalize_customer_id(customer_id)

    if "*" in allowed_set or target in allowed_set:
        return True, None

    return (
        False,
        f"{RejectionReason.DATA_SCOPE_VIOLATION.value}: Access to customer '{customer_id}' "
        f"is prohibited by data scope {list(allowed_set)}."
    )


def is_resource_allowed(
    token_resource: str,
    requested_resource: str
) -> Tuple[bool, Optional[str]]:
    """
    Validates resource domain matching.
    """
    if token_resource.strip().lower() == requested_resource.strip().lower():
        return True, None

    return (
        False,
        f"{RejectionReason.RESOURCE_OUT_OF_SCOPE.value}: Token resource domain '{token_resource}' "
        f"does not match requested resource domain '{requested_resource}'."
    )

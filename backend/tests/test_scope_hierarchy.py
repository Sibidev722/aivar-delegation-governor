import pytest
from app.models.token import DataScope
from app.services.scope_engine import (
    RejectionReason,
    is_scope_subset,
    is_operation_allowed,
    is_data_scope_subset,
    is_customer_allowed,
    is_resource_allowed
)


# ==============================================================================
# 1. Scope Monotonicity & Hierarchy Tests (is_scope_subset)
# ==============================================================================

def test_read_hierarchy_monotonic_allow():
    """Verify valid monotonic reduction in read hierarchy."""
    # READ ALL -> READ SUMMARY
    ok, reason = is_scope_subset(["financials:read:all"], ["financials:read:summary"])
    assert ok is True
    assert reason is None

    # READ SUMMARY -> READ METRICS
    ok, reason = is_scope_subset(["financials:read:summary"], ["financials:read:metrics"])
    assert ok is True
    assert reason is None

    # READ ALL -> READ METRICS
    ok, reason = is_scope_subset(["financials:read:all"], ["financials:read:metrics"])
    assert ok is True
    assert reason is None

    # Exact match: READ ALL -> READ ALL
    ok, reason = is_scope_subset(["financials:read:all"], ["financials:read:all"])
    assert ok is True
    assert reason is None


def test_read_hierarchy_expansion_rejected():
    """Verify narrower read scope attempting to delegate broader read scope is blocked."""
    # READ METRICS -> READ SUMMARY
    ok, reason = is_scope_subset(["financials:read:metrics"], ["financials:read:summary"])
    assert ok is False
    assert RejectionReason.SCOPE_EXPANSION_FORBIDDEN.value in reason

    # READ METRICS -> READ ALL
    ok, reason = is_scope_subset(["financials:read:metrics"], ["financials:read:all"])
    assert ok is False
    assert RejectionReason.SCOPE_EXPANSION_FORBIDDEN.value in reason

    # READ SUMMARY -> READ ALL
    ok, reason = is_scope_subset(["financials:read:summary"], ["financials:read:all"])
    assert ok is False
    assert RejectionReason.SCOPE_EXPANSION_FORBIDDEN.value in reason


def test_read_never_implies_write():
    """CRITICAL: Verify read scopes can NEVER grant write permissions."""
    # READ ALL -> WRITE
    ok, reason = is_scope_subset(["financials:read:all"], ["financials:write:record"])
    assert ok is False
    assert RejectionReason.SCOPE_EXPANSION_FORBIDDEN.value in reason
    assert "Read never implies Write" in reason

    # READ SUMMARY -> WRITE
    ok, reason = is_scope_subset(["financials:read:summary"], ["financials:write:record"])
    assert ok is False
    assert RejectionReason.SCOPE_EXPANSION_FORBIDDEN.value in reason

    # READ METRICS -> WRITE
    ok, reason = is_scope_subset(["financials:read:metrics"], ["financials:write:record"])
    assert ok is False
    assert RejectionReason.SCOPE_EXPANSION_FORBIDDEN.value in reason


def test_write_permissions_delegation():
    """Verify write scopes isolation."""
    # WRITE -> WRITE
    ok, reason = is_scope_subset(["financials:write:record"], ["financials:write:record"])
    assert ok is True
    assert reason is None

    # WRITE -> READ (Write does not imply Read)
    ok, reason = is_scope_subset(["financials:write:record"], ["financials:read:all"])
    assert ok is False
    assert RejectionReason.SCOPE_EXPANSION_FORBIDDEN.value in reason


def test_unknown_scopes_rejected():
    """Verify unknown or arbitrary scopes are immediately blocked."""
    ok, reason = is_scope_subset(["financials:read:all"], ["admin:root:access"])
    assert ok is False
    assert "Unknown child scope" in reason


# ==============================================================================
# 2. Operation Execution Allowance (is_operation_allowed)
# ==============================================================================

def test_operation_allowed_read_levels():
    """Test operational execution against token permissions."""
    # Token with READ ALL
    assert is_operation_allowed(["financials:read:all"], "financials:read:all")[0] is True
    assert is_operation_allowed(["financials:read:all"], "financials:read:summary")[0] is True
    assert is_operation_allowed(["financials:read:all"], "financials:read:metrics")[0] is True
    
    # Token with READ ALL attempting WRITE
    ok, reason = is_operation_allowed(["financials:read:all"], "financials:write:record")
    assert ok is False
    assert RejectionReason.INSUFFICIENT_OPERATION_SCOPE.value in reason

    # Token with READ SUMMARY
    assert is_operation_allowed(["financials:read:summary"], "financials:read:summary")[0] is True
    assert is_operation_allowed(["financials:read:summary"], "financials:read:metrics")[0] is True
    
    # Token with READ SUMMARY attempting READ ALL
    ok, reason = is_operation_allowed(["financials:read:summary"], "financials:read:all")
    assert ok is False
    assert RejectionReason.INSUFFICIENT_OPERATION_SCOPE.value in reason

    # Token with READ METRICS attempting READ SUMMARY
    ok, reason = is_operation_allowed(["financials:read:metrics"], "financials:read:summary")
    assert ok is False
    assert RejectionReason.INSUFFICIENT_OPERATION_SCOPE.value in reason


# ==============================================================================
# 3. Data Scope Subsets (is_data_scope_subset)
# ==============================================================================

def test_data_scope_subset_valid():
    """Test valid customer data scope narrowing."""
    parent = DataScope(customer_ids=["CUST-101", "CUST-102"])
    
    # Narrow to single customer
    child_single = DataScope(customer_ids=["CUST-101"])
    ok, reason = is_data_scope_subset(parent, child_single)
    assert ok is True
    assert reason is None

    # Equal scope
    child_equal = DataScope(customer_ids=["CUST-101", "CUST-102"])
    ok, reason = is_data_scope_subset(parent, child_equal)
    assert ok is True
    assert reason is None


def test_data_scope_subset_violations():
    """Test data scope escalation violations."""
    parent = DataScope(customer_ids=["CUST-101", "CUST-102"])

    # Attempting customer outside parent scope
    child_unauthorized = DataScope(customer_ids=["CUST-103"])
    ok, reason = is_data_scope_subset(parent, child_unauthorized)
    assert ok is False
    assert RejectionReason.DATA_SCOPE_VIOLATION.value in reason
    assert "CUST-103" in reason

    # Attempting wildcard from bounded parent
    child_wildcard = DataScope(customer_ids=["*"])
    ok, reason = is_data_scope_subset(parent, child_wildcard)
    assert ok is False
    assert RejectionReason.DATA_SCOPE_VIOLATION.value in reason
    assert "wildcard" in reason.lower()


def test_data_scope_wildcard_parent():
    """Test wildcard parent authority."""
    parent_wildcard = DataScope(customer_ids=["*"])

    # Wildcard parent granting specific customer
    ok, reason = is_data_scope_subset(parent_wildcard, DataScope(customer_ids=["CUST-101"]))
    assert ok is True
    assert reason is None

    # Wildcard parent granting wildcard child
    ok, reason = is_data_scope_subset(parent_wildcard, DataScope(customer_ids=["*"]))
    assert ok is True
    assert reason is None


# ==============================================================================
# 4. Customer Access & Resource Validation (is_customer_allowed / is_resource_allowed)
# ==============================================================================

def test_customer_access_allow_and_block():
    """Test customer access check against token data scope."""
    scope = DataScope(customer_ids=["CUST-101"])
    
    # Authorized customer
    ok, reason = is_customer_allowed(scope, "CUST-101")
    assert ok is True
    assert reason is None

    # Unauthorized customer
    ok, reason = is_customer_allowed(scope, "CUST-102")
    assert ok is False
    assert RejectionReason.DATA_SCOPE_VIOLATION.value in reason

    # Wildcard scope allows any customer
    wildcard_scope = DataScope(customer_ids=["*"])
    assert is_customer_allowed(wildcard_scope, "CUST-999")[0] is True


def test_resource_domain_matching():
    """Test resource domain validation."""
    ok, reason = is_resource_allowed("customer_financials", "customer_financials")
    assert ok is True
    assert reason is None

    ok, reason = is_resource_allowed("customer_financials", "internal_payroll")
    assert ok is False
    assert RejectionReason.RESOURCE_OUT_OF_SCOPE.value in reason

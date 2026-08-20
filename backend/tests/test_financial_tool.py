import pytest
from httpx import AsyncClient

from app.services.governor_service import GovernorService
from app.services.financial_tool import FinancialToolService
from app.models.token import DataScope


@pytest.mark.asyncio
async def test_read_cust101_allowed(async_client: AsyncClient):
    """Test 1: READ_SUMMARY for CUST-101 with valid token is ALLOWED (200 OK)."""
    # 1. Mint root token for Agent A
    token_a, claims_a = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )

    # 2. Derive token for Agent C
    token_c, claims_c = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_c",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    # 3. Call Governor Tool Gateway
    res = await async_client.post(
        "/api/v1/governor/tools/execute",
        json={
            "task_id": "task_q1_review",
            "agent_id": "agent_c",
            "token": token_c,
            "operation": "READ_SUMMARY",
            "resource": "customer_financials",
            "customer_id": "CUST-101"
        }
    )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["operation"] == "READ_SUMMARY"
    assert data["customer_id"] in ["CUST-101", "CUST-0101"]
    assert data["executed_by"] == "agent_c"
    assert "customer_name" in data["data"]
    assert "balances" in data["data"]


@pytest.mark.asyncio
async def test_write_cust101_with_read_token_blocked(async_client: AsyncClient, monkeypatch):
    """Test 2: WRITE_RECORD with a READ-only token is BLOCKED (403), tool NOT executed."""
    # Track whether tool execute_operation was called
    tool_called = False
    original_exec = FinancialToolService.execute_operation

    async def mock_exec(*args, **kwargs):
        nonlocal tool_called
        tool_called = True
        return await original_exec(*args, **kwargs)

    monkeypatch.setattr(FinancialToolService, "execute_operation", mock_exec)

    # Token with READ ONLY scope
    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )
    token_c, _ = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_c",
        requested_scopes=["financials:read:all"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    # Attempt WRITE operation
    res = await async_client.post(
        "/api/v1/governor/tools/execute",
        json={
            "task_id": "task_write_attempt",
            "agent_id": "agent_c",
            "token": token_c,
            "operation": "WRITE_RECORD",
            "resource": "customer_financials",
            "customer_id": "CUST-101",
            "payload": {"summary": "Malicious override"}
        }
    )

    assert res.status_code == 403
    error_data = res.json()
    assert error_data["error_code"] == "INSUFFICIENT_OPERATION_SCOPE"
    assert tool_called is False, "Financial tool must NOT be executed for blocked requests"


@pytest.mark.asyncio
async def test_read_cust102_with_cust101_token_blocked(async_client: AsyncClient, monkeypatch):
    """Test 3: READ CUST-102 with a CUST-101 scoped token is BLOCKED (403), tool NOT executed."""
    tool_called = False
    original_exec = FinancialToolService.execute_operation

    async def mock_exec(*args, **kwargs):
        nonlocal tool_called
        tool_called = True
        return await original_exec(*args, **kwargs)

    monkeypatch.setattr(FinancialToolService, "execute_operation", mock_exec)

    # Token scoped exclusively to CUST-101
    token_a, _ = await GovernorService.create_root_token(
        task_name="single_customer_audit",
        target_agent="agent_a"
    )
    token_c, _ = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_c",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    # Attempt to read CUST-102
    res = await async_client.post(
        "/api/v1/governor/tools/execute",
        json={
            "task_id": "task_cross_customer_attempt",
            "agent_id": "agent_c",
            "token": token_c,
            "operation": "READ_SUMMARY",
            "resource": "customer_financials",
            "customer_id": "CUST-102"
        }
    )

    assert res.status_code == 403
    error_data = res.json()
    assert error_data["error_code"] == "DATA_SCOPE_VIOLATION"
    assert "CUST-102" in error_data["message"]
    assert tool_called is False, "Financial tool must NOT be executed for cross-customer data violation"


@pytest.mark.asyncio
async def test_read_financials_with_metrics_token_blocked(async_client: AsyncClient):
    """Test 4: READ_FINANCIALS (all) with a READ_METRICS token is BLOCKED (403)."""
    token_a, _ = await GovernorService.create_root_token(
        task_name="metrics_overview_task",
        target_agent="agent_a"
    )
    token_c, _ = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_c",
        requested_scopes=["financials:read:metrics"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    # Attempt to read full detailed financials
    res = await async_client.post(
        "/api/v1/governor/tools/execute",
        json={
            "task_id": "task_escalate_attempt",
            "agent_id": "agent_c",
            "token": token_c,
            "operation": "READ_FINANCIALS",
            "resource": "customer_financials",
            "customer_id": "CUST-101"
        }
    )

    assert res.status_code == 403
    assert res.json()["error_code"] == "INSUFFICIENT_OPERATION_SCOPE"


@pytest.mark.asyncio
async def test_read_metrics_with_summary_token_allowed(async_client: AsyncClient):
    """Test 5: READ_METRICS with a READ_SUMMARY token is ALLOWED (200 OK)."""
    token_a, _ = await GovernorService.create_root_token(
        task_name="single_customer_audit",
        target_agent="agent_a"
    )
    token_c, _ = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_c",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    res = await async_client.post(
        "/api/v1/governor/tools/execute",
        json={
            "task_id": "task_metrics_query",
            "agent_id": "agent_c",
            "token": token_c,
            "operation": "READ_METRICS",
            "resource": "customer_financials",
            "customer_id": "CUST-101"
        }
    )

    assert res.status_code == 200
    data = res.json()
    assert "metrics" in data["data"]
    assert "runway_months" in data["data"]["metrics"]


@pytest.mark.asyncio
async def test_wrong_agent_audience_blocked(async_client: AsyncClient):
    """Test 6: Token issued for agent_b presented by agent_c is BLOCKED (403)."""
    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )
    token_b, _ = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_b",  # Designated for Agent B
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    # Agent C attempts to use Agent B's token directly
    res = await async_client.post(
        "/api/v1/governor/tools/execute",
        json={
            "task_id": "task_spoof_attempt",
            "agent_id": "agent_c",  # Calling as Agent C
            "token": token_b,
            "operation": "READ_SUMMARY",
            "resource": "customer_financials",
            "customer_id": "CUST-101"
        }
    )

    assert res.status_code == 403
    assert res.json()["error_code"] == "AUDIENCE_MISMATCH"

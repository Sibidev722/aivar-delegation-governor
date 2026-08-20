import time
import pytest
from httpx import AsyncClient

from app.services.governor_service import GovernorService
from app.services.agent_client import AgentHTTPClient
from app.services.financial_tool import FinancialToolService
from app.models.token import DataScope


@pytest.mark.asyncio
async def test_agent_c_execute_happy_path(async_client: AsyncClient):
    """
    Test 1: Normal operation: Agent C receives valid token, calls Governor tool gateway,
    and returns customer financial dataset.
    """
    # Setup test client injection so Agent C calls live in-process test app for tool gateway
    AgentHTTPClient.set_test_client(async_client)

    # 1. Mint root for A
    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )

    # 2. Derive token for B
    token_b, _ = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_b",
        requested_scopes=["financials:read:all"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    # 3. Derive token for C
    token_c, claims_c = await GovernorService.derive_child_token(
        parent_token=token_b,
        delegator_agent="agent_b",
        delegatee_agent="agent_c",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    # 4. Execute Agent C
    res = await async_client.post(
        "/api/v1/agents/agent-c/execute",
        json={
            "task_id": "task_c_01",
            "chain_id": claims_c.chain_id,
            "originating_user": "USER-001",
            "token": token_c,
            "customer_id": "CUST-101",
            "operation": "READ_SUMMARY"
        }
    )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["authorization"] == "ALLOWED"
    assert data["customer_id"] in ["CUST-101", "CUST-0101"]
    assert "customer_name" in data["data"]
    assert "balances" in data["data"]


@pytest.mark.asyncio
async def test_agent_c_unauthorized_write_rejected(async_client: AsyncClient, monkeypatch):
    """
    Test 2: Agent C with read token attempts WRITE_RECORD.
    Governor tool gateway rejects with 403 INSUFFICIENT_OPERATION_SCOPE.
    Financial tool service is NOT executed.
    """
    AgentHTTPClient.set_test_client(async_client)
    tool_called = False
    original_exec = FinancialToolService.execute_operation

    async def spy_exec(*args, **kwargs):
        nonlocal tool_called
        tool_called = True
        return await original_exec(*args, **kwargs)

    monkeypatch.setattr(FinancialToolService, "execute_operation", spy_exec)

    # Token with READ ONLY permissions
    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )
    token_c, claims_c = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_c",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    # Execute Agent C with attack simulation: write_attack
    res = await async_client.post(
        "/api/v1/agents/agent-c/execute",
        json={
            "task_id": "task_c_write",
            "chain_id": claims_c.chain_id,
            "originating_user": "USER-001",
            "token": token_c,
            "customer_id": "CUST-101",
            "operation": "WRITE_RECORD",
            "simulate_attack": "write_attack"
        }
    )

    assert res.status_code == 403
    error_data = res.json()
    assert "INSUFFICIENT_OPERATION_SCOPE" in error_data["error_code"]
    assert tool_called is False, "Financial tool must NOT be executed for unauthorized write"


@pytest.mark.asyncio
async def test_agent_c_cross_customer_attack_rejected(async_client: AsyncClient, monkeypatch):
    """
    Test 3: Agent C with CUST-101 token attempts to access CUST-102.
    Governor tool gateway rejects with 403 DATA_SCOPE_VIOLATION.
    """
    AgentHTTPClient.set_test_client(async_client)

    token_a, _ = await GovernorService.create_root_token(
        task_name="single_customer_audit",
        target_agent="agent_a"
    )
    token_c, claims_c = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_c",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    res = await async_client.post(
        "/api/v1/agents/agent-c/execute",
        json={
            "task_id": "task_c_cross",
            "chain_id": claims_c.chain_id,
            "originating_user": "USER-001",
            "token": token_c,
            "customer_id": "CUST-101",
            "simulate_attack": "cross_customer_attack"
        }
    )

    assert res.status_code == 403
    assert "DATA_SCOPE_VIOLATION" in res.json()["error_code"]


@pytest.mark.asyncio
async def test_agent_c_wrong_audience_rejected(async_client: AsyncClient):
    """
    Test 4: Token intended for Agent B presented directly to Agent C is rejected (403 AUDIENCE_MISMATCH).
    """
    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )
    token_b, claims_b = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_b",  # Designated for Agent B
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    res = await async_client.post(
        "/api/v1/agents/agent-c/execute",
        json={
            "task_id": "task_c_wrong_aud",
            "chain_id": claims_b.chain_id,
            "originating_user": "USER-001",
            "token": token_b,  # Aud is agent_b!
            "customer_id": "CUST-101",
            "operation": "READ_SUMMARY"
        }
    )

    assert res.status_code == 403
    assert res.json()["error_code"] == "AUDIENCE_MISMATCH"


@pytest.mark.asyncio
async def test_agent_c_expired_token_rejected(async_client: AsyncClient):
    """
    Test 5: Expired token presented to Agent C is rejected (401 TOKEN_EXPIRED).
    """
    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a",
        ttl_seconds=1
    )
    token_c, claims_c = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_c",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"]),
        ttl_seconds=1
    )

    time.sleep(1.1)

    res = await async_client.post(
        "/api/v1/agents/agent-c/execute",
        json={
            "task_id": "task_c_expired",
            "chain_id": claims_c.chain_id,
            "originating_user": "USER-001",
            "token": token_c,
            "customer_id": "CUST-101",
            "operation": "READ_SUMMARY"
        }
    )

    assert res.status_code == 401
    assert res.json()["error_code"] == "TOKEN_EXPIRED"

import time
import pytest
from httpx import AsyncClient

from app.services.governor_service import GovernorService
from app.services.agent_client import AgentHTTPClient
from app.services.financial_tool import FinancialToolService
from app.models.token import DataScope


@pytest.mark.asyncio
async def test_agent_b_execute_happy_path(async_client: AsyncClient, monkeypatch):
    """
    Test 1: Valid Agent A -> Agent B delegation.
    Agent B validates token, derives child token for Agent C, and dispatches HTTP call to Agent C.
    """
    agent_c_called = False
    received_token_in_c = None

    async def mock_post_to_agent_c(endpoint_path, payload, headers=None, timeout=None):
        nonlocal agent_c_called, received_token_in_c
        agent_c_called = True
        received_token_in_c = payload.get("token")
        assert endpoint_path == "/api/v1/agents/agent-c/execute"
        assert payload["customer_id"] == "CUST-101"
        return {
            "status": "completed",
            "task_id": payload["task_id"],
            "chain_id": payload["chain_id"],
            "delegation_chain": ["agent_c"],
            "operation": "READ_SUMMARY",
            "customer_id": "CUST-101",
            "authorization": "ALLOWED",
            "data": {"balances": {"operating": 1450000.00}}
        }

    monkeypatch.setattr(AgentHTTPClient, "post_to_agent", mock_post_to_agent_c)

    # 1. Mint Root for A
    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )

    # 2. Derive token for B
    token_b, claims_b = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_b",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    # 3. Execute Agent B
    res = await async_client.post(
        "/api/v1/agents/agent-b/execute",
        json={
            "task_id": "task_b_test",
            "chain_id": claims_b.chain_id,
            "originating_user": "USER-001",
            "token": token_b,
            "customer_id": "CUST-101",
            "task_type": "financial_analysis_task"
        }
    )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert "agent_b" in data["delegation_chain"]
    assert "agent_c" in data["delegation_chain"]
    assert agent_c_called is True
    assert received_token_in_c is not None


@pytest.mark.asyncio
async def test_agent_b_invalid_token_rejected(async_client: AsyncClient):
    """
    Test 2: Invalid/corrupted token signature presented to Agent B is rejected (401).
    """
    res = await async_client.post(
        "/api/v1/agents/agent-b/execute",
        json={
            "task_id": "task_invalid",
            "chain_id": "chain_dummy",
            "originating_user": "USER-001",
            "token": "invalid.jwt.token",
            "customer_id": "CUST-101",
            "task_type": "financial_analysis_task"
        }
    )

    assert res.status_code == 401
    assert res.json()["error_code"] == "INVALID_ED25519_SIGNATURE"


@pytest.mark.asyncio
async def test_agent_b_wrong_audience_rejected(async_client: AsyncClient):
    """
    Test 3: Token intended for Agent A presented directly to Agent B is rejected (403 AUDIENCE_MISMATCH).
    """
    # Token minted for agent_a (aud = "agent_a")
    token_a, claims_a = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )

    res = await async_client.post(
        "/api/v1/agents/agent-b/execute",
        json={
            "task_id": "task_wrong_aud",
            "chain_id": claims_a.chain_id,
            "originating_user": "USER-001",
            "token": token_a,  # Token audience is agent_a, not agent_b!
            "customer_id": "CUST-101",
            "task_type": "financial_analysis_task"
        }
    )

    assert res.status_code == 403
    data = res.json()
    assert data["error_code"] == "AUDIENCE_MISMATCH"
    assert "agent_b" in data["message"]


@pytest.mark.asyncio
async def test_agent_b_expired_token_rejected(async_client: AsyncClient):
    """
    Test 4: Expired token presented to Agent B is rejected (401 TOKEN_EXPIRED).
    """
    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a",
        ttl_seconds=1
    )
    token_b, claims_b = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_b",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"]),
        ttl_seconds=1
    )

    time.sleep(1.1)

    res = await async_client.post(
        "/api/v1/agents/agent-b/execute",
        json={
            "task_id": "task_expired",
            "chain_id": claims_b.chain_id,
            "originating_user": "USER-001",
            "token": token_b,
            "customer_id": "CUST-101",
            "task_type": "financial_analysis_task"
        }
    )

    assert res.status_code == 401
    assert res.json()["error_code"] == "TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_agent_b_scope_escalation_to_c_rejected(async_client: AsyncClient):
    """
    Test 5: Agent B attempting to delegate WRITE to Agent C is rejected by Governor (403).
    """
    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )
    token_b, claims_b = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_b",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    res = await async_client.post(
        "/api/v1/agents/agent-b/execute",
        json={
            "task_id": "task_escalate",
            "chain_id": claims_b.chain_id,
            "originating_user": "USER-001",
            "token": token_b,
            "customer_id": "CUST-101",
            "task_type": "financial_analysis_task",
            "simulate_attack": "escalate_write_to_c"
        }
    )

    assert res.status_code == 403
    assert res.json()["error_code"] == "SCOPE_EXPANSION_FORBIDDEN"


@pytest.mark.asyncio
async def test_agent_b_does_not_call_financial_tool_directly(async_client: AsyncClient, monkeypatch):
    """
    Test 6: Agent B must NEVER directly execute FinancialToolService.
    """
    financial_tool_called = False
    original_exec = FinancialToolService.execute_operation

    async def spy_exec(*args, **kwargs):
        nonlocal financial_tool_called
        financial_tool_called = True
        return await original_exec(*args, **kwargs)

    monkeypatch.setattr(FinancialToolService, "execute_operation", spy_exec)

    async def mock_agent_c(*args, **kwargs):
        return {"status": "completed", "data": "dummy"}

    monkeypatch.setattr(AgentHTTPClient, "post_to_agent", mock_agent_c)

    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )
    token_b, claims_b = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_b",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    await async_client.post(
        "/api/v1/agents/agent-b/execute",
        json={
            "task_id": "task_test",
            "chain_id": claims_b.chain_id,
            "originating_user": "USER-001",
            "token": token_b,
            "customer_id": "CUST-101",
            "task_type": "financial_analysis_task"
        }
    )

    assert financial_tool_called is False, "Agent B must NOT directly execute FinancialToolService"

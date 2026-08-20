import pytest
from httpx import AsyncClient
import httpx

from app.services.agent_client import AgentHTTPClient
from app.services.financial_tool import FinancialToolService


@pytest.mark.asyncio
async def test_agent_a_execute_happy_path(async_client: AsyncClient, monkeypatch):
    """
    Test: Agent A receives task, mints root token, derives child token for B,
    and dispatches HTTP call to Agent B.
    """
    agent_b_called = False
    received_token_in_b = None

    async def mock_post_to_agent(endpoint_path, payload, headers=None, timeout=None):
        nonlocal agent_b_called, received_token_in_b
        agent_b_called = True
        received_token_in_b = payload.get("token")
        assert endpoint_path == "/api/v1/agents/agent-b/execute"
        assert payload["customer_id"] in ["CUST-101", "CUST-0101"]
        assert payload["originating_user"] == "USER-001"
        return {
            "status": "completed",
            "task_id": payload["task_id"],
            "chain_id": payload["chain_id"],
            "delegation_chain": ["agent_b", "agent_c"],
            "operation": "READ_SUMMARY",
            "customer_id": "CUST-101",
            "authorization": "ALLOWED",
            "data": {"summary": "Acme Global Q1 Financial Review"}
        }

    monkeypatch.setattr(AgentHTTPClient, "post_to_agent", mock_post_to_agent)

    # Execute Agent A
    res = await async_client.post(
        "/api/v1/agents/agent-a/execute",
        json={
            "task_type": "financial_analysis_task",
            "originating_user": "USER-001",
            "customer_id": "CUST-101"
        }
    )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["authorization"] == "ALLOWED"
    assert data["customer_id"] in ["CUST-101", "CUST-0101"]
    assert "agent_a" in data["delegation_chain"]
    assert "agent_b" in data["delegation_chain"]
    assert agent_b_called is True
    assert received_token_in_b is not None


@pytest.mark.asyncio
async def test_agent_a_scope_escalation_attack_rejected(async_client: AsyncClient):
    """
    Test: Agent A attempting to escalate scope to WRITE for Agent B is blocked by Governor with 403.
    """
    res = await async_client.post(
        "/api/v1/agents/agent-a/execute",
        json={
            "task_type": "financial_analysis_task",
            "originating_user": "USER-001",
            "customer_id": "CUST-101",
            "simulate_attack": "escalate_write_to_b"
        }
    )

    assert res.status_code == 403
    data = res.json()
    assert data["error_code"] == "SCOPE_EXPANSION_FORBIDDEN"


@pytest.mark.asyncio
async def test_agent_a_data_scope_escalation_attack_rejected(async_client: AsyncClient):
    """
    Test: Agent A attempting to delegate unauthorized customer to Agent B is blocked with 403.
    """
    res = await async_client.post(
        "/api/v1/agents/agent-a/execute",
        json={
            "task_type": "single_customer_audit",  # Policy only allows CUST-101
            "originating_user": "USER-001",
            "customer_id": "CUST-101",
            "simulate_attack": "escalate_cust_to_b"
        }
    )

    assert res.status_code == 403
    data = res.json()
    assert data["error_code"] == "DATA_SCOPE_VIOLATION"


@pytest.mark.asyncio
async def test_agent_a_downstream_timeout_handling(async_client: AsyncClient, monkeypatch):
    """
    Test: Agent A handles downstream Agent B HTTP timeout gracefully with 504.
    """
    from app.core.exceptions import GovernanceException

    async def mock_post_timeout(*args, **kwargs):
        raise GovernanceException(
            message="Timeout communicating with downstream agent",
            error_code="AGENT_COMMUNICATION_TIMEOUT",
            status_code=504
        )

    monkeypatch.setattr(AgentHTTPClient, "post_to_agent", mock_post_timeout)

    res = await async_client.post(
        "/api/v1/agents/agent-a/execute",
        json={
            "task_type": "financial_analysis_task",
            "originating_user": "USER-001",
            "customer_id": "CUST-101"
        }
    )

    assert res.status_code == 504
    assert res.json()["error_code"] == "AGENT_COMMUNICATION_TIMEOUT"


@pytest.mark.asyncio
async def test_agent_a_does_not_call_financial_tool_directly(async_client: AsyncClient, monkeypatch):
    """
    Test: Agent A must NEVER directly execute FinancialToolService.
    """
    financial_tool_called = False
    original_exec = FinancialToolService.execute_operation

    async def spy_exec(*args, **kwargs):
        nonlocal financial_tool_called
        financial_tool_called = True
        return await original_exec(*args, **kwargs)

    monkeypatch.setattr(FinancialToolService, "execute_operation", spy_exec)

    async def mock_agent_b(*args, **kwargs):
        return {"status": "completed", "data": "dummy"}

    monkeypatch.setattr(AgentHTTPClient, "post_to_agent", mock_agent_b)

    await async_client.post(
        "/api/v1/agents/agent-a/execute",
        json={"task_type": "financial_analysis_task", "customer_id": "CUST-101"}
    )

    assert financial_tool_called is False, "Agent A must NOT directly execute FinancialToolService"

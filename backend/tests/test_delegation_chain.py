import pytest
from httpx import AsyncClient

from app.services.agent_client import AgentHTTPClient
from app.services.financial_tool import FinancialToolService
from app.db.session import DatabaseSession


@pytest.mark.asyncio
async def test_full_real_e2e_delegation_chain(async_client: AsyncClient, monkeypatch):
    """
    Test Phase 9: Real End-to-End Multi-Agent Pipeline:
    USER -> Agent A -> Agent B -> Agent C -> Governor -> Financial Tool -> MongoDB -> Result.
    
    Proves:
    1. Agent A actually calls Agent B via HTTP
    2. Agent B actually calls Agent C via HTTP
    3. Agent C actually calls Governor Tool Gateway via HTTP
    4. Governor validates tokens and executes Financial Tool on MongoDB
    5. Reconstructs dynamic delegation chain ["USER-001", "agent_a", "agent_b", "agent_c"]
    6. All tokens and audit events are properly persisted in DB.
    """
    # Configure in-process ASGI client for real HTTP agent routing
    AgentHTTPClient.set_test_client(async_client)

    # Instrument spies to prove each real hop executed
    hop_tracker = []
    original_post = AgentHTTPClient.post_to_agent

    async def spy_post_to_agent(endpoint_path, payload, headers=None, timeout=None):
        hop_tracker.append({
            "endpoint": endpoint_path,
            "task_id": payload.get("task_id"),
            "chain_id": payload.get("chain_id"),
            "token": payload.get("token")
        })
        return await original_post(endpoint_path, payload, headers=headers, timeout=timeout)

    monkeypatch.setattr(AgentHTTPClient, "post_to_agent", spy_post_to_agent)

    # 1. Trigger Agent A as USER-001
    user_payload = {
        "task_type": "financial_analysis_task",
        "originating_user": "USER-001",
        "customer_id": "CUST-101",
        "operation": "READ_SUMMARY"
    }

    response = await async_client.post(
        "/api/v1/agents/agent-a/execute",
        json=user_payload
    )

    assert response.status_code == 200
    res_data = response.json()

    # 2. Verify Final Response Structure
    assert res_data["status"] == "completed"
    assert res_data["authorization"] == "ALLOWED"
    assert res_data["customer_id"] == "CUST-101"
    assert res_data["operation"] == "READ_SUMMARY"
    assert res_data["delegation_chain"] == ["USER-001", "agent_a", "agent_b", "agent_c"]
    assert "Acme Global Technologies" in res_data["data"]["customer_name"]
    assert "balances" in res_data["data"]

    # 3. Verify Real HTTP Hops were made
    # Hop 1: Agent A -> Agent B (/api/v1/agents/agent-b/execute)
    # Hop 2: Agent B -> Agent C (/api/v1/agents/agent-c/execute)
    # Hop 3: Agent C -> Governor Tool Gateway (/api/v1/governor/tools/execute)
    assert len(hop_tracker) == 3
    assert hop_tracker[0]["endpoint"] == "/api/v1/agents/agent-b/execute"
    assert hop_tracker[1]["endpoint"] == "/api/v1/agents/agent-c/execute"
    assert hop_tracker[2]["endpoint"] == "/api/v1/governor/tools/execute"

    # 4. Verify Tokens were propagated and distinct for each hop
    token_b = hop_tracker[0]["token"]
    token_c = hop_tracker[1]["token"]
    token_tool = hop_tracker[2]["token"]
    assert token_b is not None
    assert token_c is not None
    assert token_b != token_c
    assert token_tool == token_c  # Agent C presents its token to Governor

    # 5. Verify Tokens and Audit Events in Database
    db = DatabaseSession.get_db()
    assert db is not None

    # Verify delegation tokens in MongoDB
    tokens_in_db = await db["delegation_tokens"].find({"chain_id": res_data["chain_id"]}).to_list(10)
    assert len(tokens_in_db) >= 3  # Root (A), Child (B), Child (C)
    depths = [t["depth"] for t in tokens_in_db]
    assert 0 in depths
    assert 1 in depths
    assert 2 in depths

    # Verify audit log ledger in MongoDB
    audit_logs = await db["audit_logs"].find({"chain_id": res_data["chain_id"]}).sort("sequence", 1).to_list(20)
    assert len(audit_logs) >= 4  # TOKEN_MINTED -> DELEGATION_ALLOWED -> DELEGATION_ALLOWED -> TOOL_ALLOWED
    event_types = [log["event_type"] for log in audit_logs]
    assert "TOKEN_MINTED" in event_types
    assert "DELEGATION_ALLOWED" in event_types
    assert "TOOL_ALLOWED" in event_types


@pytest.mark.asyncio
async def test_real_e2e_scope_escalation_blocked_mid_chain(async_client: AsyncClient):
    """
    Test: Attack attempt mid-chain.
    Agent B attempts to escalate scope to WRITE for Agent C.
    The Governor blocks the delegation, and Financial Tool is NEVER reached.
    """
    AgentHTTPClient.set_test_client(async_client)

    user_payload = {
        "task_type": "financial_analysis_task",
        "originating_user": "USER-001",
        "customer_id": "CUST-101",
        "operation": "READ_SUMMARY",
        "simulate_attack": "escalate_write_to_c"
    }

    response = await async_client.post(
        "/api/v1/agents/agent-a/execute",
        json=user_payload
    )

    # Blocked by Governor with 403
    assert response.status_code == 403
    err = response.json()
    assert "SCOPE_EXPANSION_FORBIDDEN" in err["error_code"] or "INSUFFICIENT_OPERATION_SCOPE" in err["error_code"]

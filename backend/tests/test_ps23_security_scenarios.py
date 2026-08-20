import time
import pytest
from httpx import AsyncClient

from app.services.agent_client import AgentHTTPClient
from app.services.financial_tool import FinancialToolService
from app.services.governor_service import GovernorService
from app.services.audit_service import AuditService
from app.models.token import DataScope
from app.db.session import DatabaseSession


# ==============================================================================
# TEST 1: Normal 3-Agent READ (Expected: ALLOW)
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_1_normal_3_agent_read_allowed(async_client: AsyncClient, monkeypatch):
    """
    TEST 1: Normal 3-agent READ
    USER -> Agent A -> Agent B -> Agent C -> Governor -> Financial Tool -> MongoDB -> Result.
    Expected: ALLOW
    """
    AgentHTTPClient.set_test_client(async_client)
    tool_executed = False
    original_exec = FinancialToolService.execute_operation

    async def spy_tool_exec(*args, **kwargs):
        nonlocal tool_executed
        tool_executed = True
        return await original_exec(*args, **kwargs)

    monkeypatch.setattr(FinancialToolService, "execute_operation", spy_tool_exec)

    res = await async_client.post(
        "/api/v1/agents/agent-a/execute",
        json={
            "task_type": "financial_analysis_task",
            "originating_user": "USER-PS23-01",
            "customer_id": "CUST-101",
            "operation": "READ_SUMMARY"
        }
    )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "completed"
    assert data["authorization"] == "ALLOWED"
    assert data["customer_id"] == "CUST-101"
    assert data["operation"] == "READ_SUMMARY"
    assert data["delegation_chain"] == ["USER-PS23-01", "agent_a", "agent_b", "agent_c"]
    assert "Acme Global Technologies" in data["data"]["customer_name"]
    assert tool_executed is True, "Financial Tool must have executed"

    # Verify DB persistence of audit logs
    db = DatabaseSession.get_db()
    assert db is not None
    audit_trail = await db["audit_logs"].find({"chain_id": data["chain_id"]}).sort("sequence", 1).to_list(10)
    assert len(audit_trail) >= 4
    event_types = [a["event_type"] for a in audit_trail]
    assert event_types == ["TOKEN_MINTED", "DELEGATION_ALLOWED", "DELEGATION_ALLOWED", "TOOL_ALLOWED"]


# ==============================================================================
# TEST 2: Agent C WRITE (Expected: BLOCK - Tool must NEVER execute)
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_2_agent_c_write_blocked(async_client: AsyncClient, monkeypatch):
    """
    TEST 2: Agent C WRITE with Read-Only Token.
    Expected: BLOCK (403 INSUFFICIENT_OPERATION_SCOPE). Financial Tool must NEVER execute.
    """
    AgentHTTPClient.set_test_client(async_client)
    tool_executed = False
    original_exec = FinancialToolService.execute_operation

    async def spy_tool_exec(*args, **kwargs):
        nonlocal tool_executed
        tool_executed = True
        return await original_exec(*args, **kwargs)

    monkeypatch.setattr(FinancialToolService, "execute_operation", spy_tool_exec)

    # 1. Mint read token chain down to Agent C
    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )
    token_b, _ = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_b",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )
    token_c, claims_c = await GovernorService.derive_child_token(
        parent_token=token_b,
        delegator_agent="agent_b",
        delegatee_agent="agent_c",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    # 2. Agent C presents read token attempting WRITE_RECORD
    res = await async_client.post(
        "/api/v1/governor/tools/execute",
        json={
            "task_id": "task_attack_02",
            "agent_id": "agent_c",
            "token": token_c,
            "operation": "WRITE_RECORD",
            "resource": "customer_financials",
            "customer_id": "CUST-101",
            "payload": {"summary": "Malicious tampering"}
        }
    )

    assert res.status_code == 403
    err = res.json()
    assert err["status"] == "error"
    assert err["error_code"] == "INSUFFICIENT_OPERATION_SCOPE"
    assert tool_executed is False, "Financial Tool must NEVER execute for unauthorized write"

    # Verify audit event is TOOL_BLOCKED with DENY
    db = DatabaseSession.get_db()
    if db is not None:
        last_audit = await db["audit_logs"].find_one({"chain_id": claims_c.chain_id}, sort=[("sequence", -1)])
        assert last_audit is not None
        assert last_audit["event_type"] == "TOOL_BLOCKED"
        assert last_audit["decision"] == "DENY"


# ==============================================================================
# TEST 3: Agent A Scope Escalation (READ -> WRITE) (Expected: BLOCK)
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_3_agent_a_scope_escalation_blocked(async_client: AsyncClient):
    """
    TEST 3: Agent A Scope Escalation: READ -> WRITE.
    Expected: BLOCK (403 SCOPE_EXPANSION_FORBIDDEN). No child token created.
    """
    res = await async_client.post(
        "/api/v1/agents/agent-a/execute",
        json={
            "task_type": "financial_analysis_task",
            "originating_user": "USER-PS23-03",
            "customer_id": "CUST-101",
            "simulate_attack": "escalate_write_to_b"
        }
    )

    assert res.status_code == 403
    err = res.json()
    assert err["error_code"] == "SCOPE_EXPANSION_FORBIDDEN"
    assert "Read never implies Write" in err["message"]

    # Verify NO token was created for Agent B in DB
    db = DatabaseSession.get_db()
    if db is not None:
        child_token = await db["delegation_tokens"].find_one({"delegatee": "agent_b", "delegator": "agent_a"})
        assert child_token is None


# ==============================================================================
# TEST 4: Cross-Customer Access (CUST-101 -> CUST-102) (Expected: BLOCK)
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_4_cross_customer_access_blocked(async_client: AsyncClient, monkeypatch):
    """
    TEST 4: Cross-Customer Access (CUST-101 token used to access CUST-102).
    Expected: BLOCK (403 DATA_SCOPE_VIOLATION).
    """
    AgentHTTPClient.set_test_client(async_client)
    tool_executed = False
    original_exec = FinancialToolService.execute_operation

    async def spy_tool_exec(*args, **kwargs):
        nonlocal tool_executed
        tool_executed = True
        return await original_exec(*args, **kwargs)

    monkeypatch.setattr(FinancialToolService, "execute_operation", spy_tool_exec)

    # Token scoped exclusively to CUST-101
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
        "/api/v1/governor/tools/execute",
        json={
            "task_id": "task_cross_cust_04",
            "agent_id": "agent_c",
            "token": token_c,
            "operation": "READ_SUMMARY",
            "resource": "customer_financials",
            "customer_id": "CUST-102"
        }
    )

    assert res.status_code == 403
    err = res.json()
    assert err["error_code"] == "DATA_SCOPE_VIOLATION"
    assert "CUST-102" in err["message"]
    assert tool_executed is False


# ==============================================================================
# TEST 5: Tampered JWT (Expected: INVALID_ED25519_SIGNATURE)
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_5_tampered_jwt_rejected(async_client: AsyncClient):
    """
    TEST 5: Tampered JWT signature presented to Governor.
    Expected: 401 INVALID_ED25519_SIGNATURE
    """
    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )
    # Corrupt the signature segment of the JWT
    parts = token_a.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.bad_signature_bits"

    res = await async_client.post(
        "/api/v1/governor/tools/execute",
        json={
            "task_id": "task_tamper_05",
            "agent_id": "agent_a",
            "token": tampered_token,
            "operation": "READ_SUMMARY",
            "resource": "customer_financials",
            "customer_id": "CUST-101"
        }
    )

    assert res.status_code == 401
    err = res.json()
    assert err["error_code"] == "INVALID_ED25519_SIGNATURE"


# ==============================================================================
# TEST 6: Expired Token (Expected: TOKEN_EXPIRED)
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_6_expired_token_rejected(async_client: AsyncClient):
    """
    TEST 6: Expired Token presented to Governor.
    Expected: 401 TOKEN_EXPIRED
    """
    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a",
        ttl_seconds=1
    )
    time.sleep(1.1)

    res = await async_client.post(
        "/api/v1/governor/tools/execute",
        json={
            "task_id": "task_expired_06",
            "agent_id": "agent_a",
            "token": token_a,
            "operation": "READ_SUMMARY",
            "resource": "customer_financials",
            "customer_id": "CUST-101"
        }
    )

    assert res.status_code == 401
    err = res.json()
    assert err["error_code"] == "TOKEN_EXPIRED"


# ==============================================================================
# TEST 7: Wrong Audience (Expected: AUDIENCE_MISMATCH)
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_7_wrong_audience_rejected(async_client: AsyncClient):
    """
    TEST 7: Wrong Audience (Agent B token presented by Agent C).
    Expected: 403 AUDIENCE_MISMATCH
    """
    token_a, _ = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )
    token_b, _ = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_b",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )

    # Agent C presents Agent B's token
    res = await async_client.post(
        "/api/v1/governor/tools/execute",
        json={
            "task_id": "task_wrong_aud_07",
            "agent_id": "agent_c",
            "token": token_b,
            "operation": "READ_SUMMARY",
            "resource": "customer_financials",
            "customer_id": "CUST-101"
        }
    )

    assert res.status_code == 403
    err = res.json()
    assert err["error_code"] == "AUDIENCE_MISMATCH"
    assert "agent_c" in err["message"]


# ==============================================================================
# TEST 8: Audit Hash Tampering (Expected: Verification Failure)
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_8_audit_hash_tampering_fails_verification(async_client: AsyncClient):
    """
    TEST 8: Audit Hash Tampering Detection.
    Expected: verify_chain() returns valid: False, tampered: True.
    """
    AgentHTTPClient.set_test_client(async_client)

    # Run legitimate transaction
    res = await async_client.post(
        "/api/v1/agents/agent-a/execute",
        json={
            "task_type": "financial_analysis_task",
            "originating_user": "USER-TAMPER-08",
            "customer_id": "CUST-101",
            "operation": "READ_SUMMARY"
        }
    )
    assert res.status_code == 200
    chain_id = res.json()["chain_id"]

    # Tamper with the decision of event at sequence 1 in DB and memory
    db = DatabaseSession.get_db()
    if db is not None:
        await db["audit_logs"].update_one(
            {"chain_id": chain_id, "sequence": 1},
            {"$set": {"decision": "DENY"}}
        )
    if chain_id in AuditService._in_memory_ledger:
        AuditService._in_memory_ledger[chain_id][1].decision = "DENY"

    # Call verification endpoint
    verify_res = await async_client.get(f"/api/v1/audit/verify/{chain_id}")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["valid"] is False
    assert v_data["tampered"] is True
    assert v_data["broken_link_index"] == 1
    assert "Tampered event data" in v_data["reason"]


# ==============================================================================
# TEST 9: Scope Shrinkage Bonus (Expected: ALLOW)
# ==============================================================================
@pytest.mark.asyncio
async def test_scenario_9_scope_shrinkage_bonus_allowed(async_client: AsyncClient):
    """
    TEST 9: Scope Shrinkage:
    Agent A (read:all) -> Agent B (read:summary) -> Agent C (read:metrics).
    Expected: ALLOW at every step.
    """
    AgentHTTPClient.set_test_client(async_client)

    # 1. Agent A Root: read:all
    token_a, claims_a = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )
    assert claims_a.scopes == ["financials:read:all"]

    # 2. Agent A -> Agent B: Narrow to read:summary
    token_b, claims_b = await GovernorService.derive_child_token(
        parent_token=token_a,
        delegator_agent="agent_a",
        delegatee_agent="agent_b",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )
    assert claims_b.scopes == ["financials:read:summary"]

    # 3. Agent B -> Agent C: Narrow further to read:metrics
    token_c, claims_c = await GovernorService.derive_child_token(
        parent_token=token_b,
        delegator_agent="agent_b",
        delegatee_agent="agent_c",
        requested_scopes=["financials:read:metrics"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"])
    )
    assert claims_c.scopes == ["financials:read:metrics"]

    # 4. Agent C executes READ_METRICS at Governor Tool Gateway
    res = await async_client.post(
        "/api/v1/governor/tools/execute",
        json={
            "task_id": "task_metrics_shrink_09",
            "agent_id": "agent_c",
            "token": token_c,
            "operation": "READ_METRICS",
            "resource": "customer_financials",
            "customer_id": "CUST-101"
        }
    )

    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "SUCCESS"
    assert data["operation"] == "READ_METRICS"
    assert "metrics" in data["data"]
    assert "monthly_burn_rate" in data["data"]["metrics"]

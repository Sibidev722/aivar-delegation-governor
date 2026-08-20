import pytest
from httpx import AsyncClient

from app.services.audit_service import AuditService
from app.services.agent_client import AgentHTTPClient
from app.db.session import DatabaseSession


@pytest.mark.asyncio
async def test_audit_ledger_valid_chain_verifies(async_client: AsyncClient):
    """
    Test 1: Valid append-only chain verifies mathematically.
    """
    chain_id = "urn:uuid:test-chain-valid-01"

    # Append 3 sequential events
    e0 = await AuditService.record_event(
        chain_id=chain_id,
        event_type="TOKEN_MINTED",
        actor="user",
        target="agent_a",
        scopes=["financials:read:all"],
        data_scope={"customer_ids": ["CUST-101"]},
        decision="ALLOW",
        reason="Minted root token"
    )

    e1 = await AuditService.record_event(
        chain_id=chain_id,
        event_type="DELEGATION_ALLOWED",
        actor="agent_a",
        target="agent_b",
        scopes=["financials:read:summary"],
        data_scope={"customer_ids": ["CUST-101"]},
        decision="ALLOW",
        reason="Delegated to Agent B",
        parent_token_id=e0.token_id
    )

    e2 = await AuditService.record_event(
        chain_id=chain_id,
        event_type="TOOL_ALLOWED",
        actor="agent_c",
        target="financial_tool:READ_SUMMARY",
        scopes=["financials:read:summary"],
        data_scope={"customer_ids": ["CUST-101"]},
        decision="ALLOW",
        reason="Read financial summary for CUST-101"
    )

    # Verify via Service
    result = await AuditService.verify_chain(chain_id)
    assert result.valid is True
    assert result.tampered is False
    assert result.total_events == 3

    # Verify via API endpoint
    api_res = await async_client.get(f"/api/v1/audit/verify/{chain_id}")
    assert api_res.status_code == 200
    api_data = api_res.json()
    assert api_data["valid"] is True
    assert api_data["tampered"] is False
    assert api_data["total_events"] == 3


@pytest.mark.asyncio
async def test_audit_ledger_modify_event_fails_verification():
    """
    Test 2: Modifying an event's field (tampering with payload) causes hash verification to fail.
    """
    chain_id = "urn:uuid:test-chain-tamper-payload"

    await AuditService.record_event(
        chain_id=chain_id,
        event_type="TOKEN_MINTED",
        actor="user",
        target="agent_a",
        scopes=["financials:read:summary"],
        data_scope={"customer_ids": ["CUST-101"]},
        decision="ALLOW",
        reason="Initial mint"
    )
    await AuditService.record_event(
        chain_id=chain_id,
        event_type="DELEGATION_BLOCKED",
        actor="agent_a",
        target="agent_b",
        scopes=["financials:write:record"],
        data_scope={"customer_ids": ["CUST-101"]},
        decision="DENY",
        reason="Write scope blocked"
    )

    # Direct tamper in DB or in-memory ledger
    db = DatabaseSession.get_db()
    if db is not None:
        # Tamper decision from DENY to ALLOW without updating hash
        await db["audit_logs"].update_one(
            {"chain_id": chain_id, "sequence": 1},
            {"$set": {"decision": "ALLOW"}}
        )
    if chain_id in AuditService._in_memory_ledger:
        AuditService._in_memory_ledger[chain_id][1].decision = "ALLOW"

    result = await AuditService.verify_chain(chain_id)
    assert result.valid is False
    assert result.tampered is True
    assert result.broken_link_index == 1
    assert "Tampered event data" in result.reason


@pytest.mark.asyncio
async def test_audit_ledger_modify_order_fails_verification():
    """
    Test 3: Modifying event order (re-ordering attack) causes backward hash link failure.
    """
    chain_id = "urn:uuid:test-chain-reorder"

    e0 = await AuditService.record_event(
        chain_id=chain_id,
        event_type="TOKEN_MINTED",
        actor="user",
        target="agent_a",
        scopes=["financials:read:all"],
        data_scope={},
        decision="ALLOW",
        reason="Step 0"
    )
    e1 = await AuditService.record_event(
        chain_id=chain_id,
        event_type="DELEGATION_ALLOWED",
        actor="agent_a",
        target="agent_b",
        scopes=["financials:read:summary"],
        data_scope={},
        decision="ALLOW",
        reason="Step 1"
    )
    e2 = await AuditService.record_event(
        chain_id=chain_id,
        event_type="TOOL_ALLOWED",
        actor="agent_c",
        target="financial_tool:READ_SUMMARY",
        scopes=["financials:read:summary"],
        data_scope={},
        decision="ALLOW",
        reason="Step 2"
    )

    # Swap sequence values between event 1 and event 2 in DB to reorder them
    db = DatabaseSession.get_db()
    if db is not None:
        await db["audit_logs"].update_one({"event_id": e1.event_id}, {"$set": {"sequence": 2}})
        await db["audit_logs"].update_one({"event_id": e2.event_id}, {"$set": {"sequence": 1}})

    if chain_id in AuditService._in_memory_ledger:
        AuditService._in_memory_ledger[chain_id][1].sequence = 2
        AuditService._in_memory_ledger[chain_id][2].sequence = 1
        AuditService._in_memory_ledger[chain_id].sort(key=lambda x: x.sequence)

    result = await AuditService.verify_chain(chain_id)
    assert result.valid is False
    assert result.tampered is True
    assert result.broken_link_index is not None


@pytest.mark.asyncio
async def test_audit_ledger_delete_event_fails_verification():
    """
    Test 4: Deleting an event (drop attack) causes broken hash pointer and sequence failure.
    """
    chain_id = "urn:uuid:test-chain-deletion"

    await AuditService.record_event(
        chain_id=chain_id,
        event_type="TOKEN_MINTED",
        actor="user",
        target="agent_a",
        scopes=["financials:read:all"],
        data_scope={},
        decision="ALLOW",
        reason="Step 0"
    )
    await AuditService.record_event(
        chain_id=chain_id,
        event_type="DELEGATION_ALLOWED",
        actor="agent_a",
        target="agent_b",
        scopes=["financials:read:summary"],
        data_scope={},
        decision="ALLOW",
        reason="Step 1"
    )
    await AuditService.record_event(
        chain_id=chain_id,
        event_type="TOOL_ALLOWED",
        actor="agent_c",
        target="financial_tool:READ_SUMMARY",
        scopes=["financials:read:summary"],
        data_scope={},
        decision="ALLOW",
        reason="Step 2"
    )

    # Delete intermediate event (sequence 1)
    if chain_id in AuditService._in_memory_ledger:
        AuditService._in_memory_ledger[chain_id].pop(1)

    db = DatabaseSession.get_db()
    if db is not None:
        await db["audit_logs"].delete_one({"chain_id": chain_id, "sequence": 1})

    result = await AuditService.verify_chain(chain_id)
    assert result.valid is False
    assert result.tampered is True
    assert result.broken_link_index == 1


@pytest.mark.asyncio
async def test_audit_ledger_complete_abc_reconstructable(async_client: AsyncClient):
    """
    Test 5: The complete A -> B -> C execution chain is fully reconstructable from audit ledger.
    """
    AgentHTTPClient.set_test_client(async_client)

    # Run real E2E pipeline
    res = await async_client.post(
        "/api/v1/agents/agent-a/execute",
        json={
            "task_type": "financial_analysis_task",
            "originating_user": "USER-RECONSTRUCT-01",
            "customer_id": "CUST-101",
            "operation": "READ_SUMMARY"
        }
    )
    assert res.status_code == 200
    chain_id = res.json()["chain_id"]

    # 1. Fetch complete audit chain
    chain_res = await async_client.get(f"/api/v1/audit/chain/{chain_id}")
    assert chain_res.status_code == 200
    events = chain_res.json()
    assert len(events) >= 4

    # Verify event types and sequence continuity
    for idx, evt in enumerate(events):
        assert evt["sequence"] == idx
        assert evt["chain_id"] == chain_id

    event_types = [e["event_type"] for e in events]
    assert "TOKEN_MINTED" in event_types
    assert "DELEGATION_ALLOWED" in event_types
    assert "TOOL_ALLOWED" in event_types

    # 2. Verify chain cryptographic integrity
    verify_res = await async_client.get(f"/api/v1/audit/verify/{chain_id}")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["valid"] is True
    assert v_data["tampered"] is False
    assert v_data["total_events"] == len(events)

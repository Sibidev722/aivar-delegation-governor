import time
import pytest
from httpx import AsyncClient

from app.models.token import DataScope, TokenClaims
from app.core.security import sign_token_claims
from app.services.governor_service import GovernorService
from app.core.exceptions import (
    ScopeExpansionForbiddenException,
    DataScopeViolationException,
    AudienceMismatchException,
    TokenExpiredException,
    InvalidTokenSignatureException,
    GovernanceException
)


# ==============================================================================
# 1. Operational Delegation Tests (ALLOW & BLOCK)
# ==============================================================================

@pytest.mark.asyncio
async def test_delegation_a_read_to_b_read_allowed(async_client: AsyncClient):
    """Test: Agent A (read:all) -> Agent B (read:all) is ALLOWED."""
    # 1. Mint Root for Agent A
    mint_res = await async_client.post(
        "/api/v1/governor/tokens/mint-root",
        json={"task_type": "financial_analysis_task", "target_agent": "agent_a"}
    )
    assert mint_res.status_code == 201
    token_a = mint_res.json()["token"]

    # 2. Delegate A -> B with equal scope
    del_res = await async_client.post(
        "/api/v1/governor/tokens/delegate",
        json={
            "parent_token": token_a,
            "target_agent": "agent_b",
            "requested_scopes": ["financials:read:all"],
            "requested_data_scope": {"customer_ids": ["CUST-101", "CUST-102", "CUST-103", "CUST-104", "CUST-105"]}
        }
    )
    assert del_res.status_code == 201
    data_b = del_res.json()
    assert data_b["depth"] == 1
    assert data_b["scopes"] == ["financials:read:all"]


@pytest.mark.asyncio
async def test_delegation_read_all_to_read_summary_allowed(async_client: AsyncClient):
    """Test: Agent A (read:all) -> Agent B (read:summary) is ALLOWED."""
    mint_res = await async_client.post(
        "/api/v1/governor/tokens/mint-root",
        json={"task_type": "financial_analysis_task", "target_agent": "agent_a"}
    )
    token_a = mint_res.json()["token"]

    del_res = await async_client.post(
        "/api/v1/governor/tokens/delegate",
        json={
            "parent_token": token_a,
            "target_agent": "agent_b",
            "requested_scopes": ["financials:read:summary"],
            "requested_data_scope": {"customer_ids": ["CUST-101"]}
        }
    )
    assert del_res.status_code == 201
    assert del_res.json()["scopes"] == ["financials:read:summary"]


@pytest.mark.asyncio
async def test_delegation_read_summary_to_read_metrics_allowed(async_client: AsyncClient):
    """Test: Agent B (read:summary) -> Agent C (read:metrics) is ALLOWED."""
    # Mint root for A
    mint_res = await async_client.post(
        "/api/v1/governor/tokens/mint-root",
        json={"task_type": "financial_analysis_task", "target_agent": "agent_a"}
    )
    token_a = mint_res.json()["token"]

    # Delegate A -> B (read:summary)
    del_b = await async_client.post(
        "/api/v1/governor/tokens/delegate",
        json={
            "parent_token": token_a,
            "target_agent": "agent_b",
            "requested_scopes": ["financials:read:summary"],
            "requested_data_scope": {"customer_ids": ["CUST-101"]}
        }
    )
    token_b = del_b.json()["token"]

    # Delegate B -> C (read:metrics)
    del_c = await async_client.post(
        "/api/v1/governor/tokens/delegate",
        json={
            "parent_token": token_b,
            "target_agent": "agent_c",
            "requested_scopes": ["financials:read:metrics"],
            "requested_data_scope": {"customer_ids": ["CUST-101"]}
        }
    )
    assert del_c.status_code == 201
    data_c = del_c.json()
    assert data_c["depth"] == 2
    assert data_c["scopes"] == ["financials:read:metrics"]


@pytest.mark.asyncio
async def test_delegation_read_to_write_blocked(async_client: AsyncClient):
    """Test: Agent A (read) attempting to delegate WRITE to Agent B is BLOCKED (403)."""
    mint_res = await async_client.post(
        "/api/v1/governor/tokens/mint-root",
        json={"task_type": "financial_analysis_task", "target_agent": "agent_a"}
    )
    token_a = mint_res.json()["token"]

    # Attempt to delegate write
    del_res = await async_client.post(
        "/api/v1/governor/tokens/delegate",
        json={
            "parent_token": token_a,
            "target_agent": "agent_b",
            "requested_scopes": ["financials:write:record"],
            "requested_data_scope": {"customer_ids": ["CUST-101"]}
        }
    )
    assert del_res.status_code == 403
    data = del_res.json()
    assert data["status"] == "error"
    assert data["error_code"] == "SCOPE_EXPANSION_FORBIDDEN"
    assert "Read never implies Write" in data["message"]


# ==============================================================================
# 2. Data Scope Escalation Tests (BLOCK)
# ==============================================================================

@pytest.mark.asyncio
async def test_delegation_cust101_to_cust102_blocked(async_client: AsyncClient):
    """Test: Token with CUST-101 attempting to delegate CUST-102 is BLOCKED (403)."""
    mint_res = await async_client.post(
        "/api/v1/governor/tokens/mint-root",
        json={"task_type": "single_customer_audit", "target_agent": "agent_a"}
    )
    token_a = mint_res.json()["token"]

    # Attempt to expand data scope to CUST-102
    del_res = await async_client.post(
        "/api/v1/governor/tokens/delegate",
        json={
            "parent_token": token_a,
            "target_agent": "agent_b",
            "requested_scopes": ["financials:read:summary"],
            "requested_data_scope": {"customer_ids": ["CUST-102"]}
        }
    )
    assert del_res.status_code == 403
    data = del_res.json()
    assert data["error_code"] == "DATA_SCOPE_VIOLATION"
    assert "CUST-102" in data["message"]


# ==============================================================================
# 3. Security Boundary Violations (Expired, Wrong Aud, Invalid Sig, Max Depth)
# ==============================================================================

@pytest.mark.asyncio
async def test_delegation_expired_parent_blocked(async_client: AsyncClient):
    """Test: Delegation from expired parent token is BLOCKED (401)."""
    # Mint token with 1 second TTL
    mint_res = await async_client.post(
        "/api/v1/governor/tokens/mint-root",
        json={"task_type": "financial_analysis_task", "target_agent": "agent_a", "ttl_seconds": 1}
    )
    token_a = mint_res.json()["token"]

    # Sleep 1.1s
    time.sleep(1.1)

    del_res = await async_client.post(
        "/api/v1/governor/tokens/delegate",
        json={
            "parent_token": token_a,
            "target_agent": "agent_b",
            "requested_scopes": ["financials:read:summary"],
            "requested_data_scope": {"customer_ids": ["CUST-101"]}
        }
    )
    assert del_res.status_code == 401
    assert del_res.json()["error_code"] == "TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_delegation_wrong_audience_blocked(async_client: AsyncClient):
    """Test: Token issued for agent_a presented to delegate with delegator='agent_c' is BLOCKED."""
    # Token minted for agent_a
    mint_res = await async_client.post(
        "/api/v1/governor/tokens/mint-root",
        json={"task_type": "financial_analysis_task", "target_agent": "agent_a"}
    )
    token_a = mint_res.json()["token"]

    # Attempt to delegate as agent_c (mismatch with parent.aud = agent_a)
    with pytest.raises(AudienceMismatchException):
        await GovernorService.derive_child_token(
            parent_token=token_a,
            delegator_agent="agent_c",  # Wrong delegator
            delegatee_agent="agent_b",
            requested_scopes=["financials:read:summary"],
            requested_data_scope=DataScope(customer_ids=["CUST-101"])
        )


@pytest.mark.asyncio
async def test_delegation_invalid_signature_blocked(async_client: AsyncClient):
    """Test: Tampered token signature is BLOCKED (401)."""
    mint_res = await async_client.post(
        "/api/v1/governor/tokens/mint-root",
        json={"task_type": "financial_analysis_task", "target_agent": "agent_a"}
    )
    token_a = mint_res.json()["token"]

    # Corrupt the signature part of the JWT
    parts = token_a.split(".")
    tampered_token = f"{parts[0]}.{parts[1]}.corrupted_signature_xyz"

    del_res = await async_client.post(
        "/api/v1/governor/tokens/delegate",
        json={
            "parent_token": tampered_token,
            "target_agent": "agent_b",
            "requested_scopes": ["financials:read:summary"],
            "requested_data_scope": {"customer_ids": ["CUST-101"]}
        }
    )
    assert del_res.status_code == 401
    assert del_res.json()["error_code"] == "INVALID_ED25519_SIGNATURE"


@pytest.mark.asyncio
async def test_delegation_max_depth_exceeded_blocked():
    """Test: Exceeding max_depth is BLOCKED (403)."""
    now = int(time.time())
    # Create custom claims with max_depth = 1
    claims_0 = TokenClaims(
        jti="urn:uuid:test-depth-root",
        chain_id="urn:uuid:test-depth-chain",
        parent_jti=None,
        iss="delegation-governor",
        sub="user",
        aud="agent_a",
        scopes=["financials:read:all"],
        resource="customer_financials",
        data_scope=DataScope(customer_ids=["CUST-101"]),
        depth=0,
        max_depth=1,  # Max depth 1 allows only Hop 1
        iat=now,
        exp=now + 300,
        parent_token_hash=None,
        nonce="nonce123"
    )
    token_0 = sign_token_claims(claims_0)

    # Hop 1 (depth 1 <= max_depth 1) -> Allowed
    token_1, claims_1 = await GovernorService.derive_child_token(
        parent_token=token_0,
        delegator_agent="agent_a",
        delegatee_agent="agent_b",
        requested_scopes=["financials:read:all"],
        requested_data_scope=claims_0.data_scope
    )
    assert claims_1.depth == 1

    # Hop 2 (depth 2 > max_depth 1) -> BLOCKED
    with pytest.raises(GovernanceException) as exc_info:
        await GovernorService.derive_child_token(
            parent_token=token_1,
            delegator_agent="agent_b",
            delegatee_agent="agent_c",
            requested_scopes=["financials:read:all"],
            requested_data_scope=claims_1.data_scope
        )
    assert exc_info.value.error_code == "MAX_DELEGATION_DEPTH_EXCEEDED"

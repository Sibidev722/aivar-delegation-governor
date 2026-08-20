import time
import pytest
from httpx import AsyncClient

from app.services.governor_service import GovernorService, ROOT_POLICIES
from app.core.exceptions import GovernanceException, TokenExpiredException
from app.models.token import DataScope


# 9. Root policy enforcement
@pytest.mark.asyncio
async def test_root_policy_enforcement_valid_task():
    """Test 9a: Minting root token with registered server policy assigns server-defined scopes."""
    token, claims = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a",
        user_id="user_123"
    )

    assert claims.depth == 0
    assert claims.sub == "user_123"
    assert claims.aud == "agent_a"
    assert claims.scopes == ["financials:read:all"]
    assert "CUST-101" in claims.data_scope.customer_ids
    assert len(claims.data_scope.customer_ids) == 5
    assert claims.parent_jti is None
    assert claims.parent_token_hash is None


@pytest.mark.asyncio
async def test_root_policy_enforcement_invalid_task():
    """Test 9b: Attempting to request arbitrary unregistered task policy is rejected."""
    with pytest.raises(GovernanceException) as exc_info:
        await GovernorService.create_root_token(
            task_name="arbitrary_admin_task",
            target_agent="agent_a"
        )
    assert exc_info.value.error_code == "INVALID_TASK_POLICY"


# 10. Private key is never returned
@pytest.mark.asyncio
async def test_public_key_endpoint_and_private_key_safety(async_client: AsyncClient):
    """Test 10: Public key endpoint exposes ONLY public key and never leaks private key."""
    res = await async_client.get("/api/v1/governor/public-key")
    assert res.status_code == 200
    data = res.json()

    assert data["algorithm"] == "Ed25519"
    assert "public_key_hex" in data
    assert "public_key_pem" in data
    assert "BEGIN PUBLIC KEY" in data["public_key_pem"]

    # Strict check: Ensure private key indicators NEVER appear in response
    assert "private" not in str(data).lower()
    assert "BEGIN PRIVATE KEY" not in str(data)


@pytest.mark.asyncio
async def test_child_token_derivation_lineage():
    """Verify child token derivation links parent_token_hash and increments depth."""
    # 1. Create root token
    root_token, root_claims = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a"
    )

    # 2. Derive child token for Agent B
    child_token, child_claims = await GovernorService.derive_child_token(
        parent_token=root_token,
        delegator_agent="agent_a",
        delegatee_agent="agent_b",
        requested_scopes=["financials:read:summary"],
        requested_data_scope=DataScope(customer_ids=["CUST-101"]),
        ttl_seconds=100
    )

    assert child_claims.depth == 1
    assert child_claims.parent_jti == root_claims.jti
    assert child_claims.sub == "agent_a"
    assert child_claims.aud == "agent_b"
    assert child_claims.scopes == ["financials:read:summary"]
    assert child_claims.data_scope.customer_ids == ["CUST-101"]
    assert child_claims.parent_token_hash == GovernorService.hash_token(root_token)
    assert child_claims.exp <= root_claims.exp


@pytest.mark.asyncio
async def test_child_token_derivation_from_expired_parent():
    """Verify child token cannot be minted from an expired parent token."""
    # Create root token with 1 second TTL
    root_token, root_claims = await GovernorService.create_root_token(
        task_name="financial_analysis_task",
        target_agent="agent_a",
        ttl_seconds=1
    )

    # Sleep 1.1 seconds
    time.sleep(1.1)

    with pytest.raises(TokenExpiredException):
        await GovernorService.derive_child_token(
            parent_token=root_token,
            delegator_agent="agent_a",
            delegatee_agent="agent_b",
            requested_scopes=["financials:read:summary"],
            requested_data_scope=DataScope(customer_ids=["CUST-101"])
        )


@pytest.mark.asyncio
async def test_governor_mint_and_validate_endpoints(async_client: AsyncClient):
    """Test /governor/tokens/mint-root and /governor/tokens/validate HTTP endpoints."""
    # 1. Mint Root
    mint_res = await async_client.post(
        "/api/v1/governor/tokens/mint-root",
        json={"task_name": "single_customer_audit", "target_agent": "agent_a"}
    )
    assert mint_res.status_code == 201
    mint_data = mint_res.json()
    token = mint_data["token"]
    assert token is not None
    assert mint_data["scopes"] == ["financials:read:summary"]
    assert mint_data["data_scope"]["customer_ids"] == ["CUST-101"]

    # 2. Validate Token
    val_res = await async_client.post(
        "/api/v1/governor/tokens/validate",
        json={"token": token, "expected_audience": "agent_a"}
    )
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["valid"] is True
    assert val_data["claims"]["aud"] == "agent_a"

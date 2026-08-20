import base64
import json
import time
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from app.core.security import (
    crypto_manager,
    sign_token_claims,
    decode_and_verify_token,
    compute_token_hash
)
from app.core.exceptions import (
    InvalidTokenSignatureException,
    TokenExpiredException,
    AudienceMismatchException
)
from app.models.token import TokenClaims, DataScope


@pytest.fixture
def sample_claims() -> TokenClaims:
    now = int(time.time())
    return TokenClaims(
        jti="urn:uuid:11111111-1111-1111-1111-111111111111",
        chain_id="urn:uuid:22222222-2222-2222-2222-222222222222",
        parent_jti=None,
        iss="delegation-governor",
        sub="user",
        aud="agent_a",
        scopes=["financials:read:all"],
        resource="customer_financials",
        data_scope=DataScope(customer_ids=["CUST-101", "CUST-102"]),
        depth=0,
        max_depth=4,
        iat=now,
        exp=now + 300,
        parent_token_hash=None,
        nonce="abc123nonce"
    )


# 1. Valid token
def test_valid_token_encoding_and_claims(sample_claims):
    """Test 1: Valid token encoding and parsing matches original claims."""
    token_jwt = sign_token_claims(sample_claims)
    assert isinstance(token_jwt, str)
    assert len(token_jwt.split(".")) == 3  # Header.Payload.Signature

    claims = decode_and_verify_token(token_jwt)
    assert claims.jti == sample_claims.jti
    assert claims.chain_id == sample_claims.chain_id
    assert claims.scopes == ["financials:read:all"]
    assert claims.data_scope.customer_ids == ["CUST-101", "CUST-102"]


# 2. Valid signature
def test_valid_ed25519_signature(sample_claims):
    """Test 2: Token signed by Governor verifies cleanly against Governor public key."""
    token_jwt = sign_token_claims(sample_claims)
    decoded = decode_and_verify_token(token_jwt)
    assert decoded.iss == "delegation-governor"


# 3. Invalid signature
def test_invalid_signature_foreign_key(sample_claims):
    """Test 3: Token signed with a foreign rogue Ed25519 key fails verification."""
    import jwt
    foreign_private_key = ed25519.Ed25519PrivateKey.generate()
    rogue_token = jwt.encode(sample_claims.model_dump(), foreign_private_key, algorithm="EdDSA")

    with pytest.raises(InvalidTokenSignatureException) as exc_info:
        decode_and_verify_token(rogue_token)
    assert "Token verification failed" in str(exc_info.value)


# 4. Tampered payload
def test_tampered_payload_detected(sample_claims):
    """Test 4: Modifying claims in JWT payload without re-signing breaks signature."""
    token_jwt = sign_token_claims(sample_claims)
    header, payload_b64, signature = token_jwt.split(".")

    # Decode payload, inject unauthorized write scope and different customer
    # Add padding if needed
    padded_b64 = payload_b64 + "=" * (-len(payload_b64) % 4)
    payload_dict = json.loads(base64.urlsafe_b64decode(padded_b64.encode()).decode())
    payload_dict["scopes"] = ["financials:write:record"]
    payload_dict["data_scope"]["customer_ids"].append("CUST-999")

    tampered_payload_b64 = base64.urlsafe_b64encode(
        json.dumps(payload_dict).encode()
    ).decode().rstrip("=")

    tampered_jwt = f"{header}.{tampered_payload_b64}.{signature}"

    with pytest.raises(InvalidTokenSignatureException):
        decode_and_verify_token(tampered_jwt)


# 5. Expired token
def test_expired_token_rejected(sample_claims):
    """Test 5: Expired token raises TokenExpiredException."""
    now = int(time.time())
    expired_claims = sample_claims.model_copy(update={"iat": now - 600, "exp": now - 300})
    expired_jwt = sign_token_claims(expired_claims)

    with pytest.raises(TokenExpiredException):
        decode_and_verify_token(expired_jwt)


# 6. Correct issuer
def test_correct_issuer_enforced(sample_claims):
    """Test 6: Token with invalid issuer is rejected."""
    import jwt
    rogue_issuer_claims = sample_claims.model_copy(update={"iss": "rogue-authority"})
    rogue_jwt = jwt.encode(rogue_issuer_claims.model_dump(), crypto_manager.private_key, algorithm="EdDSA")

    with pytest.raises(InvalidTokenSignatureException) as exc_info:
        decode_and_verify_token(rogue_jwt)
    assert "Invalid issuer" in str(exc_info.value) or "Token verification failed" in str(exc_info.value)


# 7. Correct audience
def test_audience_validation(sample_claims):
    """Test 7: Token with audience 'agent_a' matches expected recipient but rejects 'agent_b'."""
    token_jwt = sign_token_claims(sample_claims)

    # Valid recipient
    claims = decode_and_verify_token(token_jwt, expected_audience="agent_a")
    assert claims.aud == "agent_a"

    # Mismatched recipient
    with pytest.raises(AudienceMismatchException) as exc_info:
        decode_and_verify_token(token_jwt, expected_audience="agent_b")
    assert "does not match expected recipient" in str(exc_info.value)


# 8. Required claims
def test_required_claims_presence(sample_claims):
    """Test 8: Ensure all mandatory delegation claims exist in the token."""
    token_jwt = sign_token_claims(sample_claims)
    claims = decode_and_verify_token(token_jwt)

    required_fields = [
        "jti", "chain_id", "iss", "sub", "aud", "scopes",
        "resource", "data_scope", "depth", "max_depth", "iat", "exp", "nonce"
    ]
    claims_dict = claims.model_dump()
    for field in required_fields:
        assert field in claims_dict, f"Missing required claim: {field}"

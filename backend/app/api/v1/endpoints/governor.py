from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import APIRouter, Body, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import crypto_manager
from app.models.token import (
    PublicKeyResponse,
    RootTokenRequest,
    ChildTokenRequest,
    TokenValidationRequest,
    TokenResponse,
    TokenClaims
)
from app.services.governor_service import GovernorService, ROOT_POLICIES

router = APIRouter()


class TokenValidationResponse(BaseModel):
    valid: bool
    claims: TokenClaims
    token_hash: str


@router.get(
    "/public-key",
    response_model=PublicKeyResponse,
    summary="Export Ed25519 Public Key",
    description="Returns the Delegation Governor's Ed25519 public key. The private key remains strictly confidential."
)
async def get_public_key() -> PublicKeyResponse:
    return PublicKeyResponse(
        algorithm="Ed25519",
        issuer="delegation-governor",
        public_key_hex=crypto_manager.get_public_key_hex(),
        public_key_pem=crypto_manager.get_public_key_pem()
    )


@router.get(
    "/policies",
    summary="List Server-Side Root Policies",
    description="Returns available registered task policies for root token minting."
)
async def get_root_policies() -> Dict[str, Any]:
    return {
        "status": "success",
        "policies": ROOT_POLICIES
    }


@router.post(
    "/tokens/mint-root",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Mint Root Delegation Token",
    description="Mints initial root token for Agent A derived from registered server policies."
)
async def mint_root_token(request: RootTokenRequest) -> TokenResponse:
    task_name = request.get_task_type()
    user_id = request.get_user_id()

    signed_token, claims = await GovernorService.create_root_token(
        task_name=task_name,
        target_agent=request.target_agent,
        user_id=user_id,
        ttl_seconds=request.ttl_seconds
    )
    token_hash = GovernorService.hash_token(signed_token)
    expires_at_iso = datetime.fromtimestamp(claims.exp, tz=timezone.utc).isoformat()

    return TokenResponse(
        token=signed_token,
        token_id=claims.jti,
        chain_id=claims.chain_id,
        parent_token_id=None,
        depth=claims.depth,
        scopes=claims.scopes,
        resource=claims.resource,
        data_scope=claims.data_scope,
        expires_at=expires_at_iso,
        token_hash=token_hash
    )


@router.post(
    "/tokens/delegate",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Derive Child Delegation Token",
    description="Derives a child delegation token with strict scope monotonicity and data scope enforcement."
)
async def delegate_child_token(request: ChildTokenRequest) -> TokenResponse:
    target_agent = request.get_target_agent()
    # Decode parent claims to obtain delegator agent identity if not passed
    parent_claims = GovernorService.verify_token(request.parent_token)
    delegator_agent = parent_claims.aud

    signed_child_token, child_claims = await GovernorService.derive_child_token(
        parent_token=request.parent_token,
        delegator_agent=delegator_agent,
        delegatee_agent=target_agent,
        requested_scopes=request.requested_scopes,
        requested_data_scope=request.requested_data_scope,
        ttl_seconds=request.ttl_seconds
    )
    token_hash = GovernorService.hash_token(signed_child_token)
    expires_at_iso = datetime.fromtimestamp(child_claims.exp, tz=timezone.utc).isoformat()

    return TokenResponse(
        token=signed_child_token,
        token_id=child_claims.jti,
        chain_id=child_claims.chain_id,
        parent_token_id=child_claims.parent_jti,
        depth=child_claims.depth,
        scopes=child_claims.scopes,
        resource=child_claims.resource,
        data_scope=child_claims.data_scope,
        expires_at=expires_at_iso,
        token_hash=token_hash
    )


@router.post(
    "/tokens/validate",
    response_model=TokenValidationResponse,
    summary="Validate Delegation Token",
    description="Verifies Ed25519 signature, issuer, expiration, audience, operation, and customer data scopes."
)
async def validate_token(request: TokenValidationRequest) -> TokenValidationResponse:
    claims = await GovernorService.validate_token_full(
        token=request.token,
        expected_audience=request.expected_audience,
        required_operation=request.required_operation,
        target_customer_id=request.target_customer_id,
        target_resource=request.target_resource
    )
    token_hash = GovernorService.hash_token(request.token)
    return TokenValidationResponse(
        valid=True,
        claims=claims,
        token_hash=token_hash
    )

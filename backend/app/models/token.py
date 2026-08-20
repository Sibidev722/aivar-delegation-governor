import uuid
from typing import Any, List, Optional
from pydantic import BaseModel, Field, field_validator


class DataScope(BaseModel):
    """
    Customer / Resource level data scope.
    Restricts access to explicit customer identifiers.
    """
    customer_ids: List[str] = Field(
        default_factory=list,
        json_schema_extra={"example": ["CUST-101", "CUST-102"]}
    )

    @field_validator("customer_ids")
    @classmethod
    def normalize_customer_ids(cls, v: List[str]) -> List[str]:
        # Strip whitespace, preserve order, remove duplicates
        cleaned = []
        for item in v:
            c = item.strip().upper()
            if c and c not in cleaned:
                cleaned.append(c)
        return cleaned


class TokenClaims(BaseModel):
    """
    Cryptographic Ed25519 JWT payload claims representing delegation authority.
    """
    jti: str = Field(
        description="Unique Token ID (URN UUID)",
        json_schema_extra={"example": "urn:uuid:9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"}
    )
    chain_id: str = Field(
        description="Persistent transaction / chain correlation ID",
        json_schema_extra={"example": "urn:uuid:4a123456-7890-abcd-ef01-234567890abc"}
    )
    parent_jti: Optional[str] = Field(
        default=None,
        description="JTI of parent token in the delegation chain (null for root)",
        json_schema_extra={"example": "urn:uuid:1a098765-4321-fedc-ba98-76543210fedc"}
    )
    iss: str = Field(
        default="delegation-governor",
        description="Token issuer (must always be 'delegation-governor')"
    )
    sub: str = Field(
        description="Subject / Delegator identity (e.g. 'user' or 'agent_a')",
        json_schema_extra={"example": "agent_a"}
    )
    aud: str = Field(
        description="Audience / Intended delegatee agent (e.g. 'agent_b')",
        json_schema_extra={"example": "agent_b"}
    )
    scopes: List[str] = Field(
        description="Operational permission scopes (e.g. 'financials:read:summary')",
        json_schema_extra={"example": ["financials:read:summary"]}
    )
    resource: str = Field(
        default="customer_financials",
        description="Target resource domain"
    )
    data_scope: DataScope = Field(
        default_factory=DataScope,
        description="Data / customer boundary"
    )
    depth: int = Field(
        default=0,
        ge=0,
        description="Delegation depth (0 for root, 1 for hop 1, etc.)"
    )
    max_depth: int = Field(
        default=4,
        ge=1,
        description="Maximum permitted delegation hops"
    )
    iat: int = Field(
        description="Issued-at timestamp (Unix epoch seconds)"
    )
    exp: int = Field(
        description="Expiration timestamp (Unix epoch seconds)"
    )
    parent_token_hash: Optional[str] = Field(
        default=None,
        description="SHA-256 hash of the parent raw JWT string (null for root)"
    )
    nonce: str = Field(
        default_factory=lambda: uuid.uuid4().hex[:12],
        description="Cryptographic nonce to ensure uniqueness"
    )


class RootTokenRequest(BaseModel):
    """
    Request model to mint a root token from server-side ROOT_POLICIES.
    Supports task_type or task_name, originating_user or user_id.
    """
    task_type: Optional[str] = Field(
        default=None,
        json_schema_extra={"example": "financial_analysis_task"},
        description="Registered server policy task name"
    )
    task_name: Optional[str] = Field(
        default=None,
        description="Alias for task_type"
    )
    originating_user: Optional[str] = Field(
        default=None,
        json_schema_extra={"example": "USER-001"},
        description="Originating user ID"
    )
    user_id: Optional[str] = Field(
        default=None,
        description="Alias for originating_user"
    )
    target_agent: str = Field(
        default="agent_a",
        json_schema_extra={"example": "agent_a"},
        description="Designated root agent"
    )
    ttl_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        le=3600,
        description="Optional custom TTL"
    )

    def get_task_type(self) -> str:
        return self.task_type or self.task_name or "financial_analysis_task"

    def get_user_id(self) -> str:
        return self.originating_user or self.user_id or "user_root"


class ChildTokenRequest(BaseModel):
    """
    Request model to derive a scoped child token.
    Supports target_agent or delegatee.
    """
    parent_token: str = Field(
        description="Encoded parent JWT delegation token"
    )
    target_agent: Optional[str] = Field(
        default=None,
        json_schema_extra={"example": "agent_b"},
        description="Target delegatee agent ID"
    )
    delegatee: Optional[str] = Field(
        default=None,
        description="Alias for target_agent"
    )
    requested_scopes: List[str] = Field(
        json_schema_extra={"example": ["financials:read:summary"]},
        description="Requested operational scopes (must be subset of parent)"
    )
    requested_data_scope: DataScope = Field(
        default_factory=DataScope,
        description="Requested customer data scope (must be subset of parent)"
    )
    ttl_seconds: Optional[int] = Field(
        default=None,
        ge=1,
        le=3600,
        description="Requested TTL (bounded by remaining parent lifetime)"
    )

    def get_target_agent(self) -> str:
        target = self.target_agent or self.delegatee
        if not target:
            raise ValueError("Must provide target_agent or delegatee")
        return target


class TokenValidationRequest(BaseModel):
    """
    Comprehensive token validation request.
    """
    token: str = Field(description="JWT token to validate")
    expected_audience: Optional[str] = Field(default=None, description="Expected recipient agent ID (e.g. 'agent_b')")
    required_operation: Optional[str] = Field(default=None, description="Operational scope required (e.g. 'financials:read:summary')")
    target_customer_id: Optional[str] = Field(default=None, description="Target customer ID (e.g. 'CUST-101')")
    target_resource: Optional[str] = Field(default=None, description="Resource domain required (e.g. 'customer_financials')")


class TokenResponse(BaseModel):
    """
    Response model returned when a delegation token is minted or derived.
    """
    token: str = Field(description="Signed Ed25519 JWT string")
    token_id: str = Field(description="JTI of the token")
    chain_id: str = Field(description="Correlation chain ID")
    parent_token_id: Optional[str] = Field(default=None)
    depth: int
    scopes: List[str]
    resource: str
    data_scope: DataScope
    expires_at: str
    token_hash: str


class PublicKeyResponse(BaseModel):
    """
    Public key export for signature verification.
    """
    algorithm: str = "Ed25519"
    issuer: str = "delegation-governor"
    public_key_hex: str
    public_key_pem: str

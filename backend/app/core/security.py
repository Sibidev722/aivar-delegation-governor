import hashlib
import json
import time
from typing import Any, Optional
import jwt
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from app.config import settings
from app.core.logging import logger
from app.core.exceptions import (
    InvalidTokenSignatureException,
    TokenExpiredException,
    AudienceMismatchException
)
from app.models.token import TokenClaims


class CryptoManager:
    """
    Ed25519 cryptographic key management.
    The private key is exclusively held in memory by the Delegation Governor.
    """
    _private_key: ed25519.Ed25519PrivateKey
    _public_key: ed25519.Ed25519PublicKey

    def __init__(self) -> None:
        self._init_keys()

    def _init_keys(self) -> None:
        if settings.ED25519_PRIVATE_KEY_HEX:
            try:
                raw_bytes = bytes.fromhex(settings.ED25519_PRIVATE_KEY_HEX.strip())
                if len(raw_bytes) != 32:
                    raise ValueError(f"Ed25519 seed must be 32 bytes (64 hex characters), got {len(raw_bytes)} bytes.")
                self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)
                self._public_key = self._private_key.public_key()
                logger.info("Loaded Ed25519 private key from environment configuration.")
            except Exception as e:
                logger.error(f"Failed to load configured Ed25519 key: {e}. Generating ephemeral keypair.")
                self._private_key = ed25519.Ed25519PrivateKey.generate()
                self._public_key = self._private_key.public_key()
        else:
            # Ephemeral generation for development/testing
            self._private_key = ed25519.Ed25519PrivateKey.generate()
            self._public_key = self._private_key.public_key()
            logger.info("Generated ephemeral Ed25519 keypair for Governor service.")

    @property
    def private_key(self) -> ed25519.Ed25519PrivateKey:
        """Governor-only access to private signing key."""
        return self._private_key

    @property
    def public_key(self) -> ed25519.Ed25519PublicKey:
        """Public key for token signature verification."""
        return self._public_key

    def get_public_key_hex(self) -> str:
        """Return raw 32-byte public key as hex string."""
        raw_public_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        )
        return raw_public_bytes.hex()

    def get_public_key_pem(self) -> str:
        """Return SubjectPublicKeyInfo PEM string."""
        pem_bytes = self._public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem_bytes.decode("utf-8")


# Global cryptographic manager instance
crypto_manager = CryptoManager()


def compute_sha256(data: str) -> str:
    """Compute standard SHA-256 hexadecimal digest of input string."""
    return hashlib.sha256(data.encode("utf-8")).hexdigest()


def compute_token_hash(token_str: str) -> str:
    """Compute SHA-256 hash of a raw JWT string."""
    return compute_sha256(token_str.strip())


def compute_canonical_json_hash(payload: dict[str, Any], previous_hash: str = "") -> str:
    """
    Compute canonical SHA-256 hash of a dictionary (sorted keys, compact separators)
    chained with previous hash.
    """
    canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    combined = f"{canonical_str}{previous_hash}"
    return hashlib.sha256(combined.encode("utf-8")).hexdigest()


def sign_token_claims(claims: TokenClaims) -> str:
    """
    Cryptographically sign TokenClaims using the Governor's Ed25519 private key.
    Returns: Encoded JWT string.
    """
    payload = claims.model_dump()
    return jwt.encode(payload, crypto_manager.private_key, algorithm="EdDSA")


def decode_and_verify_token(
    token_str: str,
    expected_audience: Optional[str] = None,
    verify_exp: bool = True
) -> TokenClaims:
    """
    Verify Ed25519 signature, issuer, expiry, and audience of a JWT delegation token.
    Raises:
        InvalidTokenSignatureException: if signature or issuer is invalid or payload is corrupted.
        TokenExpiredException: if token exp has elapsed.
        AudienceMismatchException: if token audience does not match expected agent.
    Returns:
        Validated TokenClaims instance.
    """
    if not token_str or not isinstance(token_str, str):
        raise InvalidTokenSignatureException("Missing or invalid token string.")

    try:
        payload = jwt.decode(
            token_str.strip(),
            crypto_manager.public_key,
            algorithms=["EdDSA"],
            issuer="delegation-governor",
            options={
                "verify_signature": True,
                "verify_exp": verify_exp,
                "verify_iss": True,
                "verify_aud": False,  # Evaluated explicitly below for granular AudienceMismatchException
                "require": ["jti", "chain_id", "iss", "sub", "aud", "scopes", "resource", "data_scope", "depth", "iat", "exp"]
            }
        )
        claims = TokenClaims(**payload)

        if expected_audience and claims.aud != expected_audience:
            raise AudienceMismatchException(
                f"Token audience '{claims.aud}' does not match expected recipient '{expected_audience}'."
            )

        return claims

    except jwt.ExpiredSignatureError:
        raise TokenExpiredException("Delegation token has expired.")
    except AudienceMismatchException:
        raise
    except (jwt.InvalidSignatureError, jwt.DecodeError, jwt.InvalidIssuerError, Exception) as e:
        logger.warning(f"Token signature verification failed: {e}")
        raise InvalidTokenSignatureException(f"Token verification failed: {str(e)}")

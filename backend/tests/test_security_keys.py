import pytest
from app.core.security import CryptoManager, compute_sha256, compute_canonical_json_hash


def test_crypto_manager_keypair_generation():
    """Verify Ed25519 keypair generation and public key exports."""
    mgr = CryptoManager()
    assert mgr.private_key is not None
    assert mgr.public_key is not None
    
    pub_hex = mgr.get_public_key_hex()
    assert len(pub_hex) == 64  # 32 bytes in hex = 64 characters
    
    pub_pem = mgr.get_public_key_pem()
    assert "BEGIN PUBLIC KEY" in pub_pem


def test_compute_sha256():
    """Verify SHA-256 string hashing."""
    h1 = compute_sha256("test_string_payload")
    h2 = compute_sha256("test_string_payload")
    h3 = compute_sha256("different_string")
    
    assert h1 == h2
    assert h1 != h3
    assert len(h1) == 64


def test_canonical_json_hash():
    """Verify deterministic hashing of JSON objects with key sorting."""
    payload_a = {"z_key": 1, "a_key": "val", "data": [1, 2, 3]}
    payload_b = {"a_key": "val", "data": [1, 2, 3], "z_key": 1}
    
    hash_a = compute_canonical_json_hash(payload_a, previous_hash="genesis_000")
    hash_b = compute_canonical_json_hash(payload_b, previous_hash="genesis_000")
    
    assert hash_a == hash_b
    assert len(hash_a) == 64

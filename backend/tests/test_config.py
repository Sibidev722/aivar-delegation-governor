import pytest
from pydantic import ValidationError
from app.config import Settings


def test_default_settings():
    """Test standard settings defaults."""
    cfg = Settings(
        MONGODB_URI="mongodb://localhost:27017",
        CORS_ORIGINS=["http://localhost:3000"]
    )
    assert cfg.PROJECT_NAME == "Delegation Chain Governor"
    assert cfg.MAX_DELEGATION_DEPTH == 4
    assert cfg.DEFAULT_TOKEN_TTL_SECONDS == 300
    assert "http://localhost:3000" in cfg.CORS_ORIGINS


def test_cors_origins_parsing():
    """Test parsing comma-separated string or JSON string CORS origins."""
    # 1. Comma-separated
    cfg1 = Settings(CORS_ORIGINS="http://localhost:3000, http://example.com")
    assert cfg1.CORS_ORIGINS == ["http://localhost:3000", "http://example.com"]

    # 2. JSON list format
    cfg2 = Settings(CORS_ORIGINS='["http://site1.com", "http://site2.com"]')
    assert cfg2.CORS_ORIGINS == ["http://site1.com", "http://site2.com"]


def test_invalid_mongodb_uri():
    """Test validation failure for malformed MongoDB URI."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(MONGODB_URI="postgres://user:pass@localhost:5432/db")
    assert "MONGODB_URI" in str(exc_info.value)


def test_invalid_delegation_depth():
    """Test validation bounds on MAX_DELEGATION_DEPTH."""
    with pytest.raises(ValidationError):
        Settings(MAX_DELEGATION_DEPTH=0)  # Must be >= 1

    with pytest.raises(ValidationError):
        Settings(MAX_DELEGATION_DEPTH=20)  # Must be <= 10

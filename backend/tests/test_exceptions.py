import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
from app.core.exceptions import (
    GovernanceException,
    ScopeExpansionForbiddenException,
    DataScopeViolationException,
    governance_exception_handler
)


@pytest.fixture
def test_app_with_exceptions():
    """Create a minimal app with exception handlers to test error responses."""
    test_app = FastAPI()
    test_app.add_exception_handler(GovernanceException, governance_exception_handler)

    @test_app.get("/trigger-scope-error")
    async def trigger_scope_error():
        raise ScopeExpansionForbiddenException(
            message="Cannot expand scope from read to write",
            details={"requested": "write", "held": "read"},
            chain_id="test-chain-99"
        )

    @test_app.get("/trigger-data-error")
    async def trigger_data_error():
        raise DataScopeViolationException(
            message="Unauthorized customer access",
            details={"customer_id": "CUST-999"}
        )

    return test_app


@pytest.mark.asyncio
async def test_governance_exception_response_structure(test_app_with_exceptions):
    """Verify GovernanceException returns standard error structure with HTTP 403."""
    transport = ASGITransport(app=test_app_with_exceptions)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/trigger-scope-error")
        assert res.status_code == 403
        data = res.json()
        assert data["status"] == "error"
        assert data["error_code"] == "SCOPE_EXPANSION_FORBIDDEN"
        assert data["message"] == "Cannot expand scope from read to write"
        assert data["chain_id"] == "test-chain-99"
        assert "timestamp" in data
        assert data["details"]["requested"] == "write"


@pytest.mark.asyncio
async def test_data_scope_exception(test_app_with_exceptions):
    """Verify DataScopeViolationException error payload."""
    transport = ASGITransport(app=test_app_with_exceptions)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        res = await client.get("/trigger-data-error")
        assert res.status_code == 403
        data = res.json()
        assert data["status"] == "error"
        assert data["error_code"] == "DATA_SCOPE_VIOLATION"
        assert data["details"]["customer_id"] == "CUST-999"

import pytest
from httpx import AsyncClient
from app.db.session import DatabaseSession


@pytest.mark.asyncio
async def test_root_endpoint(async_client: AsyncClient):
    """Test root application status endpoint."""
    response = await async_client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "version" in data
    assert "health_check" in data


@pytest.mark.asyncio
async def test_health_liveness(async_client: AsyncClient):
    """Test liveness probe returns healthy."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Delegation Chain Governor"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_health_readiness_connected(async_client: AsyncClient):
    """Test readiness probe returns ready when DB is connected."""
    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
    assert data["database"]["status"] == "connected"
    assert "latency_ms" in data["database"]


@pytest.mark.asyncio
async def test_health_readiness_disconnected(async_client: AsyncClient, monkeypatch):
    """Test readiness probe returns 503 when DB connection fails."""
    async def mock_unhealthy_check():
        return False, 0.0, "Connection refused"

    monkeypatch.setattr(DatabaseSession, "check_health", mock_unhealthy_check)

    response = await async_client.get("/api/v1/health/ready")
    assert response.status_code == 503
    data = response.json()
    assert data["status"] == "unhealthy"
    assert data["database"]["status"] == "disconnected"
    assert "error" in data


@pytest.mark.asyncio
async def test_request_id_middleware(async_client: AsyncClient):
    """Test request ID generation and propagation in response headers."""
    # 1. Without custom request ID -> Server generates UUID
    res1 = await async_client.get("/api/v1/health")
    assert "X-Request-ID" in res1.headers
    assert len(res1.headers["X-Request-ID"]) > 0
    assert "X-Execution-Time-MS" in res1.headers

    # 2. With custom request ID -> Server echoes back custom request ID
    custom_id = "test-req-custom-12345"
    res2 = await async_client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert res2.headers.get("X-Request-ID") == custom_id

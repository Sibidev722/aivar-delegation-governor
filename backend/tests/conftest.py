import sys
import os
from pathlib import Path
import pytest
from httpx import AsyncClient, ASGITransport
import mongomock_motor

# Ensure backend directory is in sys.path
backend_path = Path(__file__).resolve().parent.parent
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from app.main import app
from app.db.session import DatabaseSession


@pytest.fixture(autouse=True)
async def setup_mock_db():
    """
    Inject a fresh in-memory mock MongoDB database for tests.
    """
    mock_client = mongomock_motor.AsyncMongoMockClient()
    mock_db = mock_client["test_delegation_governor"]
    DatabaseSession.set_mock_db(mock_db)
    from app.db.seed import seed_financial_data
    await seed_financial_data(num_customers=150, force_reseed=True)
    yield mock_db
    DatabaseSession.clear_mock_db()


@pytest.fixture
async def async_client():
    """
    Async HTTP client for testing FastAPI endpoints.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

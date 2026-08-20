import time
from typing import Any, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings
from app.core.logging import logger


class DatabaseSession:
    """
    MongoDB Async connection manager using Motor.
    """
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None
    _mock_db: Optional[Any] = None

    @classmethod
    async def connect(cls) -> None:
        """Initialize connection pool to MongoDB."""
        if cls._mock_db is not None:
            cls.db = cls._mock_db
            logger.info("Using mock database instance for testing.")
            return

        try:
            logger.info(f"Connecting to MongoDB database: {settings.MONGODB_DB_NAME}...")
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                serverSelectionTimeoutMS=settings.MONGODB_SERVER_SELECTION_TIMEOUT_MS,
                connectTimeoutMS=settings.MONGODB_CONNECT_TIMEOUT_MS,
            )
            cls.db = cls.client[settings.MONGODB_DB_NAME]
            # Verify connectivity with an initial ping
            await cls.client.admin.command("ping")
            logger.info("Successfully connected to MongoDB Atlas / cluster.")
        except Exception as e:
            logger.warning(
                f"Initial MongoDB connection failed: {e}. App will start, but readiness probe will report unavailable."
            )

    @classmethod
    async def disconnect(cls) -> None:
        """Close connection pool."""
        if cls.client:
            cls.client.close()
            cls.client = None
            cls.db = None
            logger.info("Closed MongoDB connection pool.")

    @classmethod
    def get_db(cls) -> Optional[AsyncIOMotorDatabase]:
        """Get the active database handle."""
        if cls._mock_db is not None:
            return cls._mock_db
        return cls.db

    @classmethod
    def set_mock_db(cls, mock_db: Any) -> None:
        """Inject mock database instance (used by test suites)."""
        cls._mock_db = mock_db
        cls.db = mock_db

    @classmethod
    def clear_mock_db(cls) -> None:
        """Clear test mock database."""
        cls._mock_db = None
        cls.db = None

    @classmethod
    async def check_health(cls) -> Tuple[bool, float, Optional[str]]:
        """
        Check database connectivity with a ping command.
        Returns: (is_healthy, latency_ms, error_message)
        """
        if cls._mock_db is not None:
            return True, 0.5, None

        if cls.client is None or cls.db is None:
            return False, 0.0, "Database client not initialized"

        start_time = time.perf_counter()
        try:
            await cls.client.admin.command("ping")
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return True, round(latency_ms, 2), None
        except Exception as e:
            latency_ms = (time.perf_counter() - start_time) * 1000.0
            return False, round(latency_ms, 2), str(e)


async def get_db() -> Optional[AsyncIOMotorDatabase]:
    """Dependency / helper for database injection."""
    return DatabaseSession.get_db()

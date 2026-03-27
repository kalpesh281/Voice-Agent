import asyncio
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None

MAX_RETRIES = 3
RETRY_DELAY = 2.0


async def connect(uri: str, database: str) -> AsyncIOMotorDatabase:
    global _client, _db

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            _client = AsyncIOMotorClient(
                uri,
                maxPoolSize=10,
                minPoolSize=2,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                retryWrites=True,
            )
            await _client.admin.command("ping")
            _db = _client[database]
            logger.info("Connected to MongoDB: %s", database)
            return _db
        except Exception as e:
            if attempt == MAX_RETRIES:
                logger.error("Failed to connect to MongoDB after %d attempts: %s", MAX_RETRIES, e)
                raise
            logger.warning("MongoDB connection attempt %d failed: %s. Retrying in %.1fs...", attempt, e, RETRY_DELAY * attempt)
            await asyncio.sleep(RETRY_DELAY * attempt)

    raise RuntimeError("Unreachable")


async def disconnect():
    global _client, _db
    if _client:
        _client.close()
        logger.info("Disconnected from MongoDB")
    _client = None
    _db = None


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("Database not connected. Call connect() first.")
    return _db


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("Database not connected. Call connect() first.")
    return _client

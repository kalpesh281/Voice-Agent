"""MongoDB connection manager — dual connection architecture.

Platform DB (our MongoDB):
  - clients collection: client configs from onboarding API
  - bookings collection: all bookings made through voice agent
  - checkpoints: LangGraph conversation state

Client DB (client's MongoDB):
  - Their data: rooms, tables, courts, etc.
  - We only READ from this — never write to client's collections
"""

import asyncio
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2.0

# Platform DB (our data: clients, bookings, checkpoints)
_platform_motor: AsyncIOMotorClient | None = None
_platform_db: AsyncIOMotorDatabase | None = None

# Client DB (their data: rooms, tables, courts — read only)
_client_motor: AsyncIOMotorClient | None = None
_client_db: AsyncIOMotorDatabase | None = None


async def _connect_one(uri: str, database: str, label: str) -> tuple[AsyncIOMotorClient, AsyncIOMotorDatabase]:
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            client = AsyncIOMotorClient(
                uri,
                maxPoolSize=10,
                minPoolSize=2,
                serverSelectionTimeoutMS=5000,
                connectTimeoutMS=5000,
                retryWrites=True,
            )
            await client.admin.command("ping")
            db = client[database]
            logger.info("Connected to %s DB: %s", label, database)
            return client, db
        except Exception as e:
            if attempt == MAX_RETRIES:
                logger.error("Failed to connect to %s DB after %d attempts: %s", label, MAX_RETRIES, e)
                raise
            delay = RETRY_DELAY * attempt
            logger.warning("%s DB attempt %d failed: %s. Retrying in %.1fs...", label, attempt, e, delay)
            await asyncio.sleep(delay)
    raise RuntimeError("Unreachable")


async def connect_platform(uri: str, database: str) -> AsyncIOMotorDatabase:
    """Connect to the platform database (our data)."""
    global _platform_motor, _platform_db
    _platform_motor, _platform_db = await _connect_one(uri, database, "Platform")
    return _platform_db


async def connect_client(uri: str, database: str) -> AsyncIOMotorDatabase:
    """Connect to a client's database (their data — read only)."""
    global _client_motor, _client_db
    _client_motor, _client_db = await _connect_one(uri, database, "Client")
    return _client_db


async def disconnect():
    global _platform_motor, _platform_db, _client_motor, _client_db

    if _client_motor and _client_motor is not _platform_motor:
        _client_motor.close()
        logger.info("Disconnected from Client DB")

    if _platform_motor:
        _platform_motor.close()
        logger.info("Disconnected from Platform DB")

    _platform_motor = _platform_db = None
    _client_motor = _client_db = None


def get_platform_db() -> AsyncIOMotorDatabase:
    """Our database — clients, bookings, checkpoints."""
    if _platform_db is None:
        raise RuntimeError("Platform DB not connected. Call connect_platform() first.")
    return _platform_db


def get_client_db() -> AsyncIOMotorDatabase:
    """Client's database — rooms, tables, courts (read only)."""
    if _client_db is None:
        raise RuntimeError("Client DB not connected. Call connect_client() first.")
    return _client_db


# Legacy alias for repos that use platform DB
def get_db() -> AsyncIOMotorDatabase:
    return get_platform_db()


def get_platform_client() -> AsyncIOMotorClient:
    if _platform_motor is None:
        raise RuntimeError("Platform DB not connected.")
    return _platform_motor

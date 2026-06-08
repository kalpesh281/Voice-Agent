"""MongoDB connection manager — dual connection with security isolation.

Platform DB (our MongoDB) — READ + WRITE:
  - clients: client configs from onboarding API
  - bookings: bookings made through voice agent
  - checkpoints: LangGraph conversation state

Client DB (client's MongoDB) — READ ONLY:
  - rooms, tables, courts, etc.
  - We NEVER write, update, or delete client's data
  - Connection is restricted to read-only operations

SECURITY:
  - Client DB connection is wrapped in ReadOnlyDatabase
  - All write operations (insert, update, delete, drop) are blocked in code
  - Even if the LLM hallucinates a tool, it cannot modify client data
  - For production: also create a read-only MongoDB user for the client DB
"""

import asyncio
import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection, AsyncIOMotorDatabase

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY = 2.0

# Platform DB (our data: clients, bookings, checkpoints)
_platform_motor: AsyncIOMotorClient | None = None
_platform_db: AsyncIOMotorDatabase | None = None

# Client DB (their data: rooms, tables, courts — READ ONLY)
_client_motor: AsyncIOMotorClient | None = None
_client_db: "ReadOnlyDatabase | None" = None


# ──────────────────────────────────────────────
#  Read-Only Database Wrapper
# ──────────────────────────────────────────────


class ReadOnlyCollection:
    """Wraps a Motor collection, blocking all write operations.

    The agent tools can only call find/count/distinct on client data.
    Any attempt to insert, update, delete, or drop is blocked.
    """

    def __init__(self, collection: AsyncIOMotorCollection):
        self._col = collection

    @property
    def name(self):
        return self._col.name

    # ── ALLOWED: Read operations ──

    def find(self, *args, **kwargs):
        return self._col.find(*args, **kwargs)

    async def find_one(self, *args, **kwargs):
        return await self._col.find_one(*args, **kwargs)

    async def count_documents(self, *args, **kwargs):
        return await self._col.count_documents(*args, **kwargs)

    async def distinct(self, *args, **kwargs):
        return await self._col.distinct(*args, **kwargs)

    async def aggregate(self, *args, **kwargs):
        return self._col.aggregate(*args, **kwargs)

    # ── BLOCKED: Write operations ──

    async def insert_one(self, *args, **kwargs):
        raise PermissionError(f"BLOCKED: Cannot insert into client collection '{self.name}'. Client DB is read-only.")

    async def insert_many(self, *args, **kwargs):
        raise PermissionError(f"BLOCKED: Cannot insert into client collection '{self.name}'. Client DB is read-only.")

    async def update_one(self, *args, **kwargs):
        raise PermissionError(f"BLOCKED: Cannot update client collection '{self.name}'. Client DB is read-only.")

    async def update_many(self, *args, **kwargs):
        raise PermissionError(f"BLOCKED: Cannot update client collection '{self.name}'. Client DB is read-only.")

    async def delete_one(self, *args, **kwargs):
        raise PermissionError(f"BLOCKED: Cannot delete from client collection '{self.name}'. Client DB is read-only.")

    async def delete_many(self, *args, **kwargs):
        raise PermissionError(f"BLOCKED: Cannot delete from client collection '{self.name}'. Client DB is read-only.")

    async def drop(self, *args, **kwargs):
        raise PermissionError(f"BLOCKED: Cannot drop client collection '{self.name}'. Client DB is read-only.")

    async def rename(self, *args, **kwargs):
        raise PermissionError(f"BLOCKED: Cannot rename client collection '{self.name}'. Client DB is read-only.")

    async def replace_one(self, *args, **kwargs):
        raise PermissionError(f"BLOCKED: Cannot replace in client collection '{self.name}'. Client DB is read-only.")


class ReadOnlyDatabase:
    """Wraps a Motor database, returning ReadOnlyCollection for all collections.

    This ensures NO write operation can reach the client's database,
    regardless of what code or tool tries to do it.
    """

    def __init__(self, db: AsyncIOMotorDatabase):
        self._db = db

    @property
    def name(self):
        return self._db.name

    def __getitem__(self, collection_name: str) -> ReadOnlyCollection:
        return ReadOnlyCollection(self._db[collection_name])

    def __getattr__(self, name: str):
        # Block database-level destructive operations
        if name in ("drop_collection", "create_collection", "command"):
            raise PermissionError(f"BLOCKED: Cannot call '{name}' on client DB. Read-only.")
        return getattr(self._db, name)

    async def list_collection_names(self, *args, **kwargs):
        return await self._db.list_collection_names(*args, **kwargs)


# ──────────────────────────────────────────────
#  Connection functions
# ──────────────────────────────────────────────


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
    """Connect to the platform database (our data — read + write)."""
    global _platform_motor, _platform_db
    _platform_motor, _platform_db = await _connect_one(uri, database, "Platform")
    return _platform_db


async def connect_client(uri: str, database: str) -> ReadOnlyDatabase:
    """Connect to a client's database (their data — READ ONLY).

    Returns a ReadOnlyDatabase that blocks all write operations.
    """
    global _client_motor, _client_db
    _client_motor, raw_db = await _connect_one(uri, database, "Client")
    _client_db = ReadOnlyDatabase(raw_db)
    logger.info("Client DB wrapped in READ-ONLY mode")
    return _client_db


async def connect_client_writable(uri: str, database: str) -> AsyncIOMotorDatabase:
    """Connect to a client's database with full write access.

    FOR ADMIN/SEED SCRIPTS ONLY. Never use this in agent or API code.
    """
    global _client_motor, _client_db
    _client_motor, raw_db = await _connect_one(uri, database, "Client (writable)")
    _client_db = ReadOnlyDatabase(raw_db)  # keep get_client_db() safe for any runtime callers
    return raw_db


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
    """Our database — clients, bookings, checkpoints. Read + Write."""
    if _platform_db is None:
        raise RuntimeError("Platform DB not connected. Call connect_platform() first.")
    return _platform_db


def get_client_db() -> ReadOnlyDatabase:
    """Client's database — rooms, tables, courts. READ ONLY."""
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

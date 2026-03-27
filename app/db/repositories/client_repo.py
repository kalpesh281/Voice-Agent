"""Client config repository with field-level encryption.

Sensitive fields encrypted before writing to MongoDB:
  - database.connection_uri  (client's DB password is in this URL)
  - owner.email
  - owner.phone

Even if someone accesses the platform DB directly,
they cannot read client credentials without the ENCRYPTION_KEY.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from app.db.models import ClientConfig
from app.db.mongo import get_db
from app.db.repositories.base import BaseRepository
from app.utils.security import decrypt_sensitive_fields, encrypt_sensitive_fields

logger = logging.getLogger(__name__)

# Fields that get encrypted in MongoDB
SENSITIVE_FIELDS = [
    "database.connection_uri",
    "owner.email",
    "owner.phone",
]


class ClientRepository(BaseRepository):
    """CRUD for the clients collection with automatic encryption."""

    COLLECTION = "clients"

    def _col(self):
        return get_db()[self.COLLECTION]

    async def find_one(self, filter: dict[str, Any]) -> dict | None:
        return await self._col().find_one(filter, {"_id": 0})

    async def find_many(
        self,
        filter: dict[str, Any],
        sort: list[tuple[str, int]] | None = None,
        limit: int = 10,
    ) -> list[dict]:
        cursor = self._col().find(filter, {"_id": 0})
        if sort:
            cursor = cursor.sort(sort)
        return await cursor.to_list(length=limit)

    async def insert_one(self, document: dict[str, Any]) -> str:
        await self._col().insert_one(document)
        return document.get("client_id", "")

    async def update_one(
        self, filter: dict[str, Any], update: dict[str, Any]
    ) -> bool:
        result = await self._col().update_one(filter, {"$set": update})
        return result.modified_count > 0

    async def count(self, filter: dict[str, Any]) -> int:
        return await self._col().count_documents(filter)

    async def distinct(self, field: str, filter: dict[str, Any] | None = None) -> list:
        return await self._col().distinct(field, filter or {})

    # ----- domain helpers (with encryption) -----

    async def get_by_id(self, client_id: str) -> ClientConfig | None:
        """Load client config and decrypt sensitive fields."""
        doc = await self.find_one({"client_id": client_id})
        if doc is None:
            return None
        try:
            doc = decrypt_sensitive_fields(doc, SENSITIVE_FIELDS)
        except (ValueError, Exception) as e:
            logger.error("Failed to decrypt client '%s': %s", client_id, e)
            return None
        return ClientConfig(**doc)

    async def upsert(self, config: ClientConfig) -> str:
        """Save client config with sensitive fields encrypted."""
        data = config.model_dump(mode="json")
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        # Encrypt sensitive fields before writing
        data = encrypt_sensitive_fields(data, SENSITIVE_FIELDS)

        await self._col().update_one(
            {"client_id": config.client_id},
            {"$set": data},
            upsert=True,
        )
        logger.info("Client '%s' saved (sensitive fields encrypted)", config.client_id)
        return config.client_id

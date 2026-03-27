from datetime import datetime, timezone
from typing import Any

from app.db.mongo import get_db
from app.db.models import ClientConfig
from app.db.repositories.base import BaseRepository


class ClientRepository(BaseRepository):
    """CRUD for the clients collection in MongoDB."""

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

    # ----- domain helpers -----

    async def get_by_id(self, client_id: str) -> ClientConfig | None:
        doc = await self.find_one({"client_id": client_id})
        if doc is None:
            return None
        return ClientConfig(**doc)

    async def upsert(self, config: ClientConfig) -> str:
        data = config.model_dump(mode="json")
        data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await self._col().update_one(
            {"client_id": config.client_id},
            {"$set": data},
            upsert=True,
        )
        return config.client_id

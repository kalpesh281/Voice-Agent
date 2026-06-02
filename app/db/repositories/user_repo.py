"""User repository — CRUD for the users collection (platform DB)."""

import logging
from datetime import datetime, timezone
from typing import Any

from app.db.models import ClientUser
from app.db.mongo import get_db
from app.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserRepository(BaseRepository):
    """CRUD for the users collection."""

    COLLECTION = "users"

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
        return document.get("user_id", "")

    async def update_one(
        self, filter: dict[str, Any], update: dict[str, Any]
    ) -> bool:
        result = await self._col().update_one(filter, {"$set": update})
        return result.modified_count > 0

    async def count(self, filter: dict[str, Any]) -> int:
        return await self._col().count_documents(filter)

    async def distinct(self, field: str, filter: dict[str, Any] | None = None) -> list:
        return await self._col().distinct(field, filter or {})

    async def delete_one(self, filter: dict[str, Any]) -> bool:
        result = await self._col().delete_one(filter)
        return result.deleted_count > 0

    # ----- domain helpers -----

    async def get_by_id(self, user_id: str) -> ClientUser | None:
        doc = await self.find_one({"user_id": user_id})
        if doc is None:
            return None
        return ClientUser(**doc)

    async def get_by_email(self, email: str) -> ClientUser | None:
        doc = await self.find_one({"email": email.lower().strip()})
        if doc is None:
            return None
        return ClientUser(**doc)

    async def create(self, user: ClientUser) -> str:
        data = user.model_dump(mode="json")
        data["email"] = data["email"].lower().strip()
        await self.insert_one(data)
        logger.info("User created: %s (%s)", user.user_id, user.email)
        return user.user_id

    async def set_onboarded(self, user_id: str, client_id: str) -> bool:
        return await self.update_one(
            {"user_id": user_id},
            {
                "client_id": client_id,
                "onboarding_complete": True,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        )

    async def delete_user(self, user_id: str) -> bool:
        return await self.delete_one({"user_id": user_id})

    async def ensure_indexes(self):
        """Create unique index on email."""
        await self._col().create_index("email", unique=True)
        await self._col().create_index("user_id", unique=True)
        logger.info("User indexes ensured")

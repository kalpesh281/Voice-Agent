import re
from typing import Any

from app.db.mongo import get_client_db
from app.db.repositories.base import BaseRepository


class ResourceRepository(BaseRepository):
    """Generic resource repository — works for rooms, tables, courts, etc.

    Reads from the CLIENT's database (not platform DB).
    The collection name comes from the client's DatabaseMapping config,
    so one repository class serves all categories.
    """

    def __init__(self, collection_name: str):
        self._collection_name = collection_name

    def _col(self):
        return get_client_db()[self._collection_name]

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
        result = await self._col().insert_one(document)
        return str(result.inserted_id)

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

    async def search(
        self,
        filters: dict[str, Any],
        searchable_fields: list[str],
        sort_field: str = "price_per_night",
        availability_field: str = "available",
        limit: int = 3,
        fuzzy_fields: list[str] | None = None,
        array_fields: list[str] | None = None,
    ) -> list[dict]:
        """Search resources with dynamic field filtering.

        Only applies filters on fields declared in searchable_fields
        to prevent injection of arbitrary query parameters.

        Fields listed in `fuzzy_fields` (typically the resource name) match on
        ANY significant word rather than the whole string — so a caller naming a
        room ("Maharaja deluxe suite") still finds "Maharaja Deluxe King" via the
        shared word "Maharaja", instead of needing the exact full name.

        Fields listed in `array_fields` (e.g. `amenities`, a list of descriptive
        phrases) match by keyword: EACH significant word in the value must appear
        in some array element. So "private pool butler" returns only rooms whose
        amenities mention a private pool AND a butler — letting a caller shop by
        feature without knowing room names.
        """
        query: dict[str, Any] = {availability_field: True}
        fuzzy = set(fuzzy_fields or [])
        arrays = set(array_fields or [])
        and_clauses: list[dict[str, Any]] = []

        for field, value in filters.items():
            if value is None or field not in searchable_fields:
                continue
            if field in arrays and isinstance(value, str):
                # Each keyword must match some element of the array field.
                words = [w for w in value.split() if len(w) > 2] or [value]
                for w in words:
                    and_clauses.append({field: {"$regex": re.escape(w), "$options": "i"}})
            elif field in fuzzy and isinstance(value, str):
                # Match any word >3 chars from the spoken value (case-insensitive).
                words = [re.escape(w) for w in value.split() if len(w) > 3]
                pattern = "|".join(words) if words else re.escape(value)
                query[field] = {"$regex": pattern, "$options": "i"}
            elif isinstance(value, str):
                query[field] = {"$regex": f"^{value}$", "$options": "i"}
            elif isinstance(value, (int, float)):
                # For numeric searchable fields, treat as max filter
                # (e.g., max_price, max_guests threshold)
                if field.startswith("max_") or field.endswith("_max"):
                    query[field] = {"$gte": value}
                elif field.startswith("min_") or field.endswith("_min"):
                    query[field] = {"$lte": value}
                else:
                    query[field] = value
            else:
                query[field] = value

        if and_clauses:
            query["$and"] = and_clauses

        cursor = self._col().find(query, {"_id": 0}).sort(sort_field, 1).limit(limit)
        return await cursor.to_list(length=limit)

    async def get_by_resource_id(
        self, resource_id: str, id_field: str = "id"
    ) -> dict | None:
        return await self.find_one({id_field: resource_id})

    async def get_available_values(
        self, field: str, availability_field: str = "available"
    ) -> list:
        return await self.distinct(field, {availability_field: True})

    async def insert_many(self, documents: list[dict]) -> int:
        if not documents:
            return 0
        result = await self._col().insert_many(documents)
        return len(result.inserted_ids)

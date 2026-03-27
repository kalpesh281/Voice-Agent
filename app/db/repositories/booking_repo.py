import logging
from datetime import datetime, timezone
from typing import Any

from app.db.mongo import get_db
from app.db.models import Booking
from app.db.repositories.base import BaseRepository
from app.utils.security import decrypt_sensitive_fields, encrypt_sensitive_fields

logger = logging.getLogger(__name__)

SENSITIVE_BOOKING_FIELDS = [
    "customer_phone",
    "customer_email",
]


class BookingRepository(BaseRepository):
    """Generic booking repository — works for any category."""

    def __init__(self, collection_name: str = "bookings"):
        self._collection_name = collection_name

    def _col(self):
        return get_db()[self._collection_name]

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
        return document.get("booking_id", "")

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

    async def generate_booking_id(self, client_id: str) -> str:
        today = datetime.now(timezone.utc).strftime("%Y%m%d")
        prefix = f"BK-{today}"
        existing = await self.count({"booking_id": {"$regex": f"^{prefix}"}})
        seq = existing + 1
        return f"{prefix}-{seq:03d}"

    async def save_booking(self, booking: Booking) -> str:
        if not booking.booking_id:
            booking.booking_id = await self.generate_booking_id(booking.client_id)
        booking.booked_at = datetime.now(timezone.utc)

        data = booking.model_dump(mode="json")
        data = encrypt_sensitive_fields(data, SENSITIVE_BOOKING_FIELDS)
        await self.insert_one(data)
        logger.info("Booking '%s' saved (PII encrypted)", booking.booking_id)
        return booking.booking_id

    async def get_booking(self, booking_id: str) -> Booking | None:
        doc = await self.find_one({"booking_id": booking_id})
        if doc is None:
            return None
        doc = decrypt_sensitive_fields(doc, SENSITIVE_BOOKING_FIELDS)
        return Booking(**doc)

    async def get_bookings_by_client(
        self, client_id: str, limit: int = 50
    ) -> list[Booking]:
        docs = await self.find_many(
            {"client_id": client_id},
            sort=[("booked_at", -1)],
            limit=limit,
        )
        return [Booking(**doc) for doc in docs]

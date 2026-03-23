import json
import os
from datetime import datetime, timezone
from pathlib import Path

import aiofiles

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
BOOKINGS_FILE = DATA_DIR / "bookings.json"


async def load_bookings() -> dict:
    if not BOOKINGS_FILE.exists():
        return {"bookings": []}
    async with aiofiles.open(BOOKINGS_FILE, "r") as f:
        content = await f.read()
        return json.loads(content) if content.strip() else {"bookings": []}


async def save_booking(booking: dict) -> str:
    data = await load_bookings()
    booking_id = generate_booking_id(len(data["bookings"]) + 1)
    booking["booking_id"] = booking_id
    booking["booked_at"] = datetime.now(timezone.utc).isoformat()
    booking["status"] = "confirmed"
    data["bookings"].append(booking)

    os.makedirs(DATA_DIR, exist_ok=True)
    async with aiofiles.open(BOOKINGS_FILE, "w") as f:
        await f.write(json.dumps(data, indent=2))

    return booking_id


def generate_booking_id(seq: int) -> str:
    today = datetime.now(timezone.utc).strftime("%Y%m%d")
    return f"BK-{today}-{seq:03d}"


async def get_booking(booking_id: str) -> dict | None:
    data = await load_bookings()
    for b in data["bookings"]:
        if b["booking_id"] == booking_id:
            return b
    return None

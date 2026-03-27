"""Seed resources (rooms, tables, courts) into MongoDB.

Usage:
    poetry run python scripts/seed_resources.py                  # seeds hotel rooms (default)
    poetry run python scripts/seed_resources.py --category restaurant
    poetry run python scripts/seed_resources.py --category cricket_ground
    poetry run python scripts/seed_resources.py --all
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.db.mongo import connect_client, disconnect, get_client_db


# ──────────────────────────────────────────────
#  Resource data per category
# ──────────────────────────────────────────────

def load_hotel_rooms() -> list[dict]:
    """Load rooms from existing data/rooms.json."""
    rooms_file = Path(__file__).resolve().parent.parent / "data" / "rooms.json"
    if rooms_file.exists():
        with open(rooms_file) as f:
            data = json.load(f)
        return data.get("rooms", [])

    # Fallback: return empty if file doesn't exist
    print("  Warning: data/rooms.json not found, no rooms seeded.")
    return []


RESTAURANT_TABLES = [
    {
        "table_id": "table-001",
        "name": "Window Table A1",
        "section": "window",
        "max_guests": 2,
        "outdoor": False,
        "price_per_head": 1500,
        "description": "Intimate window seat with a view of Bandra's Linking Road.",
        "available": True,
    },
    {
        "table_id": "table-002",
        "name": "Garden Table G1",
        "section": "garden",
        "max_guests": 4,
        "outdoor": True,
        "price_per_head": 1200,
        "description": "Shaded outdoor table surrounded by tropical plants and fairy lights.",
        "available": True,
    },
    {
        "table_id": "table-003",
        "name": "Private Dining Room",
        "section": "private",
        "max_guests": 8,
        "outdoor": False,
        "price_per_head": 2500,
        "description": "Exclusive enclosed room with personal service — perfect for celebrations.",
        "available": True,
    },
    {
        "table_id": "table-004",
        "name": "Bar Counter Seat B1",
        "section": "bar",
        "max_guests": 2,
        "outdoor": False,
        "price_per_head": 800,
        "description": "Front-row seat at the bar with live kitchen views.",
        "available": True,
    },
    {
        "table_id": "table-005",
        "name": "Terrace Table T1",
        "section": "terrace",
        "max_guests": 6,
        "outdoor": True,
        "price_per_head": 1800,
        "description": "Rooftop terrace table with panoramic Mumbai skyline views.",
        "available": False,
    },
    {
        "table_id": "table-006",
        "name": "Main Hall M1",
        "section": "main",
        "max_guests": 4,
        "outdoor": False,
        "price_per_head": 1000,
        "description": "Central dining area with warm lighting and live music on weekends.",
        "available": True,
    },
    {
        "table_id": "table-007",
        "name": "Garden Table G2",
        "section": "garden",
        "max_guests": 6,
        "outdoor": True,
        "price_per_head": 1200,
        "description": "Large garden table near the fountain — ideal for group gatherings.",
        "available": True,
    },
    {
        "table_id": "table-008",
        "name": "Window Table A2",
        "section": "window",
        "max_guests": 4,
        "outdoor": False,
        "price_per_head": 1500,
        "description": "Spacious window table perfect for a family of four with street views.",
        "available": False,
    },
]

SPORTS_COURTS = [
    {
        "court_id": "court-001",
        "name": "Cricket Ground Alpha",
        "sport": "cricket",
        "surface": "turf",
        "capacity": 22,
        "indoor": False,
        "floodlights": True,
        "price_per_slot": 5000,
        "description": "Full-size turf cricket ground with international-grade pitch and floodlights.",
        "available": True,
    },
    {
        "court_id": "court-002",
        "name": "Cricket Net Practice Bay 1",
        "sport": "cricket",
        "surface": "astro_turf",
        "capacity": 6,
        "indoor": True,
        "floodlights": True,
        "price_per_slot": 1500,
        "description": "Indoor net practice bay with bowling machine included.",
        "available": True,
    },
    {
        "court_id": "court-003",
        "name": "Pickleball Court 1",
        "sport": "pickleball",
        "surface": "hard_court",
        "capacity": 4,
        "indoor": True,
        "floodlights": True,
        "price_per_slot": 1200,
        "description": "Professional indoor pickleball court with cushioned surface.",
        "available": True,
    },
    {
        "court_id": "court-004",
        "name": "Pickleball Court 2",
        "sport": "pickleball",
        "surface": "hard_court",
        "capacity": 4,
        "indoor": False,
        "floodlights": True,
        "price_per_slot": 1000,
        "description": "Outdoor pickleball court with evening floodlight option.",
        "available": True,
    },
    {
        "court_id": "court-005",
        "name": "Cricket Ground Beta",
        "sport": "cricket",
        "surface": "turf",
        "capacity": 22,
        "indoor": False,
        "floodlights": False,
        "price_per_slot": 3500,
        "description": "Daytime-only turf cricket ground — great for morning and afternoon matches.",
        "available": False,
    },
    {
        "court_id": "court-006",
        "name": "Pickleball Court 3",
        "sport": "pickleball",
        "surface": "synthetic",
        "capacity": 4,
        "indoor": True,
        "floodlights": True,
        "price_per_slot": 1400,
        "description": "Premium indoor court with synthetic flooring and spectator seating.",
        "available": True,
    },
]


CATEGORY_DATA = {
    "hotel": ("rooms", load_hotel_rooms),
    "restaurant": ("tables", lambda: RESTAURANT_TABLES),
    "cricket_ground": ("courts", lambda: SPORTS_COURTS),
}


async def seed_category(category: str):
    collection_name, data_fn = CATEGORY_DATA[category]
    data = data_fn()
    if not data:
        print(f"  No data for category: {category}")
        return

    db = get_client_db()
    collection = db[collection_name]

    # Drop existing and re-seed
    await collection.drop()
    result = await collection.insert_many(data)
    print(f"  Seeded {len(result.inserted_ids)} {collection_name} into '{collection_name}' collection")


async def main():
    parser = argparse.ArgumentParser(description="Seed resources into MongoDB")
    parser.add_argument(
        "--category",
        choices=list(CATEGORY_DATA.keys()),
        default="hotel",
        help="Category to seed (default: hotel)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Seed all categories",
    )
    args = parser.parse_args()

    # Seed into client's DB (for testing, use CLIENT_DB_URI or fall back to platform DB)
    uri = settings.client_db_uri or settings.mongodb_uri
    db_name = settings.client_db_name or settings.mongodb_database
    await connect_client(uri, db_name)

    categories = list(CATEGORY_DATA.keys()) if args.all else [args.category]
    for cat in categories:
        await seed_category(cat)

    await disconnect()
    print("\nDone!")


if __name__ == "__main__":
    asyncio.run(main())

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ROOMS_FILE = DATA_DIR / "rooms.json"

_rooms_cache: list[dict] | None = None


def load_rooms() -> list[dict]:
    global _rooms_cache
    if _rooms_cache is not None:
        return _rooms_cache
    with open(ROOMS_FILE, "r") as f:
        data = json.load(f)
    _rooms_cache = data["rooms"]
    return _rooms_cache


def search_rooms(
    room_type: str | None = None,
    view: str | None = None,
    min_guests: int | None = None,
    max_price: float | None = None,
) -> list[dict]:
    rooms = load_rooms()
    results = []

    for room in rooms:
        if not room.get("available", False):
            continue
        if room_type and room["type"].lower() != room_type.lower():
            continue
        if view and room["view"].lower() != view.lower():
            continue
        if min_guests and room["max_guests"] < min_guests:
            continue
        if max_price and room["price_per_night"] > max_price:
            continue
        results.append(room)

    results.sort(key=lambda r: r["price_per_night"])
    return results[:3]


def get_room_by_id(room_id: str) -> dict | None:
    rooms = load_rooms()
    for room in rooms:
        if room["id"] == room_id:
            return room
    return None


def get_available_room_types() -> list[str]:
    rooms = load_rooms()
    types = set()
    for room in rooms:
        if room.get("available", False):
            types.add(room["type"])
    return sorted(types)


def get_available_views() -> list[str]:
    rooms = load_rooms()
    views = set()
    for room in rooms:
        if room.get("available", False):
            views.add(room["view"])
    return sorted(views)


def format_room_for_speech(room: dict) -> str:
    amenities_text = ", ".join(room["amenities"][:4])
    return (
        f"The {room['name']} is a {room['type']} room on floor {room['floor']} "
        f"with a {room['view']} view. It features a {room['bed_type']} bed "
        f"and can accommodate up to {room['max_guests']} guests. "
        f"Key amenities include {amenities_text}. "
        f"The rate is {room['price_per_night']} rupees per night."
    )


def format_rooms_summary(rooms: list[dict]) -> str:
    if not rooms:
        return "No rooms match your criteria."
    lines = []
    for i, room in enumerate(rooms, 1):
        lines.append(
            f"Option {i}: {room['name']} — {room['type']}, "
            f"{room['view']} view, {room['bed_type']} bed, "
            f"up to {room['max_guests']} guests, "
            f"{room['price_per_night']} rupees per night."
        )
    return " ".join(lines)

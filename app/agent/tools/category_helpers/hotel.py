from app.db.models import ClientConfig


def format_room_for_speech(room: dict, config: ClientConfig) -> str:
    """Format a hotel room document into natural speech."""
    name = room.get("name", "")
    room_type = room.get("type", "")
    floor = room.get("floor", "")
    view = room.get("view", "")
    bed = room.get("bed_type", "")
    guests = room.get("max_guests", 2)
    price = room.get("price_per_night", 0)
    amenities = room.get("amenities", [])
    currency = config.business.currency

    amenities_text = ", ".join(amenities[:3]) if amenities else "premium amenities"

    return (
        f"The {name} is a {room_type} room on floor {floor} "
        f"with a {view} view and a {bed} bed. "
        f"It accommodates up to {guests} guests. "
        f"Key features include {amenities_text}. "
        f"The rate is {price:,} {currency} per night."
    )

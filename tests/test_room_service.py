"""Tests for agent.room_service"""

from agent.room_service import (
    load_rooms,
    search_rooms,
    get_room_by_id,
    get_available_room_types,
    get_available_views,
    format_room_for_speech,
    format_rooms_summary,
)


def test_load_rooms_returns_list():
    rooms = load_rooms()
    assert isinstance(rooms, list)
    assert len(rooms) >= 10


def test_all_rooms_have_required_fields():
    rooms = load_rooms()
    required = {"id", "name", "type", "bed_type", "floor", "view", "max_guests", "price_per_night", "available"}
    for room in rooms:
        assert required.issubset(room.keys()), f"Room {room.get('id')} missing fields"


def test_search_rooms_returns_only_available():
    rooms = search_rooms()
    for room in rooms:
        assert room["available"] is True


def test_search_rooms_filter_by_type():
    rooms = search_rooms(room_type="suite")
    for room in rooms:
        assert room["type"] == "suite"


def test_search_rooms_filter_by_view():
    rooms = search_rooms(view="sea")
    for room in rooms:
        assert room["view"] == "sea"


def test_search_rooms_filter_by_guests():
    rooms = search_rooms(min_guests=4)
    for room in rooms:
        assert room["max_guests"] >= 4


def test_search_rooms_filter_by_price():
    rooms = search_rooms(max_price=20000)
    for room in rooms:
        assert room["price_per_night"] <= 20000


def test_search_rooms_returns_max_3():
    rooms = search_rooms()
    assert len(rooms) <= 3


def test_search_rooms_sorted_by_price():
    rooms = search_rooms()
    prices = [r["price_per_night"] for r in rooms]
    assert prices == sorted(prices)


def test_get_room_by_id_found():
    room = get_room_by_id("room-001")
    assert room is not None
    assert room["id"] == "room-001"


def test_get_room_by_id_not_found():
    room = get_room_by_id("room-999")
    assert room is None


def test_available_room_types():
    types = get_available_room_types()
    assert isinstance(types, list)
    assert len(types) > 0
    assert all(isinstance(t, str) for t in types)


def test_available_views():
    views = get_available_views()
    assert isinstance(views, list)
    assert len(views) > 0


def test_format_room_for_speech():
    room = get_room_by_id("room-001")
    text = format_room_for_speech(room)
    assert isinstance(text, str)
    assert "rupees" in text
    assert room["name"] in text


def test_format_rooms_summary_empty():
    assert format_rooms_summary([]) == "No rooms match your criteria."


def test_format_rooms_summary():
    rooms = search_rooms()
    summary = format_rooms_summary(rooms)
    assert "Option 1" in summary

"""Tests for agent.booking_store"""

import json
import pytest
from pathlib import Path

from agent.booking_store import (
    load_bookings,
    save_booking,
    generate_booking_id,
    get_booking,
)


@pytest.mark.asyncio
async def test_load_bookings():
    data = await load_bookings()
    assert "bookings" in data
    assert isinstance(data["bookings"], list)


def test_generate_booking_id_format():
    bid = generate_booking_id(1)
    assert bid.startswith("BK-")
    assert len(bid) == 15  # BK-YYYYMMDD-001


def test_generate_booking_id_sequence():
    bid1 = generate_booking_id(1)
    bid2 = generate_booking_id(2)
    assert bid1.endswith("-001")
    assert bid2.endswith("-002")


@pytest.mark.asyncio
async def test_save_and_get_booking(tmp_path, monkeypatch):
    """Test saving and retrieving a booking using a temp file."""
    temp_file = tmp_path / "bookings.json"
    temp_file.write_text('{"bookings": []}')

    import agent.booking_store as bs
    monkeypatch.setattr(bs, "BOOKINGS_FILE", temp_file)

    booking = {
        "room_id": "room-001",
        "room_name": "Test Room",
        "guest_name": "Test Guest",
        "guest_phone": "1234567890",
        "check_in": "2026-04-01",
        "check_out": "2026-04-03",
        "num_guests": 2,
        "nights": 2,
        "price_per_night": 15000,
        "total_price": 30000,
        "token_amount": 6000,
        "payment_method": "UPI",
        "currency": "INR",
        "special_requests": "",
    }

    booking_id = await save_booking(booking)
    assert booking_id.startswith("BK-")

    # Verify it was saved
    data = json.loads(temp_file.read_text())
    assert len(data["bookings"]) == 1
    assert data["bookings"][0]["guest_name"] == "Test Guest"
    assert data["bookings"][0]["status"] == "confirmed"

    # Verify get_booking works
    found = await get_booking(booking_id)
    assert found is not None
    assert found["booking_id"] == booking_id


@pytest.mark.asyncio
async def test_get_booking_not_found():
    result = await get_booking("BK-99999999-999")
    assert result is None

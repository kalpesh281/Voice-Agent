"""Tests for tools.executor and tools.definitions"""

import json

from tools.definitions import TOOLS
from tools.executor import execute_tool


def test_tools_has_5_definitions():
    assert len(TOOLS) == 5


def test_all_tools_have_name():
    for tool in TOOLS:
        assert "function" in tool
        assert "name" in tool["function"]


def test_tool_names():
    names = {t["function"]["name"] for t in TOOLS}
    expected = {"search_rooms", "get_room_details", "check_availability", "create_booking", "get_booking"}
    assert names == expected


def test_execute_search_rooms():
    result = json.loads(execute_tool("search_rooms", {}))
    assert "found" in result
    assert result["found"] > 0


def test_execute_search_rooms_by_type():
    result = json.loads(execute_tool("search_rooms", {"room_type": "suite"}))
    if result["found"] > 0:
        for room in result["rooms"]:
            assert room["type"] == "suite"


def test_execute_get_room_details():
    result = json.loads(execute_tool("get_room_details", {"room_id": "room-001"}))
    assert "room" in result
    assert result["room"]["id"] == "room-001"


def test_execute_get_room_details_not_found():
    result = json.loads(execute_tool("get_room_details", {"room_id": "room-999"}))
    assert "error" in result


def test_execute_check_availability():
    result = json.loads(execute_tool("check_availability", {
        "room_id": "room-001",
        "check_in": "2026-05-01",
        "check_out": "2026-05-03",
    }))
    assert result["available"] is True
    assert result["nights"] == 2
    assert "total_price" in result
    assert "token_amount" in result


def test_execute_check_availability_booked_room():
    result = json.loads(execute_tool("check_availability", {
        "room_id": "room-002",  # Heritage Garden Twin — booked
        "check_in": "2026-05-01",
        "check_out": "2026-05-03",
    }))
    assert result["available"] is False


def test_execute_unknown_tool():
    result = json.loads(execute_tool("unknown_tool", {}))
    assert "error" in result

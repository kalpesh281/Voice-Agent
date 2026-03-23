from __future__ import annotations

from datetime import datetime
from typing import Any

from livekit.agents import Agent, RunContext, function_tool

from agent.booking_store import save_booking, get_booking as fetch_booking
from agent.room_service import (
    search_rooms as _search_rooms,
    get_room_by_id,
    format_room_for_speech,
    format_rooms_summary,
    get_available_room_types,
    get_available_views,
)

from agent.config import TOKEN_PERCENTAGE, SYSTEM_PROMPT


class HotelAgent(Agent):
    def __init__(self) -> None:
        super().__init__(instructions=SYSTEM_PROMPT)
        self._guest_name: str | None = None
        self._guest_phone: str | None = None
        self._guest_email: str | None = None

    @function_tool()
    async def search_rooms(
        self,
        context: RunContext,
        room_type: str | None = None,
        view: str | None = None,
        num_guests: int | None = None,
        max_price_per_night: float | None = None,
    ) -> dict[str, Any]:
        """Search for available hotel rooms based on guest preferences.

        Args:
            room_type: Type of room — deluxe, superior, suite, penthouse, or villa. Leave empty if no preference.
            view: Preferred view — sea, garden, city, pool, or mountain. Leave empty if no preference.
            num_guests: Number of guests who will be staying.
            max_price_per_night: Maximum budget per night in rupees.
        """
        rooms = _search_rooms(
            room_type=room_type,
            view=view,
            min_guests=num_guests,
            max_price=max_price_per_night,
        )

        if not rooms:
            available_types = get_available_room_types()
            available_views = get_available_views()
            return {
                "found": 0,
                "message": "No rooms match those exact criteria right now.",
                "available_types": available_types,
                "available_views": available_views,
                "hint": "Suggest the guest try a different room type or view. Be helpful, not dismissive.",
            }

        return {
            "found": len(rooms),
            "rooms": [
                {
                    "id": r["id"],
                    "name": r["name"],
                    "type": r["type"],
                    "bed_type": r["bed_type"],
                    "view": r["view"],
                    "floor": r["floor"],
                    "max_guests": r["max_guests"],
                    "price_per_night": r["price_per_night"],
                    "amenities": r["amenities"][:4],
                    "description": r["description"],
                }
                for r in rooms
            ],
            "summary": format_rooms_summary(rooms),
        }

    @function_tool()
    async def get_room_details(
        self,
        context: RunContext,
        room_id: str,
    ) -> dict[str, Any]:
        """Get full details about a specific hotel room including all amenities and description.

        Args:
            room_id: The room ID, e.g. room-001.
        """
        room = get_room_by_id(room_id)
        if not room:
            return {"error": f"Room {room_id} not found."}

        return {
            "room": room,
            "speech_description": format_room_for_speech(room),
            "available": room.get("available", False),
            "status": "available" if room.get("available") else "fully booked",
        }

    @function_tool()
    async def check_availability(
        self,
        context: RunContext,
        room_id: str,
        check_in: str,
        check_out: str,
    ) -> dict[str, Any]:
        """Check if a specific room is available for the given dates.

        Args:
            room_id: The room ID to check.
            check_in: Check-in date in YYYY-MM-DD format.
            check_out: Check-out date in YYYY-MM-DD format.
        """
        room = get_room_by_id(room_id)
        if not room:
            return {"error": f"Room {room_id} not found."}

        if not room.get("available", False):
            return {
                "available": False,
                "room_name": room["name"],
                "message": f"{room['name']} is currently fully booked.",
                "suggestion": "Suggest alternative rooms of similar type.",
            }

        try:
            d_in = datetime.strptime(check_in, "%Y-%m-%d")
            d_out = datetime.strptime(check_out, "%Y-%m-%d")
            nights = (d_out - d_in).days
            if nights <= 0:
                return {"error": "Check-out date must be after check-in date."}
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD."}

        total_price = room["price_per_night"] * nights
        token_amount = int(total_price * TOKEN_PERCENTAGE / 100)

        return {
            "available": True,
            "room_id": room_id,
            "room_name": room["name"],
            "price_per_night": room["price_per_night"],
            "nights": nights,
            "total_price": total_price,
            "token_amount": token_amount,
            "token_percentage": TOKEN_PERCENTAGE,
            "currency": "INR",
        }

    @function_tool()
    async def create_booking(
        self,
        context: RunContext,
        room_id: str,
        guest_name: str,
        guest_phone: str,
        check_in: str,
        check_out: str,
        num_guests: int,
        payment_method: str = "",
        special_requests: str = "",
    ) -> dict[str, Any]:
        """Create a confirmed hotel room booking. Call this ONLY after the guest has confirmed all details and agreed to the token payment.

        Args:
            room_id: The room ID to book, e.g. room-001.
            guest_name: Full name of the guest.
            guest_phone: Guest's phone number.
            check_in: Check-in date in YYYY-MM-DD format.
            check_out: Check-out date in YYYY-MM-DD format.
            num_guests: Number of guests staying.
            payment_method: Payment method chosen — UPI, credit card, or bank transfer.
            special_requests: Any special requests from the guest.
        """
        room = get_room_by_id(room_id)
        if not room:
            return {"error": f"Room {room_id} not found."}
        if not room.get("available", False):
            return {"error": f"Sorry, {room['name']} is currently fully booked."}

        try:
            d_in = datetime.strptime(check_in, "%Y-%m-%d")
            d_out = datetime.strptime(check_out, "%Y-%m-%d")
            nights = (d_out - d_in).days
            if nights <= 0:
                return {"error": "Check-out must be after check-in."}
        except ValueError:
            return {"error": "Invalid date format. Use YYYY-MM-DD."}

        total_price = room["price_per_night"] * nights
        token_amount = int(total_price * TOKEN_PERCENTAGE / 100)

        booking = {
            "room_id": room_id,
            "room_name": room["name"],
            "guest_name": guest_name,
            "guest_phone": guest_phone,
            "check_in": check_in,
            "check_out": check_out,
            "num_guests": num_guests,
            "nights": nights,
            "price_per_night": room["price_per_night"],
            "total_price": total_price,
            "token_amount": token_amount,
            "payment_method": payment_method,
            "currency": "INR",
            "special_requests": special_requests,
        }

        booking_id = await save_booking(booking)

        self._guest_name = guest_name
        self._guest_phone = guest_phone

        return {
            "booking_id": booking_id,
            "room_name": room["name"],
            "guest_name": guest_name,
            "check_in": check_in,
            "check_out": check_out,
            "nights": nights,
            "total_price": total_price,
            "token_amount": token_amount,
            "payment_method": payment_method,
            "currency": "INR",
            "message": f"Booking confirmed! Reference: {booking_id}",
        }

    @function_tool()
    async def get_booking(
        self,
        context: RunContext,
        booking_id: str,
    ) -> dict[str, Any]:
        """Look up an existing booking by its reference ID.

        Args:
            booking_id: The booking reference ID, e.g. BK-20260324-001.
        """
        booking = await fetch_booking(booking_id)
        if not booking:
            return {"error": f"No booking found with ID {booking_id}."}
        return booking

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

TOKEN_PERCENTAGE = 20  # 20% token amount for booking confirmation

SYSTEM_PROMPT = """\
You are Aria, the virtual concierge at The Grand Meridian Palace — a prestigious 5-star luxury hotel \
located on Marine Drive, Mumbai, India. You speak warmly, naturally, and conversationally — \
exactly like a real human receptionist on a phone call. You are NOT a robot.

Your personality:
- Warm, gracious, and genuinely caring — you have the legendary Indian hospitality spirit.
- You speak like a real person. Use natural fillers: "Oh lovely!", "Sure sure!", "Absolutely!", \
  "That sounds wonderful.", "Ji, bilkul!", "No worries at all."
- Speak in flowing sentences. Never bullet points, lists, or markdown.
- Never use abbreviations, symbols, or emojis — you are speaking aloud on a call.
- Keep each response to 2-4 sentences max. Short, natural, human.
- All prices are in Indian Rupees. Always say "rupees" when speaking about money.
- Address the guest by name once you know it.

===== CONVERSATION FLOW — follow this exactly =====

STEP 1 — GREETING:
- Greet the caller warmly. Say Namaste.
- Introduce yourself: "I'm Aria from The Grand Meridian Palace, Mumbai."
- Ask: "How can I help you today?"
- Do NOT ask for their name yet. Wait to hear what they need.

STEP 2 — INTENT CHECK:
- Listen to what the caller says.
- If they ask about hotel rooms, booking, availability, prices, or anything related to the hotel → proceed to Step 3.
- If they ask about something UNRELATED (food delivery, taxi, weather, random questions, etc.) → \
  politely and humbly say: "I'm really sorry, but I can only help with hotel room bookings \
  at The Grand Meridian Palace. Is there anything I can help you with regarding a room or reservation?"
- Never be rude. Always be humble when declining.

STEP 3 — ROOM INFORMATION (keep it short first):
- When the guest asks about rooms or availability, give a SHORT overview first.
- Say something like: "We have several types of rooms available — Deluxe rooms, Suites, Villas, \
  and Penthouses. We have sea views, city views, garden views, and mountain views. \
  Prices start from around 12,500 rupees per night. Would you like to know about any specific type?"
- Use the search_rooms tool to get actual available rooms if they ask.
- Do NOT dump all room details at once. Keep it brief.

STEP 4 — DETAILED ROOM INFO (only when asked):
- If the guest asks about a SPECIFIC room type or wants more details → use get_room_details or search_rooms.
- NOW describe the room in detail — amenities, view, floor, bed type, price, size.
- Paint a picture with words. Make it sound appealing.

STEP 5 — GUEST WANTS TO BOOK:
- When the guest shows interest in booking (says "I want to book", "let's book it", "I'll take it", etc.) → \
  NOW collect their details one by one, naturally:
  a) "May I have your full name please?"
  b) "And a phone number we can reach you on?"
  c) "How many guests will be staying?"
  d) "What dates are you looking at? Check-in and check-out?"
- Ask these naturally in conversation, not all at once like a form.
- Remember all details. Never ask the same thing twice.

STEP 6 — CHECK AVAILABILITY & CONFIRM:
- Use search_rooms to verify the room is still available for their dates.
- If available, read back ALL the details:
  "So let me confirm — {name}, phone {phone}, checking in on {date} and checking out on {date}, \
  {num_guests} guests, in our {room_name} at {price} rupees per night. \
  That comes to {total} rupees for {nights} nights."

STEP 7 — TOKEN PAYMENT:
- After confirming details, say: "To secure your booking, we require a token amount of {20% of total} rupees, \
  which is 20 percent of the total."
- Ask: "Would you like to pay via UPI, credit card, or bank transfer?"
- If the guest agrees to any payment method → proceed to book.
- If the guest hesitates or declines → say "No problem at all! The room will be available for some time. \
  You can call back anytime to complete the booking."

STEP 8 — BOOKING CONFIRMATION:
- Use create_booking to save the reservation.
- Read out the booking reference clearly.
- Say warm closing words: "Wonderful! Your booking is confirmed. We truly look forward to welcoming you \
  at The Grand Meridian Palace. Have a wonderful day!"
- The conversation naturally ends here.

===== IMPORTANT RULES =====
- NEVER make up room data. Always use search_rooms or get_room_details tools.
- NEVER book without calling create_booking.
- If the guest is unclear, ask ONE focused follow-up — don't overwhelm them.
- If no rooms match, relax criteria and re-search. Never say "we have nothing available."
- Remember ALL guest details throughout the call — never re-ask.
- If a room is fully booked, be honest: "I'm sorry, that particular room is currently booked. \
  But let me show you some lovely alternatives."
- Be HUMAN. Pause naturally. React to what they say. Don't sound scripted.
"""


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

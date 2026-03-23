"""
Hotel category — tool execution.
Routes tool calls to hotel room/booking services.
"""

import asyncio
import json
from datetime import datetime

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from core.config import TOKEN_PERCENTAGE
from agent.room_service import (
    search_rooms,
    get_room_by_id,
    format_room_for_speech,
    format_rooms_summary,
    get_available_room_types,
    get_available_views,
)
from agent.booking_store import save_booking, get_booking

console = Console()


def log_tool(name: str, args: dict):
    ts = datetime.now().strftime("%H:%M:%S")
    text = Text()
    text.append(f"  [{ts}]  ", style="dim")
    text.append("   TOOL", style="bold magenta")
    text.append(f"  {name}(", style="magenta")
    arg_parts = [f"{k}={v!r}" for k, v in args.items() if v is not None]
    text.append(", ".join(arg_parts), style="dim magenta")
    text.append(")", style="magenta")
    console.print(text)


def log_result(result: dict):
    ts = datetime.now().strftime("%H:%M:%S")
    text = Text()
    text.append(f"  [{ts}]  ", style="dim")
    text.append("   TOOL", style="bold magenta")
    found = result.get("found", result.get("booking_id", result.get("available", "done")))
    text.append(f"  -> {found}", style="dim")
    console.print(text)


def show_booking_banner(booking_id: str, args: dict, room_name: str, nights: int, total: int, token: int):
    console.print()
    p = Text()
    p.append("BOOKING CONFIRMED\n\n", style="bold")
    p.append(f"  Reference:  {booking_id}\n")
    p.append(f"  Guest:      {args['guest_name']}\n")
    p.append(f"  Room:       {room_name}\n")
    p.append(f"  Dates:      {args['check_in']} to {args['check_out']} ({nights} nights)\n")
    p.append(f"  Total:      Rs.{total:,}\n")
    p.append(f"  Token:      Rs.{token:,}\n")
    p.append(f"  Payment:    {args.get('payment_method', 'N/A')}\n")
    console.print(Panel(p, border_style="green", title="[bold green]Confirmed[/]", padding=(1, 2)))
    console.print()


def execute_tool(name: str, args: dict) -> str:
    """Execute a tool by name and return JSON result."""
    log_tool(name, args)

    if name == "search_rooms":
        rooms = search_rooms(
            room_type=args.get("room_type"), view=args.get("view"),
            min_guests=args.get("num_guests"), max_price=args.get("max_price_per_night"),
        )
        if not rooms:
            result = {
                "found": 0,
                "message": "No rooms match.",
                "available_types": get_available_room_types(),
                "available_views": get_available_views(),
            }
        else:
            result = {
                "found": len(rooms),
                "rooms": [
                    {
                        "id": r["id"], "name": r["name"], "type": r["type"],
                        "bed_type": r["bed_type"], "view": r["view"], "floor": r["floor"],
                        "max_guests": r["max_guests"], "price_per_night": r["price_per_night"],
                        "amenities": r["amenities"][:4], "description": r["description"],
                    }
                    for r in rooms
                ],
                "summary": format_rooms_summary(rooms),
            }

    elif name == "get_room_details":
        room = get_room_by_id(args["room_id"])
        if not room:
            result = {"error": f"Room {args['room_id']} not found."}
        else:
            result = {
                "room": room,
                "speech_description": format_room_for_speech(room),
                "available": room.get("available", False),
                "status": "available" if room.get("available") else "fully booked",
            }

    elif name == "check_availability":
        room = get_room_by_id(args["room_id"])
        if not room:
            result = {"error": "Room not found."}
        elif not room.get("available", False):
            result = {"available": False, "room_name": room["name"], "message": f"{room['name']} is fully booked."}
        else:
            try:
                d_in = datetime.strptime(args["check_in"], "%Y-%m-%d")
                d_out = datetime.strptime(args["check_out"], "%Y-%m-%d")
                nights = (d_out - d_in).days
                total = room["price_per_night"] * nights
                token = int(total * TOKEN_PERCENTAGE / 100)
                result = {
                    "available": True, "room_name": room["name"],
                    "price_per_night": room["price_per_night"], "nights": nights,
                    "total_price": total, "token_amount": token, "currency": "INR",
                }
            except Exception as e:
                result = {"error": str(e)}

    elif name == "create_booking":
        room = get_room_by_id(args["room_id"])
        if not room or not room.get("available"):
            result = {"error": "Room not available."}
        else:
            try:
                d_in = datetime.strptime(args["check_in"], "%Y-%m-%d")
                d_out = datetime.strptime(args["check_out"], "%Y-%m-%d")
                nights = (d_out - d_in).days
                total = room["price_per_night"] * nights
                token = int(total * TOKEN_PERCENTAGE / 100)
                booking = {
                    "room_id": args["room_id"], "room_name": room["name"],
                    "guest_name": args["guest_name"], "guest_phone": args["guest_phone"],
                    "check_in": args["check_in"], "check_out": args["check_out"],
                    "num_guests": args["num_guests"], "nights": nights,
                    "price_per_night": room["price_per_night"], "total_price": total,
                    "token_amount": token, "payment_method": args.get("payment_method", ""),
                    "currency": "INR", "special_requests": args.get("special_requests", ""),
                }
                booking_id = asyncio.get_event_loop().run_until_complete(save_booking(booking))
                result = {
                    "booking_id": booking_id, "room_name": room["name"],
                    "guest_name": args["guest_name"], "total_price": total,
                    "token_amount": token, "message": f"Booking confirmed! Reference: {booking_id}",
                }
                show_booking_banner(booking_id, args, room["name"], nights, total, token)
            except Exception as e:
                result = {"error": str(e)}

    elif name == "get_booking":
        booking = asyncio.get_event_loop().run_until_complete(get_booking(args["booking_id"]))
        result = booking if booking else {"error": "No booking found."}

    else:
        result = {"error": f"Unknown tool: {name}"}

    log_result(result)
    return json.dumps(result)

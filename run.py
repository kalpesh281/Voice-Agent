#!/usr/bin/env python3
"""
The Grand Meridian Palace — Voice Booking Agent
Run: poetry run python run.py

Aria speaks through your speakers. You speak through your mic.
Press ENTER to start recording, ENTER again to stop.
Type 'quit' to exit.
"""

import asyncio
import io
import json
import sys
import tempfile
import threading
import wave
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf
from dotenv import load_dotenv
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from agent.booking_store import save_booking, get_booking
from agent.room_service import (
    search_rooms,
    get_room_by_id,
    format_room_for_speech,
    format_rooms_summary,
    get_available_room_types,
    get_available_views,
)

load_dotenv()

console = Console()
TOKEN_PERCENTAGE = 20
SAMPLE_RATE = 24000
MIC_SAMPLE_RATE = 16000

# ── System prompt ───────────────────────────────────────────────────────

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
- If they ask about hotel rooms, booking, availability, prices → proceed.
- If UNRELATED → politely say you can only help with hotel room bookings.

STEP 3 — ROOM INFORMATION (short first):
- Give a SHORT overview of room types and price range.
- Use search_rooms tool for actual data.

STEP 4 — DETAILED ROOM INFO (only when asked):
- Use get_room_details for specific room details.

STEP 5 — BOOKING:
- Collect: name, phone, number of guests, dates — one by one naturally.

STEP 6 — CONFIRM all details back to the guest.

STEP 7 — TOKEN PAYMENT:
- "Token amount of 20% of total. UPI, credit card, or bank transfer?"
- If agrees → book. If not → "No problem, call back anytime."

STEP 8 — create_booking, read reference, warm goodbye.

RULES:
- NEVER make up room data. Always use tools.
- NEVER book without create_booking.
- Be HUMAN. React naturally.
"""

# ── Tool definitions ────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_rooms",
            "description": "Search available hotel rooms by preferences.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_type": {"type": "string", "description": "deluxe, superior, suite, penthouse, or villa."},
                    "view": {"type": "string", "description": "sea, garden, city, pool, or mountain."},
                    "num_guests": {"type": "integer", "description": "Number of guests."},
                    "max_price_per_night": {"type": "number", "description": "Max budget per night in rupees."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_room_details",
            "description": "Get full details about a specific hotel room.",
            "parameters": {
                "type": "object",
                "properties": {"room_id": {"type": "string", "description": "e.g. room-001."}},
                "required": ["room_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_availability",
            "description": "Check room availability for given dates and calculate pricing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "check_in": {"type": "string", "description": "YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "YYYY-MM-DD"},
                },
                "required": ["room_id", "check_in", "check_out"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_booking",
            "description": "Create a confirmed booking after guest confirms and agrees to token payment.",
            "parameters": {
                "type": "object",
                "properties": {
                    "room_id": {"type": "string"},
                    "guest_name": {"type": "string"},
                    "guest_phone": {"type": "string"},
                    "check_in": {"type": "string", "description": "YYYY-MM-DD"},
                    "check_out": {"type": "string", "description": "YYYY-MM-DD"},
                    "num_guests": {"type": "integer"},
                    "payment_method": {"type": "string", "description": "UPI, credit card, or bank transfer."},
                    "special_requests": {"type": "string"},
                },
                "required": ["room_id", "guest_name", "guest_phone", "check_in", "check_out", "num_guests"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_booking",
            "description": "Look up an existing booking by reference ID.",
            "parameters": {
                "type": "object",
                "properties": {"booking_id": {"type": "string"}},
                "required": ["booking_id"],
            },
        },
    },
]


# ── Voice: TTS (Aria speaks) ───────────────────────────────────────────

def speak(client: OpenAI, text: str):
    """Convert text to speech and play through speakers."""
    ts = datetime.now().strftime("%H:%M:%S")

    # Show what Aria is saying
    aria_text = Text()
    aria_text.append(f"  [{ts}]  ", style="dim")
    aria_text.append("  ARIA", style="bold cyan")
    aria_text.append("  >  ", style="dim")
    aria_text.append(text, style="white")
    console.print(aria_text)

    # Generate speech
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="shimmer",
        input=text,
        response_format="pcm",
        instructions="Speak warmly and clearly like a 5-star Indian hotel concierge. Calm, gracious pace.",
    )

    # Play audio
    audio_data = np.frombuffer(response.content, dtype=np.int16)
    audio_float = audio_data.astype(np.float32) / 32768.0
    sd.play(audio_float, samplerate=SAMPLE_RATE)
    sd.wait()
    console.print()


# ── Voice: STT (User speaks) ───────────────────────────────────────────

def listen(client: OpenAI) -> str:
    """Record from mic and transcribe with Whisper."""
    ts = datetime.now().strftime("%H:%M:%S")

    prompt_text = Text()
    prompt_text.append(f"  [{ts}]  ", style="dim")
    prompt_text.append("  MIC ", style="bold yellow")
    prompt_text.append("  >  ", style="dim")
    prompt_text.append("Press ENTER to start speaking...", style="dim yellow")
    console.print(prompt_text, end="")
    input()

    # Start recording
    recording = []
    is_recording = True

    def callback(indata, frames, time_info, status):
        if is_recording:
            recording.append(indata.copy())

    stream = sd.InputStream(
        samplerate=MIC_SAMPLE_RATE,
        channels=1,
        dtype="int16",
        callback=callback,
    )

    rec_text = Text()
    rec_text.append(f"  [{ts}]  ", style="dim")
    rec_text.append("  MIC ", style="bold red")
    rec_text.append("  >  ", style="dim")
    rec_text.append("Recording... Press ENTER to stop.", style="bold red")
    console.print(rec_text, end="")

    stream.start()
    input()
    is_recording = False
    stream.stop()
    stream.close()

    if not recording:
        return ""

    # Save to temp wav file
    audio_data = np.concatenate(recording, axis=0)
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    sf.write(tmp.name, audio_data, MIC_SAMPLE_RATE)

    # Transcribe with Whisper
    with open(tmp.name, "rb") as f:
        transcription = client.audio.transcriptions.create(
            model="gpt-4o-transcribe",
            file=f,
            language="en",
        )

    Path(tmp.name).unlink(missing_ok=True)

    text = transcription.text.strip()

    # Show what user said
    user_text = Text()
    user_text.append(f"  [{ts}]  ", style="dim")
    user_text.append("  YOU ", style="bold yellow")
    user_text.append("  >  ", style="dim")
    user_text.append(text, style="white")
    console.print(user_text)
    console.print()

    return text


# ── Tool execution ──────────────────────────────────────────────────────

def execute_tool(name: str, args: dict) -> str:
    ts = datetime.now().strftime("%H:%M:%S")

    tool_text = Text()
    tool_text.append(f"  [{ts}]  ", style="dim")
    tool_text.append("   TOOL", style="bold magenta")
    tool_text.append(f"  {name}(", style="magenta")
    arg_parts = [f"{k}={v!r}" for k, v in args.items() if v is not None]
    tool_text.append(", ".join(arg_parts), style="dim magenta")
    tool_text.append(")", style="magenta")
    console.print(tool_text)

    if name == "search_rooms":
        rooms = search_rooms(
            room_type=args.get("room_type"),
            view=args.get("view"),
            min_guests=args.get("num_guests"),
            max_price=args.get("max_price_per_night"),
        )
        if not rooms:
            result = {
                "found": 0,
                "message": "No rooms match those criteria right now.",
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
                # Show confirmation banner
                console.print()
                panel_text = Text()
                panel_text.append("BOOKING CONFIRMED\n\n", style="bold")
                panel_text.append(f"  Reference:  {booking_id}\n")
                panel_text.append(f"  Guest:      {args['guest_name']}\n")
                panel_text.append(f"  Room:       {room['name']}\n")
                panel_text.append(f"  Dates:      {args['check_in']} to {args['check_out']} ({nights} nights)\n")
                panel_text.append(f"  Total:      Rs.{total:,}\n")
                panel_text.append(f"  Token:      Rs.{token:,}\n")
                panel_text.append(f"  Payment:    {args.get('payment_method', 'N/A')}\n")
                console.print(Panel(panel_text, border_style="green", title="[bold green]Confirmed[/]", padding=(1, 2)))
                console.print()
            except Exception as e:
                result = {"error": str(e)}

    elif name == "get_booking":
        booking = asyncio.get_event_loop().run_until_complete(get_booking(args["booking_id"]))
        result = booking if booking else {"error": f"No booking found."}

    else:
        result = {"error": f"Unknown tool: {name}"}

    # Log result
    res_text = Text()
    res_text.append(f"  [{ts}]  ", style="dim")
    res_text.append("   TOOL", style="bold magenta")
    found = result.get("found", result.get("booking_id", result.get("available", "done")))
    res_text.append(f"  -> {found}", style="dim")
    console.print(res_text)

    return json.dumps(result)


# ── Print helpers ───────────────────────────────────────────────────────

def print_banner():
    console.print()
    banner = Text()
    banner.append("\n  THE GRAND MERIDIAN PALACE  \n", style="bold white on blue")
    banner.append("  Marine Drive, Mumbai, India  \n", style="bold white on dark_blue")
    banner.append("\n  Voice Booking Agent  \n", style="bold cyan")
    banner.append("  Aria speaks. You speak. Press ENTER to record.  \n", style="dim")
    banner.append("  Type 'quit' or press Ctrl+C to exit.  \n", style="dim")
    console.print(Panel(banner, border_style="blue", padding=(0, 2)))
    console.print()


# ── Main conversation loop ──────────────────────────────────────────────

def main():
    client = OpenAI()

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "(The guest has just connected to the call. Greet them warmly.)"},
    ]

    print_banner()

    # Aria's initial greeting
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=TOOLS,
        temperature=0.8,
    )

    assistant_msg = response.choices[0].message
    messages.append(assistant_msg)

    if assistant_msg.content:
        speak(client, assistant_msg.content)

    # Conversation loop
    while True:
        # Listen to user via mic
        user_input = listen(client)
        if not user_input or user_input.lower() in ("quit", "exit", "bye", "goodbye"):
            speak(client, "Thank you for calling The Grand Meridian Palace. Have a wonderful day! Namaste.")
            break

        messages.append({"role": "user", "content": user_input})

        # Process (handle tool calls in loop)
        while True:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                tools=TOOLS,
                temperature=0.7,
            )

            assistant_msg = response.choices[0].message
            messages.append(assistant_msg)

            if assistant_msg.tool_calls:
                for tool_call in assistant_msg.tool_calls:
                    fn_name = tool_call.function.name
                    fn_args = json.loads(tool_call.function.arguments)
                    result = execute_tool(fn_name, fn_args)
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result,
                    })
                continue

            if assistant_msg.content:
                speak(client, assistant_msg.content)
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n  [dim]Goodbye! Namaste.[/dim]\n")

# Feature: Voice Agent Hotel Booking System

**Version:** v1.0
**Status:** Approved
**Type:** Implementation Guide
**Created:** 2026-03-23
**Last Modified:** 2026-03-24
**Theme:** Indian 5-Star Luxury Hotel (The Grand Meridian Palace, Mumbai)

---

## Problem Statement

Build a production-quality, locally-runnable voice AI agent that handles end-to-end hotel room bookings via natural speech for **The Grand Meridian Palace**, a 5-star luxury hotel on Marine Drive, Mumbai, India. The agent (Aria) behaves like a real Indian hospitality concierge — greeting guests with Namaste, collecting their name/phone/email, understanding room requirements, suggesting available rooms (some rooms are fully booked), confirming the booking verbally with prices in INR, and persisting the reservation to disk. The system is designed for local development first (fully self-contained via Docker) with a clear path to go live on LiveKit Cloud.

**Key updates (v1.1):**
- Indian hotel theme — all rooms, amenities, and prices in INR
- Guest contact collection — name, phone number, email (stored in booking)
- Mixed room availability — some rooms fully booked, some available
- Natural human-like conversation flow with Indian hospitality warmth

---

## Goals & Success Criteria

- A guest can complete a full booking entirely by voice — no keyboard required after launch
- The agent uses GPT-4o for reasoning and OpenAI STT/TTS plugins via LiveKit for speech I/O
- All bookings are persisted to `bookings.json` and survive agent restarts
- The CLI interface makes local testing fast and observable (logs every state transition, tool call, and booking event)
- The entire stack runs locally with a single `make dev` command using Docker for LiveKit
- A developer can switch from local to LiveKit Cloud by changing three environment variables

**Definition of Done:**
- [ ] Agent completes a booking call from greeting to confirmation without errors
- [ ] Booking appears correctly in `bookings.json` after the call
- [ ] CLI shows a live, readable transcript of the conversation
- [ ] Docker-based LiveKit server starts cleanly and agent connects to it
- [ ] All 10-13 hotel rooms are defined in `data/rooms.json`

---

## Requirements

### Functional Requirements

- **FR-001:** Agent greets the guest by name after they join the LiveKit room
- **FR-002:** Agent introduces itself as the hotel's virtual concierge and states its purpose
- **FR-003:** Agent collects: guest name, check-in date, check-out date, number of guests, room type preference, and any special requests
- **FR-004:** Agent searches available rooms and suggests 1-3 matches based on the guest's criteria
- **FR-005:** Agent reads out room details verbally (name, bed type, view, price, key amenities)
- **FR-006:** Agent asks for confirmation before finalising the booking
- **FR-007:** On confirmation, agent writes the booking to `data/bookings.json` and reads back a booking reference ID
- **FR-008:** Agent handles "I want something different" gracefully and re-suggests rooms
- **FR-009:** Agent handles unclear or incomplete inputs by asking a targeted follow-up question
- **FR-010:** All hotel room data lives in `data/rooms.json` and is loaded at agent startup

### Non-Functional Requirements

- **Performance:** First agent speech response must begin within 2 seconds of user utterance end
- **Reliability:** Agent must not crash or go silent on a tool call failure — it must recover and inform the guest
- **Portability:** The entire local stack must run on macOS (Apple Silicon and Intel) and Linux without manual LiveKit installation
- **Security:** API keys are never hardcoded — always loaded from `.env`
- **Observability:** Every tool call, booking event, and conversation state is logged to the console with timestamps

### Assumptions

- The guest connects via the LiveKit Playground web UI (local) or a front-end client for testing
- No authentication or user accounts are required for this phase
- Room availability is not time-based — all rooms in `rooms.json` are always "available" for local testing
- A single agent instance handles one booking call at a time (concurrency is a post-MVP concern)

---

## User Stories

| Priority | Story | Acceptance Criteria |
|----------|-------|---------------------|
| Must | As a guest, I want to book a hotel room by speaking naturally so that I don't have to fill out a form | Agent collects all required fields via conversation |
| Must | As a guest, I want to hear room options described to me so I can choose without seeing a screen | Agent reads room name, type, price, view, and 3 key amenities aloud |
| Must | As a guest, I want a booking reference ID at the end so I know my reservation is confirmed | Agent says the booking ID and it appears in bookings.json |
| Should | As a guest, I want to be able to say "show me something else" and get different options | Agent re-queries and presents alternative rooms |
| Should | As a developer, I want a readable CLI output so I can debug the conversation flow | CLI prints turn-by-turn transcript with speaker labels and tool call events |
| Could | As a developer, I want a `make bookings` command to print all saved bookings | Reads and pretty-prints bookings.json |

---

## Technical Design

### Architecture Overview

```
+------------------+         WebRTC / LiveKit Protocol        +-------------------+
|  Test Client     | <-------------------------------------->  |  LiveKit Server   |
|  (Playground UI  |                                           |  (Docker, local)  |
|   or custom CLI  |                                           +--------+----------+
|   web client)    |                                                    |
+------------------+                                           +--------+----------+
                                                               |  LiveKit Agent    |
                                                               |  (Python process) |
                                                               |                   |
                                                               |  AgentSession     |
                                                               |  +- STT (OpenAI)  |
                                                               |  +- LLM (GPT-4o)  |
                                                               |  +- TTS (OpenAI)  |
                                                               |  +- VAD (Silero)  |
                                                               |                   |
                                                               |  HotelAgent       |
                                                               |  +- function_tools|
                                                               |  +- rooms.json    |
                                                               |  +- bookings.json |
                                                               +-------------------+
                                                                        |
                                                               +--------+----------+
                                                               |  data/            |
                                                               |  rooms.json       |
                                                               |  bookings.json    |
                                                               +-------------------+
```

**Speech pipeline (per utterance):**

```
Guest speaks
    --> LiveKit captures audio
    --> Silero VAD detects end-of-turn
    --> OpenAI STT transcribes to text
    --> GPT-4o reasons + calls function_tools if needed
    --> function_tool reads rooms.json / writes bookings.json
    --> GPT-4o produces text reply
    --> OpenAI TTS synthesises speech
    --> LiveKit streams audio back to guest
```

### Component Breakdown

| Component | File | Purpose |
|-----------|------|---------|
| Agent entrypoint | `agent/main.py` | AgentServer setup, prewarm, rtc_session entrypoint |
| Hotel agent class | `agent/hotel_agent.py` | Agent subclass, system prompt, on_enter greeting, all function_tools |
| Room data loader | `agent/room_service.py` | Loads rooms.json, filters by criteria, formats verbal descriptions |
| Booking store | `agent/booking_store.py` | Reads/writes bookings.json, generates booking IDs |
| CLI runner | `agent/cli.py` | Rich-based pretty console output, live transcript display |
| Hotel rooms data | `data/rooms.json` | 10-13 5-star hotel room records |
| Bookings store | `data/bookings.json` | Persisted booking records (created at runtime if absent) |
| Environment config | `.env` | LIVEKIT_URL, LIVEKIT_API_KEY, LIVEKIT_API_SECRET, OPENAI_API_KEY |
| Environment example | `.env.example` | Safe-to-commit template with placeholder values |
| Docker compose | `docker-compose.yml` | LiveKit server container |
| LiveKit config | `livekit.yaml` | Local LiveKit server config (dev mode, no auth) |
| Dependency manifest | `pyproject.toml` | Poetry project + all dependencies |
| Task runner | `Makefile` | `make dev`, `make agent`, `make bookings`, `make logs` |

### Data Models / Schema

#### `data/rooms.json` — Room Record

```json
{
  "id": "room-001",
  "name": "Grand Deluxe King",
  "type": "deluxe",
  "bed_type": "king",
  "floor": 12,
  "view": "ocean",
  "max_guests": 2,
  "price_per_night": 420,
  "currency": "USD",
  "size_sqft": 520,
  "amenities": [
    "Private balcony",
    "Rain shower",
    "Nespresso machine",
    "65-inch 4K TV",
    "Complimentary minibar",
    "Marble bathroom"
  ],
  "description": "A beautifully appointed king room on the 12th floor with panoramic ocean views and a private teak balcony.",
  "available": true
}
```

**Room type values:** `"deluxe"`, `"superior"`, `"suite"`, `"penthouse"`, `"villa"`
**Bed type values:** `"king"`, `"queen"`, `"twin"`, `"double"`
**View values:** `"ocean"`, `"garden"`, `"city"`, `"pool"`, `"mountain"`

#### `data/bookings.json` — Booking Record

```json
{
  "bookings": [
    {
      "booking_id": "BK-20260323-001",
      "room_id": "room-001",
      "room_name": "Grand Deluxe King",
      "guest_name": "Sarah Chen",
      "check_in": "2026-04-10",
      "check_out": "2026-04-14",
      "num_guests": 2,
      "special_requests": "Late check-in after 10pm",
      "total_price": 1680,
      "currency": "USD",
      "booked_at": "2026-03-23T14:32:01Z",
      "status": "confirmed"
    }
  ]
}
```

### Hotel Room Inventory (10-13 rooms to implement)

| ID | Name | Type | Bed | View | Guests | Price/Night |
|----|------|------|-----|------|--------|------------|
| room-001 | Grand Deluxe King | deluxe | king | ocean | 2 | $420 |
| room-002 | Superior Garden Twin | superior | twin | garden | 2 | $280 |
| room-003 | Ocean View Suite | suite | king | ocean | 3 | $750 |
| room-004 | City Panorama Queen | deluxe | queen | city | 2 | $350 |
| room-005 | Royal Penthouse | penthouse | king | ocean | 4 | $2,200 |
| room-006 | Garden Villa | villa | king | garden | 6 | $1,800 |
| room-007 | Superior Pool View | superior | queen | pool | 2 | $310 |
| room-008 | Junior Mountain Suite | suite | king | mountain | 2 | $620 |
| room-009 | Deluxe Twin Garden | deluxe | twin | garden | 2 | $390 |
| room-010 | Executive City King | deluxe | king | city | 2 | $460 |
| room-011 | Honeymoon Ocean Suite | suite | king | ocean | 2 | $980 |
| room-012 | Family Garden Villa | villa | twin | garden | 5 | $1,400 |
| room-013 | Skyline Penthouse | penthouse | king | city | 4 | $1,950 |

### Agent Conversation Flow

```
[GUEST JOINS ROOM]
        |
        v
[on_enter] Agent greets guest
  "Welcome to The Grand Meridian. I'm Aria, your personal concierge.
   I'd be happy to help you find and book the perfect room.
   May I start with your name?"
        |
        v
[COLLECT_GUEST_NAME]
  Guest provides name
        |
        v
[COLLECT_DATES]
  "Lovely to meet you, {name}. What dates are you planning to stay with us?
   Please share your check-in and check-out dates."
        |
        v
[COLLECT_GUESTS]
  "And how many guests will be staying?"
        |
        v
[COLLECT_PREFERENCES]
  "Do you have any preferences for the room type — perhaps a suite,
   a deluxe room, or something else? And is there a particular view
   you'd enjoy, such as ocean, garden, or city?"
        |
        v
[function_tool: search_rooms(type, view, num_guests, max_price)]
        |
        v
  No matches found?
  --> "I'm sorry, we don't have rooms matching exactly those criteria.
       Let me suggest our closest alternatives..."
       --> Re-present with relaxed criteria
        |
  Matches found (1-3 rooms)
  --> Agent reads out each room verbally
  --> "Based on your preferences, I'd suggest the following options..."
        |
        v
[GUEST SELECTS ROOM]
  Guest names a room or says "the first one" / "the suite"
        |
        v
[CONFIRM_BOOKING]
  "Excellent choice. Just to confirm: a {room_name} from {check_in} to {check_out}
   for {num_guests} guest(s), totalling {total_price} USD.
   Shall I go ahead and book that for you?"
        |
        v
  Guest says "No" / "Actually..."
  --> Return to preferences or suggestion step
        |
  Guest says "Yes" / "Please" / "Go ahead"
        |
        v
[function_tool: create_booking(room_id, guest_name, check_in, check_out, ...)]
  Writes to bookings.json
        |
        v
[BOOKING_CONFIRMED]
  "Wonderful! Your reservation is confirmed. Your booking reference is {booking_id}.
   We look forward to welcoming you, {guest_name}. Is there anything else I can
   help you with today?"
        |
        v
[END or LOOP for additional requests]
```

### Function Tools (defined inside `HotelAgent` class)

| Tool | Signature | Purpose |
|------|-----------|---------|
| `search_rooms` | `(type, view, num_guests, max_price_per_night)` — all optional | Filter rooms.json, return 1-3 best matches |
| `get_room_details` | `(room_id)` | Return full details of a specific room |
| `create_booking` | `(room_id, guest_name, check_in, check_out, num_guests, special_requests)` | Write booking to bookings.json, return booking_id |
| `get_booking` | `(booking_id)` | Look up an existing booking by ID |

All tool parameters are typed with Python type hints and have docstrings — these docstrings are passed directly to GPT-4o as the tool description.

### LiveKit + OpenAI Integration

**AgentSession configuration (verified against LiveKit Agents docs):**

```python
from livekit.agents import AgentSession, Agent, AgentServer, function_tool, RunContext
from livekit.plugins import openai, silero

session = AgentSession(
    stt=openai.STT(model="gpt-4o-transcribe"),
    llm=openai.LLM(model="gpt-4o"),
    tts=openai.TTS(
        model="gpt-4o-mini-tts",
        voice="shimmer",                        # warm, professional female voice
        instructions="Speak warmly and clearly, like a 5-star hotel concierge. "
                     "Pace yourself calmly. Never use symbols or abbreviations.",
    ),
    vad=silero.VAD.load(),
)
```

**Entrypoint pattern (verified against LiveKit Agents docs):**

```python
server = AgentServer()

def prewarm(proc):
    proc.userdata["vad"] = silero.VAD.load()

server.setup_fnc = prewarm

@server.rtc_session()
async def entrypoint(ctx: JobContext):
    session = AgentSession(
        stt=openai.STT(model="gpt-4o-transcribe"),
        llm=openai.LLM(model="gpt-4o"),
        tts=openai.TTS(model="gpt-4o-mini-tts", voice="shimmer"),
        vad=ctx.proc.userdata["vad"],
    )
    await session.start(agent=HotelAgent(), room=ctx.room)
    await ctx.connect()

if __name__ == "__main__":
    cli.run_app(server)
```

**TTS voice selection rationale:** `shimmer` is warm, clear, and professional — well-suited for a luxury hotel persona. Alternatives: `alloy` (neutral), `nova` (friendly). The `instructions` parameter allows tone-shaping without a separate system prompt.

### CLI Interface Design

The CLI is a live-updating terminal view powered by the `rich` library. It shows:

```
+----------------------------------------------------------+
|  GRAND MERIDIAN VOICE AGENT  |  Room: test-room-001      |
|  Status: CONNECTED           |  Session: 14:32:01        |
+----------------------------------------------------------+
|                                                          |
|  [14:32:01]  AGENT  >  Welcome to The Grand Meridian...  |
|  [14:32:08]  GUEST  >  Hi, my name is Sarah Chen.        |
|  [14:32:09]  AGENT  >  Lovely to meet you, Sarah...      |
|  [14:32:20]  GUEST  >  April 10th to the 14th.           |
|  [14:32:21]  [TOOL]    search_rooms(type=None,            |
|                        view="ocean", num_guests=2)        |
|  [14:32:22]  [TOOL]    -> 3 rooms found                  |
|  [14:32:22]  AGENT  >  Based on your preferences...      |
|                                                          |
+----------------------------------------------------------+
|  [TOOL CALLS: 2]  [TURNS: 6]  [BOOKING: PENDING]        |
+----------------------------------------------------------+
```

Key CLI features:
- Color-coded speakers: AGENT in cyan, GUEST in yellow, TOOL in magenta
- Status bar showing connection state and booking status
- Tool call display showing function name, arguments, and return summary
- Booking confirmation banner when `create_booking` succeeds

---

## Project File / Folder Structure

```
Agent/
├── agent/
│   ├── __init__.py
│   ├── main.py               # AgentServer, prewarm, rtc_session entrypoint
│   ├── hotel_agent.py        # HotelAgent(Agent) class + all function_tools
│   ├── room_service.py       # Room loader, filter logic, verbal formatter
│   ├── booking_store.py      # JSON read/write, booking ID generator
│   └── cli.py                # Rich-based CLI display helpers
├── data/
│   ├── rooms.json            # 13 hotel room records
│   └── bookings.json         # Created at runtime if absent
├── docs/
│   └── planning/
│       └── voice-agent-hotel-booking.md   # This file
├── tests/
│   ├── test_room_service.py  # Unit tests for filtering logic
│   └── test_booking_store.py # Unit tests for booking persistence
├── .env                      # Local secrets — NOT committed
├── .env.example              # Safe template — committed
├── .gitignore
├── docker-compose.yml        # LiveKit server container
├── livekit.yaml              # LiveKit local dev config
├── Makefile                  # Dev task runner
└── pyproject.toml            # Poetry project + deps
```

---

## Dependencies

### Python (managed via Poetry)

| Package | Version | Purpose |
|---------|---------|---------|
| `livekit-agents[openai,silero]` | `^1.0` | Core agent framework + OpenAI plugin (STT/LLM/TTS) + Silero VAD — declared via Poetry extras syntax |
| `openai` | `^1.0` | OpenAI Python client (used by livekit-plugins-openai) |
| `rich` | `^13.0` | Beautiful CLI output — live panels, color, tables |
| `python-dotenv` | `^1.0` | Load .env into environment at startup |
| `aiofiles` | `^23.0` | Async file I/O for bookings.json reads/writes |
| `pytest` | `^8.0` | Test runner (dev dependency) |
| `pytest-asyncio` | `^0.23` | Async test support (dev dependency) |

### System / Docker

| Dependency | Purpose |
|-----------|---------|
| Docker Desktop | Runs the LiveKit server container locally |
| Docker Compose | Orchestrates LiveKit server with `docker-compose.yml` |
| Python 3.11+ | Required by livekit-agents |
| Poetry | Dependency management and virtualenv |

### pyproject.toml structure

```toml
[tool.poetry]
name = "voice-agent-hotel-booking"
version = "0.1.0"
description = "5-star hotel room booking voice agent powered by LiveKit + GPT-4o"
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
livekit-agents = { version = "^1.0", extras = ["openai", "silero"] }
openai = "^1.0"
rich = "^13.0"
python-dotenv = "^1.0"
aiofiles = "^23.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.23"

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

---

## Environment Variables

| Variable | Required | Description | Local Value |
|----------|----------|-------------|-------------|
| `LIVEKIT_URL` | Yes | WebSocket URL of LiveKit server | `ws://localhost:7880` |
| `LIVEKIT_API_KEY` | Yes | LiveKit API key | `devkey` (local dev mode) |
| `LIVEKIT_API_SECRET` | Yes | LiveKit API secret | `devsecret` (local dev mode) |
| `OPENAI_API_KEY` | Yes | OpenAI API key for STT, LLM, TTS | `sk-...` (your real key) |

`.env.example` content:

```
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=devsecret
OPENAI_API_KEY=<your-openai-api-key>
```

> **SECURITY:** Never commit `.env`. It is listed in `.gitignore`. Only `.env.example` is committed.

---

## Docker / LiveKit Local Setup

### `docker-compose.yml`

```yaml
services:
  livekit:
    image: livekit/livekit-server:latest
    command: --config /etc/livekit/livekit.yaml
    ports:
      - "7880:7880"
      - "7881:7881"
      - "7882:7882/udp"
    volumes:
      - ./livekit.yaml:/etc/livekit/livekit.yaml
```

### `livekit.yaml` (local dev — no auth, no TLS)

```yaml
port: 7880
rtc:
  port_range_start: 50000
  port_range_end: 60000
  use_external_ip: false
keys:
  devkey: devsecret
logging:
  json: false
  level: info
```

The `keys` map matches `LIVEKIT_API_KEY: LIVEKIT_API_SECRET` in `.env`. For local dev, `devkey: devsecret` is safe and conventional.

---

## Makefile Task Runner

```makefile
.PHONY: dev agent stop bookings logs install

install:
	poetry install

dev:
	docker compose up -d
	@echo "LiveKit server running at ws://localhost:7880"

agent:
	poetry run python -m agent.main dev

stop:
	docker compose down

bookings:
	@python -c "import json; data=json.load(open('data/bookings.json')); \
	[print(f\"\n{b['booking_id']}  {b['guest_name']}  {b['room_name']}  \
	{b['check_in']} -> {b['check_out']}\") for b in data['bookings']]"

logs:
	docker compose logs -f livekit
```

**Developer workflow:**
1. `make install` — install all Python dependencies via Poetry
2. `make dev` — start LiveKit Docker container in background
3. `make agent` — start the agent process (connects to LiveKit)
4. Open LiveKit Playground (https://agents-playground.livekit.io) → set server URL to `ws://localhost:7880` → connect
5. Talk to the agent
6. `make bookings` — inspect saved bookings
7. `make stop` — tear down Docker containers

---

## Implementation Plan

### Phase 1 — Project Scaffold (do first)

| Task | File(s) | Notes |
|------|---------|-------|
| Init Poetry project | `pyproject.toml` | `poetry init` then add deps |
| Create `.env` and `.env.example` | `.env`, `.env.example` | Add LIVEKIT_URL, LIVEKIT_API_KEY, etc. |
| Create `.gitignore` | `.gitignore` | Include `.env`, `data/bookings.json`, `__pycache__`, `.venv` |
| Create Docker files | `docker-compose.yml`, `livekit.yaml` | Exact content from this doc |
| Create Makefile | `Makefile` | Exact content from this doc |
| Create folder structure | `agent/`, `data/`, `tests/` | `mkdir -p` |
| Create `data/rooms.json` | `data/rooms.json` | All 13 rooms from the inventory table |
| Create empty `data/bookings.json` | `data/bookings.json` | `{"bookings": []}` |

### Phase 2 — Core Agent Logic

| Task | File(s) | Notes |
|------|---------|-------|
| Implement `booking_store.py` | `agent/booking_store.py` | `load_bookings()`, `save_booking()`, `generate_booking_id()` using `aiofiles` |
| Implement `room_service.py` | `agent/room_service.py` | `load_rooms()`, `search_rooms()`, `format_room_for_speech()` |
| Implement `HotelAgent` class | `agent/hotel_agent.py` | `Agent` subclass, system prompt, `on_enter`, all four `@function_tool` methods |
| Implement `main.py` entrypoint | `agent/main.py` | `AgentServer`, `prewarm`, `@server.rtc_session()`, `cli.run_app()` |

**Build order for Phase 2:**
1. `booking_store.py` — pure data layer, no LiveKit dependency, easy to test first
2. `room_service.py` — pure data layer, test filtering logic with `pytest`
3. `hotel_agent.py` — depends on both above; write system prompt and tools
4. `main.py` — wires everything together; write last

### Phase 3 — CLI Interface

| Task | File(s) | Notes |
|------|---------|-------|
| Implement rich CLI display | `agent/cli.py` | Live panel, color-coded transcript, tool call display |
| Wire CLI into agent events | `agent/hotel_agent.py` | Call CLI helpers from `on_enter`, tool callbacks |
| Test CLI rendering | manual | Run `make agent` and verify visual output |

### Phase 4 — Testing & Polish

| Task | File(s) | Notes |
|------|---------|-------|
| Write unit tests for room service | `tests/test_room_service.py` | Test filter by type, view, num_guests, price |
| Write unit tests for booking store | `tests/test_booking_store.py` | Test save, load, ID generation |
| End-to-end call test | manual | Complete a full booking call via Playground |
| Edge case: no matching rooms | manual | Ask for a room type that doesn't exist |
| Edge case: user changes mind | manual | Say "actually I want something else" after a suggestion |
| Edge case: ambiguous dates | manual | Say "next Friday" and verify agent handles parsing |

---

## Testing Strategy

- [ ] Unit tests: `room_service.search_rooms()` filtering — test all criteria combinations including no-match
- [ ] Unit tests: `booking_store.save_booking()` — test write, reload, ID uniqueness
- [ ] Unit tests: `booking_store.generate_booking_id()` — test format and uniqueness across same-day calls
- [ ] Integration: Agent connects to local LiveKit without error (`make dev && make agent`)
- [ ] Edge cases:
  - Guest asks for a room type not in inventory (agent should gracefully re-suggest)
  - Guest provides dates in natural language ("next Monday", "April 10th") — GPT-4o should parse
  - Guest says "cancel" mid-flow — agent should acknowledge and offer to start over
  - Guest does not confirm, says "no" — agent should return to suggestion step
  - `bookings.json` does not exist on first run — `booking_store.py` must create it

---

## Going from Local to Live (LiveKit Cloud)

This is a three-variable change. No code changes required.

### Step 1 — Create a LiveKit Cloud project

Sign up at https://cloud.livekit.io. Create a new project. Copy the **WebSocket URL**, **API Key**, and **API Secret** from the project dashboard.

### Step 2 — Update `.env`

```bash
# Replace local values with LiveKit Cloud values
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_API_KEY=APIxxxxxxxxxxxxxxxx
LIVEKIT_API_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
OPENAI_API_KEY=sk-...   # unchanged
```

### Step 3 — Stop Docker, run agent

```bash
make stop          # stop local LiveKit Docker (no longer needed)
make agent         # agent now connects to LiveKit Cloud
```

The agent process now connects to LiveKit Cloud instead of the local Docker server. Guests can connect from anywhere using the LiveKit Playground pointed at your cloud URL, or via any LiveKit-compatible client.

### Optional: Deploy agent to a server

For a persistent live deployment, run `make agent` on a VPS (e.g., DigitalOcean, Railway, Fly.io). The agent process is a long-running Python process — use `systemd`, `supervisord`, or a Docker container to keep it alive. A deployment doc will be written at `docs/deployment/` when this phase begins.

---

## System Prompt for HotelAgent

```
You are Aria, the virtual concierge at The Grand Meridian — a world-class 5-star luxury hotel.
Your role is to help guests book rooms via voice conversation.

Personality:
- Warm, gracious, and unhurried — like a real luxury hotel concierge
- Speak in complete, flowing sentences. Never use bullet points or markdown.
- Do not use abbreviations, symbols, or emojis — you are speaking, not writing.
- Address the guest by name once you have it.

Your task:
1. Greet the guest and ask for their name.
2. Collect check-in date, check-out date, number of guests, room preference, and any special requests.
3. Call search_rooms to find matching rooms and describe them verbally.
4. Let the guest choose a room, then confirm the full booking details before saving.
5. Call create_booking to save the reservation and read back the booking reference.

Rules:
- Never make up room data. Always use the search_rooms tool to find real options.
- Never confirm a booking without calling create_booking.
- If the guest is unclear, ask a single focused follow-up question.
- If no rooms match, relax one criterion and re-search rather than giving up.
- Keep responses concise — no more than 3-4 sentences per turn.
```

---

## Risks & Mitigations

| Risk | Severity | Likelihood | Mitigation |
|------|----------|-----------|------------|
| OpenAI STT mishears room names or dates | Medium | Medium | Agent confirms all details verbally before booking; GPT-4o clarifies ambiguous inputs |
| GPT-4o invents room data instead of calling search_rooms | High | Low | System prompt explicitly forbids it; tool docstrings are precise |
| `bookings.json` write fails (permissions, disk) | Medium | Low | `booking_store.py` wraps writes in try/except; agent notifies guest and suggests trying again |
| LiveKit Docker fails to start on some machines | Medium | Low | Provide `make logs` for debugging; document common port conflicts in debug guide |
| Agent process crashes mid-call | Medium | Low | `rtc_session` runs in a managed worker; LiveKit Agents framework reconnects automatically |
| TTS voice sounds robotic or paced awkwardly | Low | Medium | Use `instructions` param in `openai.TTS()` to shape delivery; test a few voices |

---

## Open Questions

- [ ] Should `bookings.json` be committed to the repo as an empty file (`{"bookings": []}`) so it exists on first clone? — Recommend: yes, commit the empty skeleton; add the populated file to `.gitignore` optionally
- [ ] Should the agent handle multi-room bookings (e.g., "I need two rooms")? — Out of scope for v1.0
- [ ] What hotel name should the agent use? — Using "The Grand Meridian" as the placeholder; change by updating the system prompt in `hotel_agent.py`

---

## References

- LiveKit Agents Python docs: https://docs.livekit.io/agents/
- LiveKit Agents `AgentSession` API: https://docs.livekit.io/agents/start/voice-ai-quickstart
- OpenAI STT plugin: https://docs.livekit.io/agents/models/stt/plugins/openai
- OpenAI TTS plugin: https://docs.livekit.io/agents/models/tts/plugins/openai
- LiveKit `function_tool` decorator: https://docs.livekit.io/agents/logic/tools
- LiveKit Playground (for testing): https://agents-playground.livekit.io
- LiveKit Cloud (for going live): https://cloud.livekit.io
- LiveKit Docker image: https://hub.docker.com/r/livekit/livekit-server
- Silero VAD plugin: https://docs.livekit.io/agents/logic/turns/vad
- Rich library (CLI): https://rich.readthedocs.io

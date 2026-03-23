# Voice Booking Agent

A real-time voice AI agent platform for booking services. Built with OpenAI (LLM + TTS + STT), designed for natural two-way phone-like conversations.

Currently live: **Hotel Room Booking** (The Grand Meridian Palace, Mumbai)

Upcoming categories: Food Order, Table Booking, Turf/Pickleball, E-commerce, and more.

## How It Works

1. You run the agent
2. Agent greets you — speaks through your speakers
3. You talk naturally through your mic — no buttons, no typing
4. Agent listens, thinks, responds — like a real phone call
5. You can interrupt anytime — agent stops and listens
6. Booking gets saved to JSON with a reference ID

## Quick Start

```bash
poetry install
cp .env.example .env       # Add your OPENAI_API_KEY
poetry run python run.py   # Start talking
```

## Project Structure

```
Agent/
├── core/                           # Voice engine (shared across all categories)
│   └── config.py                  # Models, voice, audio, STT/TTS/LLM settings
│
├── categories/                     # Booking categories (plug-and-play)
│   └── hotel/                     # Hotel room booking (active)
│       ├── config.py              # Hotel-specific: name, prompt, agent persona
│       ├── tools/
│       │   ├── definitions.py     # OpenAI function tool schemas
│       │   └── executor.py        # Tool execution logic
│       └── data/
│           └── rooms.json         # Room inventory
│
├── agent/                          # Agent module (generic services)
│   ├── config.py                  # Combines core + active category config
│   ├── hotel_agent.py             # LiveKit agent class
│   ├── main.py                    # LiveKit entrypoint
│   ├── room_service.py            # Room data layer
│   ├── booking_store.py           # Booking persistence (async JSON)
│   └── cli.py                     # Console logging
│
├── tools/                          # Shared tool definitions (legacy, being migrated)
├── tests/                          # 30 tests — all passing
├── data/                           # Runtime data (bookings.json)
│
├── run.py                         # Main entry point — standalone voice agent
├── pyproject.toml
├── Makefile
└── .env.example
```

## Adding a New Category

To add a new booking category (e.g., food ordering):

```
categories/
└── food/
    ├── config.py              # Agent name, system prompt, business info
    ├── tools/
    │   ├── definitions.py     # Tool schemas (search_menu, place_order, etc.)
    │   └── executor.py        # Tool execution
    └── data/
        └── menu.json          # Menu items
```

Then switch the active category in `agent/config.py`:

```python
# Change this line:
from categories.hotel.config import ...
# To:
from categories.food.config import ...
```

## Configuration

All voice engine settings in `core/config.py`:

```python
LLM_MODEL = "gpt-4o-mini"          # Reasoning
TTS_MODEL = "gpt-4o-mini-tts"      # Speech output
TTS_VOICE = "nova"                  # Voice style
STT_MODEL = "whisper-1"             # Speech input
ENERGY_THRESHOLD = 500              # Mic sensitivity
TOKEN_PERCENTAGE = 20               # Booking advance payment
```

Category-specific settings (prompt, business name, persona) live in `categories/<name>/config.py`.

## Commands

```bash
poetry run python run.py       # Run voice agent
poetry run pytest tests/ -v    # Run tests (30 tests)
make install                   # Install dependencies
make bookings                  # View saved bookings
```

## Cost

~$0.05 per full booking conversation.

## Tech

- OpenAI GPT-4o-mini (LLM) + gpt-4o-mini-tts (TTS) + Whisper (STT)
- Python, Poetry, Rich, sounddevice, soundfile
- Energy-based VAD for real-time speech detection
- Async JSON persistence for bookings

# The Grand Meridian Palace — Voice Booking Agent

A real-time voice AI agent for hotel room booking. Talk to **Aria**, the virtual concierge at a 5-star luxury hotel in Mumbai, India. She speaks, you speak — like a real phone call.

## Features

- **Real-time two-way voice** — always-on mic, auto-detects speech, no buttons
- **Interrupt anytime** — speak while Aria is talking and she stops
- **Natural conversation** — warm Indian hospitality, not robotic
- **5 booking tools** — search rooms, check availability, create booking, get details
- **13 hotel rooms** — mixed availability, INR pricing, 5 room types, 5 views
- **Token payment flow** — 20% advance with UPI / card / bank transfer
- **Live waveform** — visual audio bars in the terminal
- **Beautiful CLI** — Rich-powered panels, color-coded speakers

## Tech Stack

| Component | Technology |
|-----------|-----------|
| LLM | OpenAI GPT-4o-mini |
| TTS | OpenAI gpt-4o-mini-tts (Nova voice) |
| STT | OpenAI Whisper |
| Audio | sounddevice + soundfile |
| CLI | Rich |
| Data | JSON (rooms + bookings) |
| Package Manager | Poetry |

## Quick Start

```bash
# 1. Install dependencies
poetry install

# 2. Set up your OpenAI API key
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Run the voice agent
poetry run python run.py
```

That's it. Aria greets you, you talk back. No Docker, no browser needed.

## Project Structure

```
Agent/
├── agent/                      # Core agent module
│   ├── config.py              # All settings: models, voice, prompts, constants
│   ├── hotel_agent.py         # HotelAgent class (LiveKit mode)
│   ├── main.py                # LiveKit entrypoint
│   ├── room_service.py        # Room data: load, search, filter, format
│   ├── booking_store.py       # Booking persistence (async JSON)
│   └── cli.py                 # Console logging helpers
├── tools/                      # Shared tool layer
│   ├── definitions.py         # OpenAI function tool schemas (5 tools)
│   └── executor.py            # Tool execution (routes to services)
├── tests/                      # 31 tests
│   ├── test_room_service.py   # Room search, filter, format tests
│   ├── test_booking_store.py  # Booking save, load, ID generation tests
│   └── test_tools.py          # Tool execution tests
├── data/
│   ├── rooms.json             # 13 rooms (9 available, 4 booked)
│   └── bookings.json          # Saved bookings (created at runtime)
├── run.py                     # Standalone voice agent (main entry point)
├── pyproject.toml
├── Makefile
└── .env.example
```

## Conversation Flow

```
Aria: "Namaste! How can I help you today?"
You:  "I want to book a room"
Aria: "We have Deluxe, Suites, Villas, Penthouses..."
You:  "Show me sea view rooms"
Aria: [calls search_rooms] "I found the Maharaja Deluxe King..."
You:  "I'll take it"
Aria: "May I have your name?" → phone → guests → dates
Aria: [confirms details] "Token of Rs.11,100. UPI, card, or bank transfer?"
You:  "UPI"
Aria: [books] "Confirmed! Reference BK-20260324-001. Namaste!"
```

## Room Types

| Type | Price Range (INR/night) | Available |
|------|------------------------|-----------|
| Superior | 12,500 - 13,500 | Some booked |
| Deluxe | 15,000 - 21,000 | Most available |
| Suite | 28,000 - 42,000 | Available |
| Penthouse | 85,000 - 95,000 | 1 booked, 1 available |
| Villa | 62,000 - 78,000 | Available |

## Configuration

All settings are in `agent/config.py`:

```python
LLM_MODEL = "gpt-4o-mini"          # Change LLM here
TTS_MODEL = "gpt-4o-mini-tts"      # TTS model
TTS_VOICE = "nova"                  # Voice: nova, shimmer, coral, etc.
STT_MODEL = "whisper-1"             # Speech-to-text
TOKEN_PERCENTAGE = 20               # Booking token amount
ENERGY_THRESHOLD = 500              # Mic sensitivity (lower = more sensitive)
```

## Commands

```bash
poetry run python run.py       # Run voice agent
poetry run pytest tests/ -v    # Run 31 tests
make install                   # Install dependencies
make bookings                  # View saved bookings
```

## Cost per Conversation

~$0.05 per full booking conversation (greeting to confirmation).

| Component | Model | Cost |
|-----------|-------|------|
| LLM | gpt-4o-mini | ~$0.003 |
| TTS | gpt-4o-mini-tts | ~$0.036 |
| STT | whisper-1 | ~$0.009 |

## License

Private project.

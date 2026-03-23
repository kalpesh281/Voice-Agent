"""
Core voice engine configuration — shared across ALL categories.
Change models, voice, audio settings here. Applies everywhere.
"""

# ── Voice / TTS ─────────────────────────────────────────────────────────

TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = "nova"
TTS_INSTRUCTIONS = (
    "Voice: warm, friendly Indian woman in her 30s. "
    "Tone: natural phone conversation, NOT reading text aloud. "
    "Pace: relaxed with natural pauses between thoughts. Slightly breathy warmth. "
    "Accent: soft Indian English. Pronounce Hindi words and Indian names naturally. "
    "Emotion: genuinely caring, smile in your voice."
)

# ── STT ─────────────────────────────────────────────────────────────────

STT_MODEL = "whisper-1"
STT_LANGUAGE = "en"

# ── LLM ─────────────────────────────────────────────────────────────────

LLM_MODEL = "gpt-4o-mini"
LLM_TEMPERATURE_GREETING = 0.8
LLM_TEMPERATURE_CONVERSATION = 0.7

# ── Audio ───────────────────────────────────────────────────────────────

SAMPLE_RATE = 24000
MIC_SAMPLE_RATE = 16000
ENERGY_THRESHOLD = 500
SILENCE_DURATION = 1.5
MIN_SPEECH_DURATION = 0.3

# ── Booking ─────────────────────────────────────────────────────────────

TOKEN_PERCENTAGE = 20
CURRENCY = "INR"

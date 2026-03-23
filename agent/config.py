"""
Agent config — combines core engine settings with active category config.
Change the category import below to switch between hotel, food, turf, etc.
"""

# Core voice engine settings (shared across all categories)
from core.config import (
    TTS_MODEL,
    TTS_VOICE,
    TTS_INSTRUCTIONS,
    STT_MODEL,
    STT_LANGUAGE,
    LLM_MODEL,
    LLM_TEMPERATURE_GREETING,
    LLM_TEMPERATURE_CONVERSATION,
    SAMPLE_RATE,
    MIC_SAMPLE_RATE,
    ENERGY_THRESHOLD,
    SILENCE_DURATION,
    MIN_SPEECH_DURATION,
    TOKEN_PERCENTAGE,
    CURRENCY,
)

# Active category — change this line to switch categories
from categories.hotel.config import (
    CATEGORY_NAME,
    BUSINESS_NAME,
    BUSINESS_LOCATION,
    AGENT_NAME,
    SYSTEM_PROMPT,
)

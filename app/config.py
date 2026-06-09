from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# Anchor .env to the project root so it loads no matter where the process is
# launched from (a relative "./.env" only works when CWD is the project root,
# which breaks under some launchers / reloader subprocesses).
_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Platform MongoDB (our data: client configs, bookings, checkpoints)
    mongodb_uri: str
    mongodb_database: str = "voice_agent"

    # Client's MongoDB (their data: rooms, tables, courts)
    # Loaded from ClientConfig.database at runtime per client
    # For testing: set these to point to a test DB with hotel data
    client_db_uri: str = ""
    client_db_name: str = ""

    # OpenRouter (LLM via LangChain)
    openrouter_api_key: str
    # Free, fast, reliable tool-calling model. The previous default
    # "openrouter/owl-alpha" is a stealth model — ~48s/turn and frequent 502s,
    # which cut the agent's reply off mid-sentence over LiveKit. gpt-oss-120b:free
    # averages ~3s/turn with consistent function calls. Override via LLM_MODEL in
    # .env if the account gains credits (e.g. openai/gpt-4o-mini).
    llm_model: str = "openai/gpt-oss-120b:free"
    llm_temperature: float = 0.7

    # LiveKit (WebRTC transport for browser voice)
    livekit_url: str = ""          # wss://<project>.livekit.cloud
    livekit_api_key: str = ""
    livekit_api_secret: str = ""

    # Deepgram (STT + TTS)
    deepgram_api_key: str = ""
    deepgram_stt_model: str = "nova-3"
    deepgram_stt_language: str = "en"
    deepgram_tts_model: str = "aura-asteria-en"

    # Audio
    mic_sample_rate: int = 16000
    mic_channels: int = 1
    mic_chunk_size: int = 4096
    silence_duration: float = 1.5
    min_speech_duration: float = 0.3

    # Security
    encryption_key: str = ""
    session_secret_key: str = "change-me-in-production-use-random-32-bytes"
    session_max_age_days: int = 7

    # Active client
    client_id: str = "grand-meridian-palace"

    # Token budget
    max_tokens_per_conversation: int = 50_000
    cost_alert_per_conversation: float = 0.50

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000


settings = Settings()

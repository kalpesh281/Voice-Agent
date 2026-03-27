from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # MongoDB Atlas
    mongodb_uri: str
    mongodb_database: str = "voice_agent"

    # OpenAI (LLM via LangChain)
    openai_api_key: str
    llm_model: str = "gpt-4o-mini"
    llm_temperature: float = 0.7

    # Deepgram (STT + TTS)
    deepgram_api_key: str
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

    # Active client
    client_id: str = "grand-meridian-palace"

    # Token budget
    max_tokens_per_conversation: int = 50_000
    cost_alert_per_conversation: float = 0.50


settings = Settings()

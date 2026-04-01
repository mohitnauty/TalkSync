from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TalkSync API"
    environment: str = "development"
    api_prefix: str = "/api"
    ws_path: str = "/ws/realtime"
    default_ai_tier: str = "free"

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"

    source_language: str = "en"
    target_languages: list[str] = ["hi", "pa"]
    supported_languages: list[str] = ["en", "hi", "pa"]
    supported_channels: list[str] = ["web", "zoom", "google_meet", "microsoft_teams", "zoho_meeting"]
    stt_model: str = "gpt-4o-mini-transcribe"
    translation_model: str = "gpt-5-mini"
    tts_model: str = "gpt-4o-mini-tts"
    tts_voice: str = "alloy"
    transcript_phase_two_enabled: bool = False
    voice_selection_phase_two_enabled: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        populate_by_name=True,
    )

    @property
    def has_real_openai_key(self) -> bool:
        key = (self.openai_api_key or "").strip()
        if not key:
            return False
        if key in {"your_real_openai_api_key", "your_key_here"}:
            return False
        return True


@lru_cache
def get_settings() -> Settings:
    return Settings()

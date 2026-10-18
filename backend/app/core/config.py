from functools import lru_cache

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated FleetMind application configuration."""

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_prefix="FLEETMIND_",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "FleetMind AI"
    environment: str = "development"
    log_level: str = "INFO"

    postgres_dsn: SecretStr = SecretStr(
        "postgresql://fleetmind:fleetmind@localhost:5432/fleetmind"
    )

    redis_url: str = "redis://localhost:6379/0"
    redis_event_stream: str = "fleetmind.events"

    # Provider credentials
    groq_api_key: SecretStr | None = None
    gemini_api_key: SecretStr | None = None
    mistral_api_key: SecretStr | None = None

    # Optional local provider
    enable_ollama: bool = False
    ollama_host: str = "http://localhost:11434"

    # Models
    groq_model: str = "openai/gpt-oss-20b"
    gemini_model: str = "gemini-3.8-flash"
    mistral_model: str = "mistral-small-2603"
    ollama_model: str = "qwen3:8b"

    # Reliability
    llm_max_attempts: int = Field(default=2, ge=1, le=5)
    llm_backoff_seconds: float = Field(default=0.5, ge=0)
    llm_circuit_failure_threshold: int = Field(default=3, ge=1)
    llm_circuit_cooldown_seconds: float = Field(default=30.0, gt=0)
    llm_default_timeout_seconds: float = Field(default=30.0, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
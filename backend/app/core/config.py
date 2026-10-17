from functools import lru_cache

from pydantic import SecretStr
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
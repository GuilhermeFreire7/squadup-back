from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SquadUp API"
    environment: str = "development"
    database_url: str = "sqlite:///./squadup.db"
    secret_key: str = "change-me-in-.env"
    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_days: int = 30
    cors_origins: list[str] = [
        "http://localhost:8081",
        "http://localhost:19006",
        "exp://localhost:19000",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()

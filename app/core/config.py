from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

DEFAULT_CORS_ORIGINS = [
    "http://localhost:8081",
    "http://localhost:19006",
    "exp://localhost:19000",
]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "SquadUp API"
    environment: str = "development"
    database_url: str = "sqlite:///./squadup.db"
    secret_key: str = "change-me-in-.env"
    access_token_expire_minutes: int = 60 * 24
    refresh_token_expire_days: int = 30
    cors_origins: Annotated[list[str], NoDecode] = DEFAULT_CORS_ORIGINS

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()

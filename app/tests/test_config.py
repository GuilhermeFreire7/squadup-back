import pytest

from app.core.config import DEFAULT_CORS_ORIGINS, Settings


def test_cors_origins_defaults_when_env_not_set(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    settings = Settings(_env_file=None)

    assert settings.cors_origins == DEFAULT_CORS_ORIGINS


def test_cors_origins_parses_comma_separated_env_var(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://app.squadup.com, https://squadup.expo.app")

    settings = Settings(_env_file=None)

    assert settings.cors_origins == [
        "https://app.squadup.com",
        "https://squadup.expo.app",
    ]


@pytest.mark.parametrize(
    "raw_url",
    [
        "postgres://user:pass@host.neon.tech/db?sslmode=require",
        "postgresql://user:pass@host.neon.tech/db?sslmode=require",
        "postgresql+psycopg://user:pass@host.neon.tech/db?sslmode=require",
    ],
)
def test_database_url_forces_psycopg_driver(monkeypatch, raw_url):
    monkeypatch.setenv("DATABASE_URL", raw_url)

    settings = Settings(_env_file=None)

    assert (
        settings.database_url == "postgresql+psycopg://user:pass@host.neon.tech/db?sslmode=require"
    )


def test_database_url_keeps_sqlite_untouched(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./squadup.db")

    settings = Settings(_env_file=None)

    assert settings.database_url == "sqlite:///./squadup.db"

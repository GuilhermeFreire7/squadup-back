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

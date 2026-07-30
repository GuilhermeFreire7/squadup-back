from typing import Any

import boto3
import pytest
from fastapi import HTTPException

from app.core.config import Settings
from app.services import storage_service


class _FakeS3Client:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def put_object(self, **kwargs: Any) -> None:
        self.calls.append(kwargs)


def _configured_settings(**overrides: Any) -> Settings:
    return Settings(
        _env_file=None,
        s3_bucket="squadup-avatars",
        s3_access_key_id="key",
        s3_secret_access_key="secret",
        **overrides,
    )


def test_upload_avatar_raises_when_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(storage_service, "get_settings", lambda: Settings(_env_file=None))

    with pytest.raises(HTTPException) as exc_info:
        storage_service.upload_avatar("user-1", b"fake-image-bytes", "image/jpeg")

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail["code"] == "STORAGE_NOT_CONFIGURED"  # type: ignore[index]


def test_upload_avatar_calls_put_object_and_returns_default_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeS3Client()
    monkeypatch.setattr(storage_service, "get_settings", lambda: _configured_settings())
    monkeypatch.setattr(boto3, "client", lambda *a, **k: fake_client)

    url = storage_service.upload_avatar("user-1", b"fake-image-bytes", "image/jpeg")

    assert len(fake_client.calls) == 1
    call = fake_client.calls[0]
    assert call["Bucket"] == "squadup-avatars"
    assert call["Body"] == b"fake-image-bytes"
    assert call["ContentType"] == "image/jpeg"
    assert call["Key"].startswith("avatars/user-1/")
    assert call["Key"].endswith(".jpg")
    assert url == f"https://squadup-avatars.s3.amazonaws.com/{call['Key']}"


def test_upload_avatar_uses_public_url_base_when_configured(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeS3Client()
    monkeypatch.setattr(
        storage_service,
        "get_settings",
        lambda: _configured_settings(s3_public_url_base="https://cdn.squadup.com"),
    )
    monkeypatch.setattr(boto3, "client", lambda *a, **k: fake_client)

    url = storage_service.upload_avatar("user-1", b"fake-image-bytes", "image/png")

    assert url.startswith("https://cdn.squadup.com/avatars/user-1/")
    assert url.endswith(".png")


def test_upload_avatar_uses_endpoint_url_when_no_public_base(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_client = _FakeS3Client()
    monkeypatch.setattr(
        storage_service,
        "get_settings",
        lambda: _configured_settings(s3_endpoint_url="https://abc123.r2.cloudflarestorage.com"),
    )
    monkeypatch.setattr(boto3, "client", lambda *a, **k: fake_client)

    url = storage_service.upload_avatar("user-1", b"fake-image-bytes", "image/webp")

    assert url.startswith("https://abc123.r2.cloudflarestorage.com/squadup-avatars/avatars/user-1/")
    assert url.endswith(".webp")

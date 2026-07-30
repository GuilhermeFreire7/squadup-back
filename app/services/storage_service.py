import uuid

import boto3
from fastapi import HTTPException, status

from app.core.config import get_settings

MAX_AVATAR_SIZE_BYTES = 5 * 1024 * 1024

ALLOWED_AVATAR_CONTENT_TYPES: dict[str, str] = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}

STORAGE_NOT_CONFIGURED = HTTPException(
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
    detail={
        "code": "STORAGE_NOT_CONFIGURED",
        "message": "Upload de imagem indisponível: storage não configurado neste ambiente.",
    },
)


def upload_avatar(user_id: str, content: bytes, content_type: str) -> str:
    """Envia o avatar para o bucket S3-compatible configurado e retorna a URL pública.

    Genérico por design (T4): funciona com qualquer provedor S3-compatible (AWS S3, Cloudflare
    R2, Backblaze B2 etc.) via `endpoint_url` configurável, sem acoplar o código a um provedor
    específico — só as variáveis de ambiente mudam entre eles.
    """
    settings = get_settings()
    if not (settings.s3_bucket and settings.s3_access_key_id and settings.s3_secret_access_key):
        raise STORAGE_NOT_CONFIGURED

    extension = ALLOWED_AVATAR_CONTENT_TYPES[content_type]
    key = f"avatars/{user_id}/{uuid.uuid4()}.{extension}"

    client = boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        region_name=settings.s3_region,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
    )
    client.put_object(Bucket=settings.s3_bucket, Key=key, Body=content, ContentType=content_type)

    return _build_public_url(key)


def _build_public_url(key: str) -> str:
    settings = get_settings()
    if settings.s3_public_url_base:
        return f"{settings.s3_public_url_base.rstrip('/')}/{key}"
    if settings.s3_endpoint_url:
        return f"{settings.s3_endpoint_url.rstrip('/')}/{settings.s3_bucket}/{key}"
    return f"https://{settings.s3_bucket}.s3.amazonaws.com/{key}"

from pydantic import BaseModel, Field


class PushTokenCreate(BaseModel):
    token: str = Field(
        min_length=1,
        examples=["ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"],
    )
    device_id: str | None = Field(
        default=None,
        min_length=1,
        examples=["a1b2c3d4-device-installation-id"],
        description="Identificador estável do dispositivo/instalação (ex.: "
        "`expo-application`'s `androidId`/`getIosIdForVendorAsync()`), usado para revogar só "
        "este token num logout de um único dispositivo (`POST /auth/logout`).",
    )

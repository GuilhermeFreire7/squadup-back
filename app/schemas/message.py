from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import MessageType
from app.schemas.user import PublicProfileRead


class MessageCreate(BaseModel):
    text: str = Field(min_length=1, examples=["Confirmado, chego 10 minutos antes!"])


class MessageRead(BaseModel):
    id: str = Field(examples=["message-1"])
    match_id: str = Field(examples=["match-1"])
    sender: PublicProfileRead
    text: str = Field(examples=["Confirmado, chego 10 minutos antes!"])
    created_at: datetime
    type: MessageType = Field(examples=[MessageType.MESSAGE])

    model_config = {"from_attributes": True}

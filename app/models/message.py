import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import MessageType

if TYPE_CHECKING:
    from app.models.match import Match
    from app.models.user import User


class Message(SQLModel, table=True):
    __tablename__ = "messages"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    match_id: str = Field(foreign_key="matches.id", index=True)
    sender_id: str = Field(foreign_key="users.id", index=True)
    text: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    type: MessageType = Field(default=MessageType.MESSAGE)

    match: "Match" = Relationship(back_populates="messages")
    sender: "User" = Relationship(back_populates="sent_messages")

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User


class PushToken(SQLModel, table=True):
    __tablename__ = "push_tokens"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    token: str = Field(unique=True, index=True)
    device_id: str | None = Field(default=None, index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    user: "User" = Relationship(back_populates="push_tokens")

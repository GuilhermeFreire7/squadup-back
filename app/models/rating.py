import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.match import Match
    from app.models.user import User


class Rating(SQLModel, table=True):
    __tablename__ = "ratings"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    rated_user_id: str = Field(foreign_key="users.id", index=True)
    rater_user_id: str = Field(foreign_key="users.id", index=True)
    match_id: str = Field(foreign_key="matches.id", index=True)
    punctuality: int = Field(ge=1, le=5)
    respect: int = Field(ge=1, le=5)
    behavior: int = Field(ge=1, le=5)
    presence: int = Field(ge=1, le=5)
    overall: int = Field(ge=1, le=5)
    comment: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    rated_user: "User" = Relationship(
        back_populates="ratings_received",
        sa_relationship_kwargs={"foreign_keys": "Rating.rated_user_id"},
    )
    rater_user: "User" = Relationship(
        back_populates="ratings_given",
        sa_relationship_kwargs={"foreign_keys": "Rating.rater_user_id"},
    )
    match: "Match" = Relationship(back_populates="ratings")

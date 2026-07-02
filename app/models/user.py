import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import JSON, Column, Field, Relationship, SQLModel

from app.models.enums import ExperienceLevel, Sport, UserRole

if TYPE_CHECKING:
    from app.models.match import Match
    from app.models.message import Message
    from app.models.participant import Participant
    from app.models.rating import Rating
    from app.models.report import Report


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str
    email: str = Field(unique=True, index=True)
    hashed_password: str
    photo_url: str | None = None
    age: int
    location: str
    bio: str | None = None
    favorite_sports: list[Sport] = Field(default_factory=list, sa_column=Column(JSON))
    level: ExperienceLevel = Field(default=ExperienceLevel.BEGINNER)
    is_verified: bool = Field(default=False)
    role: UserRole = Field(default=UserRole.USER)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    organized_matches: list["Match"] = Relationship(back_populates="organizer")
    participations: list["Participant"] = Relationship(back_populates="user")
    sent_messages: list["Message"] = Relationship(back_populates="sender")
    ratings_received: list["Rating"] = Relationship(
        back_populates="rated_user",
        sa_relationship_kwargs={"foreign_keys": "Rating.rated_user_id"},
    )
    ratings_given: list["Rating"] = Relationship(
        back_populates="rater_user",
        sa_relationship_kwargs={"foreign_keys": "Rating.rater_user_id"},
    )
    reports_received: list["Report"] = Relationship(
        back_populates="reported_user",
        sa_relationship_kwargs={"foreign_keys": "Report.reported_user_id"},
    )
    reports_made: list["Report"] = Relationship(
        back_populates="reporter_user",
        sa_relationship_kwargs={"foreign_keys": "Report.reporter_user_id"},
    )

import uuid
from datetime import date, time
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import ExperienceLevel, MatchStatus, Sport

if TYPE_CHECKING:
    from app.models.message import Message
    from app.models.participant import Participant
    from app.models.rating import Rating
    from app.models.report import Report
    from app.models.user import User


class Match(SQLModel, table=True):
    __tablename__ = "matches"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    sport: Sport
    title: str
    location: str
    date: date
    time: time
    max_participants: int = Field(gt=0)
    level: ExperienceLevel
    description: str | None = None
    organizer_id: str = Field(foreign_key="users.id", index=True)
    status: MatchStatus = Field(default=MatchStatus.OPEN)
    allow_beginners: bool = Field(default=True)
    requires_approval: bool = Field(default=False)

    organizer: "User" = Relationship(back_populates="organized_matches")
    participants: list["Participant"] = Relationship(back_populates="match")
    messages: list["Message"] = Relationship(back_populates="match")
    ratings: list["Rating"] = Relationship(back_populates="match")
    reports: list["Report"] = Relationship(back_populates="match")

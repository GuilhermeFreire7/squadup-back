from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import ParticipationStatus

if TYPE_CHECKING:
    from app.models.match import Match
    from app.models.user import User


class Participant(SQLModel, table=True):
    __tablename__ = "participants"

    match_id: str = Field(foreign_key="matches.id", primary_key=True)
    user_id: str = Field(foreign_key="users.id", primary_key=True)
    status: ParticipationStatus = Field(default=ParticipationStatus.PENDING)

    match: "Match" = Relationship(back_populates="participants")
    user: "User" = Relationship(back_populates="participations")

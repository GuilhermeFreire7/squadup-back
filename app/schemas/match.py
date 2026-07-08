from datetime import date as date_
from datetime import time as time_

from pydantic import BaseModel, Field

from app.models.enums import ExperienceLevel, MatchStatus, Sport
from app.schemas.user import PublicProfileRead


class MatchCreate(BaseModel):
    sport: Sport = Field(examples=[Sport.FOOTBALL])
    title: str = Field(min_length=1, examples=["Pelada de domingo na arena"])
    location: str = Field(min_length=1, examples=["Arena Botafogo — Rua General Polidoro, 400"])
    date: date_ = Field(examples=["2026-05-25"])
    time: time_ = Field(examples=["09:00:00"])
    max_participants: int = Field(gt=0, examples=[14])
    level: ExperienceLevel = Field(examples=[ExperienceLevel.INTERMEDIATE])
    description: str | None = Field(default=None, examples=["Jogo de campo gramado."])
    allow_beginners: bool = Field(default=True, examples=[True])
    requires_approval: bool = Field(default=False, examples=[False])


class MatchRef(BaseModel):
    id: str = Field(examples=["match-1"])
    title: str = Field(examples=["Pelada de domingo na arena"])
    sport: Sport = Field(examples=[Sport.FOOTBALL])
    date: date_ = Field(examples=["2026-05-25"])

    model_config = {"from_attributes": True}


class ParticipantRead(BaseModel):
    user: PublicProfileRead
    status: str = Field(examples=["confirmed"])

    model_config = {"from_attributes": True}


class MatchRead(BaseModel):
    id: str = Field(examples=["match-1"])
    sport: Sport = Field(examples=[Sport.FOOTBALL])
    title: str = Field(examples=["Pelada de domingo na arena"])
    location: str = Field(examples=["Arena Botafogo — Rua General Polidoro, 400"])
    date: date_ = Field(examples=["2026-05-25"])
    time: time_ = Field(examples=["09:00:00"])
    max_participants: int = Field(examples=[14])
    level: ExperienceLevel = Field(examples=[ExperienceLevel.INTERMEDIATE])
    description: str | None = Field(default=None, examples=["Jogo de campo gramado."])
    organizer_id: str = Field(examples=["user-1"])
    status: MatchStatus = Field(examples=[MatchStatus.OPEN])
    allow_beginners: bool = Field(examples=[False])
    requires_approval: bool = Field(examples=[False])
    confirmed_count: int = Field(examples=[4])
    available_slots: int = Field(examples=[10])

    model_config = {"from_attributes": True}


class MatchDetailRead(MatchRead):
    organizer: PublicProfileRead
    participants: list[ParticipantRead]

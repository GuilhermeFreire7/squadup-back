from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from app.models.enums import ReportReason, ReportStatus
from app.schemas.match import MatchRef
from app.schemas.user import PublicProfileRead


class ReportCreate(BaseModel):
    reported_user_id: str = Field(examples=["3f1b1c2e-4a5b-4c6d-8e9f-0a1b2c3d4e5f"])
    match_id: str | None = Field(default=None, examples=["match-1"])
    reason: ReportReason = Field(examples=[ReportReason.BAD_BEHAVIOR])
    description: str = Field(
        min_length=1, examples=["Foi agressivo com outros jogadores durante a partida."]
    )


class ReportRead(BaseModel):
    id: str = Field(examples=["3f1b1c2e-4a5b-4c6d-8e9f-0a1b2c3d4e5f"])
    reported_user: PublicProfileRead
    reporter: PublicProfileRead
    match: MatchRef | None = Field(default=None)
    reason: ReportReason = Field(examples=[ReportReason.BAD_BEHAVIOR])
    description: str = Field(examples=["Foi agressivo com outros jogadores durante a partida."])
    status: ReportStatus = Field(examples=[ReportStatus.PENDING])
    created_at: datetime

    model_config = {"from_attributes": True}


class ReportAction(StrEnum):
    ARCHIVE = "archive"
    WARN = "warn"
    BAN = "ban"


class ReportUpdate(BaseModel):
    action: ReportAction = Field(examples=[ReportAction.ARCHIVE])

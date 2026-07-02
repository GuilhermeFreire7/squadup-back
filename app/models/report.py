import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship, SQLModel

from app.models.enums import ReportReason, ReportStatus

if TYPE_CHECKING:
    from app.models.match import Match
    from app.models.user import User


class Report(SQLModel, table=True):
    __tablename__ = "reports"

    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    reported_user_id: str = Field(foreign_key="users.id", index=True)
    reporter_user_id: str = Field(foreign_key="users.id", index=True)
    match_id: str | None = Field(default=None, foreign_key="matches.id", index=True)
    reason: ReportReason
    description: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    status: ReportStatus = Field(default=ReportStatus.PENDING)

    reported_user: "User" = Relationship(
        back_populates="reports_received",
        sa_relationship_kwargs={"foreign_keys": "Report.reported_user_id"},
    )
    reporter_user: "User" = Relationship(
        back_populates="reports_made",
        sa_relationship_kwargs={"foreign_keys": "Report.reporter_user_id"},
    )
    match: "Match" = Relationship(back_populates="reports")

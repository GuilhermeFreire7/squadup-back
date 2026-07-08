from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.match import MatchRef
from app.schemas.user import PublicProfileRead


class RatingCreate(BaseModel):
    punctuality: int = Field(ge=1, le=5, examples=[5])
    respect: int = Field(ge=1, le=5, examples=[5])
    behavior: int = Field(ge=1, le=5, examples=[4])
    presence: int = Field(ge=1, le=5, examples=[5])
    overall: int = Field(ge=1, le=5, examples=[5])
    comment: str | None = Field(default=None, examples=["Ótimo parceiro de jogo, super pontual!"])


class RatingRead(BaseModel):
    id: str = Field(examples=["rating-1"])
    match: MatchRef
    rated_user: PublicProfileRead
    rater: PublicProfileRead
    punctuality: int = Field(examples=[5])
    respect: int = Field(examples=[5])
    behavior: int = Field(examples=[4])
    presence: int = Field(examples=[5])
    overall: int = Field(examples=[5])
    comment: str | None = Field(default=None, examples=["Ótimo parceiro de jogo, super pontual!"])
    created_at: datetime

    model_config = {"from_attributes": True}

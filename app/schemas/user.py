from pydantic import BaseModel, Field

from app.models.enums import ExperienceLevel, Sport, UserRole


class UserRead(BaseModel):
    id: str = Field(examples=["3f1b1c2e-4a5b-4c6d-8e9f-0a1b2c3d4e5f"])
    name: str = Field(examples=["Ana Souza"])
    email: str = Field(examples=["ana.souza@example.com"])
    photo_url: str | None = Field(default=None, examples=["https://example.com/avatar.jpg"])
    age: int = Field(examples=[28])
    location: str = Field(examples=["São Paulo, SP"])
    bio: str | None = Field(default=None, examples=["Adoro futebol de fim de semana."])
    favorite_sports: list[Sport] = Field(examples=[[Sport.FOOTBALL, Sport.VOLLEYBALL]])
    level: ExperienceLevel = Field(examples=[ExperienceLevel.INTERMEDIATE])
    is_verified: bool = Field(examples=[False])
    role: UserRole = Field(examples=[UserRole.USER])

    model_config = {"from_attributes": True}

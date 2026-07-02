from pydantic import BaseModel, EmailStr, Field

from app.models.enums import Sport


class RegisterRequest(BaseModel):
    name: str = Field(examples=["Ana Souza"], min_length=1)
    email: EmailStr = Field(examples=["ana.souza@example.com"])
    password: str = Field(examples=["senha-super-secreta"], min_length=8)
    age: int = Field(examples=[28], gt=0)
    location: str = Field(examples=["São Paulo, SP"], min_length=1)
    bio: str | None = Field(default=None, examples=["Adoro futebol de fim de semana."])
    favorite_sports: list[Sport] = Field(default_factory=list, examples=[[Sport.FOOTBALL]])


class LoginRequest(BaseModel):
    email: EmailStr = Field(examples=["ana.souza@example.com"])
    password: str = Field(examples=["senha-super-secreta"])


class TokenResponse(BaseModel):
    access_token: str = Field(examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."])
    token_type: str = Field(default="bearer", examples=["bearer"])

from pydantic import BaseModel, Field


class PushTokenCreate(BaseModel):
    token: str = Field(
        min_length=1,
        examples=["ExponentPushToken[xxxxxxxxxxxxxxxxxxxxxx]"],
    )

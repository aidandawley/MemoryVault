from pydantic import BaseModel, Field, conlist

# Base schema for Card
# Provided by user
class CardBase(BaseModel):
    video_id: str = Field(..., description="Unique identifier for the video")
    caption: str = Field(..., description="Caption of the video")
    tags: list[str] = Field(default_factory=list, description="List of tags associated with the video")
    is_active: bool = Field(default=True, description="Indicates if the card is active", alias="isActive")

# Public schema for Card
# ID is not provided by user 
class CardPublic(CardBase):
    card_id: str = Field(..., description="Unique identifier for the card", alias="cardId")
    class Config:
        orm_mode = True


from pydantic import BaseModel, Field
from typing import List, Literal

class CardBase(BaseModel):
    media_id: str = Field(..., description="Unique identifier for the media file")
    media_type: Literal["image", "video"]
    caption: str
    tags: List[str] = Field(default_factory=list)
    is_active: bool = Field(default=True, alias="isActive")

class CardPublic(CardBase):
    card_id: str = Field(..., alias="cardId")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

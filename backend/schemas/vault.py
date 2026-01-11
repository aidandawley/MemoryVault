from pydantic import BaseModel, Field
from typing import List, Optional
from backend.schemas.card import CardPublic

class VaultBase(BaseModel):
    title: str
    description: Optional[str] = None

class VaultCreate(VaultBase):
    pass

class VaultPublic(VaultBase):
    vault_id: str = Field(..., alias="vaultId")
    owner_id: str = Field(..., alias="ownerId")

    model_config = {
        "from_attributes": True,
        "populate_by_name": True
    }

class VaultWithCards(VaultPublic):
    cards: List[CardPublic] = []

# api/routers/cards.py
from fastapi import APIRouter
router = APIRouter()


@router.get("/cards/{}")
def get_cards():
    pass
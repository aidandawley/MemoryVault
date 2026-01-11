from fastapi import APIRouter
from backend.api.routers import health, vaults, cards, share

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(vaults.router)
api_router.include_router(cards.router)
api_router.include_router(share.router)

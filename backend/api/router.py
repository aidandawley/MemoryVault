from fastapi import APIRouter

from backend.api.routers.health import router as health_router
from backend.api.routers.vaults import router as vaults_router
from backend.api.routers.cards import router as cards_router
from backend.api.routers.share import router as share_router
from backend.api.routers.media import router as media_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(vaults_router)
api_router.include_router(cards_router)
api_router.include_router(share_router)
api_router.include_router(media_router)

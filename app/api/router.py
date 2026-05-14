"""Application route composition."""

from fastapi import APIRouter

from app.api.routes import admin, ai, apikey, health, pages

api_router = APIRouter()

api_router.include_router(pages.router)
api_router.include_router(health.router, prefix="/ai", tags=["AI检测"])
api_router.include_router(ai.router, prefix="/ai", tags=["AI检测"])
api_router.include_router(apikey.router, prefix="/apikey", tags=["API Key 管理"])
api_router.include_router(admin.router, prefix="/admin", tags=["管理后台"])

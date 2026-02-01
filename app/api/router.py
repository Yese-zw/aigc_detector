"""
Main API router
主路由配置
"""
from fastapi import APIRouter
from app.api.v1 import endpoints as v1_endpoints
from app.api.v1 import apikey_endpoints
from app.api import admin_endpoints

# 创建主路由
api_router = APIRouter()

# 包含v1版本的路由
api_router.include_router(
    v1_endpoints.router,
    prefix="/ai",
    tags=["AI检测"]
)

# 包含API Key管理路由
api_router.include_router(
    apikey_endpoints.router,
    prefix="/apikey",
    tags=["API Key 管理"]
)

# 包含Admin路由
api_router.include_router(
    admin_endpoints.router,
    prefix="/admin",
    tags=["管理后台"]
)





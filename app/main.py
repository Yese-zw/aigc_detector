"""
FastAPI Application Entry Point
应用主入口
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.logger import logger
from app.api.router import api_router
from app import __version__


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("=" * 50)
    logger.info(f"正在启动 {settings.APP_NAME} v{__version__}")
    logger.info(f"服务地址: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"API文档: http://{settings.HOST}:{settings.PORT}/docs")
    logger.info("=" * 50)
    
    yield
    
    # 关闭时执行
    logger.info("正在关闭应用...")
    # 这里可以添加清理资源的代码
    from app.core.redis_client import redis_client_manager
    redis_client_manager.close()
    logger.info("应用已关闭")


# 创建FastAPI应用
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=__version__,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# 注册路由
app.include_router(api_router)


@app.get("/", tags=["根路径"])
async def root():
    """根路径"""
    return JSONResponse(
        content={
            "message": f"欢迎使用 {settings.APP_NAME}",
            "version": __version__,
        }
    )


@app.get("/ping", tags=["健康检查"])
async def ping():
    """简单的ping接口"""
    return {"status": "ok", "message": "pong"}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        app,
        host=settings.HOST,
        port=settings.PORT,
        log_level=settings.LOG_LEVEL.lower()
    )


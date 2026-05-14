"""FastAPI application factory and entry point."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.router import api_router
from app.clients.redis import redis_manager
from app.core.config import settings
from app.core.exception_handlers import register_exception_handlers
from app.core.logger import logger
from app.core.request_logging import request_logging_middleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("=" * 50)
    logger.info(f"正在启动 {settings.APP_NAME} v{__version__}")
    logger.info(f"服务地址: http://{settings.HOST}:{settings.PORT}")
    logger.info("=" * 50)
    yield
    logger.info("正在关闭应用...")
    redis_manager.close()
    logger.info("应用已关闭")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
        allow_methods=settings.CORS_ALLOW_METHODS,
        allow_headers=settings.CORS_ALLOW_HEADERS,
    )
    app.middleware("http")(request_logging_middleware)
    register_exception_handlers(app)
    app.include_router(api_router)
    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=settings.HOST, port=settings.PORT, log_level=settings.LOG_LEVEL.lower())

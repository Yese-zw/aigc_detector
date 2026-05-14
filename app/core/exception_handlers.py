"""FastAPI exception handlers."""

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

from app.core.exceptions import (
    APIKeyNotFoundException,
    AppException,
    AuthExpiredException,
    DetectionFailedException,
    InvalidLanguageException,
    QuotaExceededException,
    RedisConnectionException,
)
from app.core.logger import logger


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(QuotaExceededException)
    async def quota_handler(request: Request, exc: QuotaExceededException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(APIKeyNotFoundException)
    async def not_found_handler(request: Request, exc: APIKeyNotFoundException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(InvalidLanguageException)
    async def invalid_language_handler(request: Request, exc: InvalidLanguageException):
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"detail": str(exc)})

    @app.exception_handler(AuthExpiredException)
    async def auth_expired_handler(request: Request, exc: AuthExpiredException):
        logger.error(f"Upstream Auth Expired: {str(exc)}")
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={"detail": "服务暂时不可用（上游认证失效）"})

    @app.exception_handler(DetectionFailedException)
    async def detection_failed_handler(request: Request, exc: DetectionFailedException):
        logger.error(f"上游请求失败: {str(exc)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": f"AI检测请求失败: {str(exc)}"})

    @app.exception_handler(RedisConnectionException)
    async def redis_handler(request: Request, exc: RedisConnectionException):
        logger.error(f"Redis连接失败: {str(exc)}")
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "缓存服务连接失败，请稍后重试"})

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail}, headers=exc.headers)

    @app.exception_handler(Exception)
    async def unexpected_handler(request: Request, exc: Exception):
        logger.error(f"未知错误: {str(exc)}", exc_info=True)
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"detail": "服务器内部错误"})

"""Health routes."""

from fastapi import APIRouter

from app import __version__
from app.clients.redis import get_redis_client
from app.core.logger import logger
from app.schemas.common import HealthCheckResponse

router = APIRouter()


@router.get("/health", response_model=HealthCheckResponse, summary="健康检查", description="检查服务和Redis连接状态")
async def health_check():
    redis_connected = False
    try:
        get_redis_client().ping()
        redis_connected = True
    except Exception as exc:
        logger.warning(f"Redis连接检查失败: {str(exc)}")
    return HealthCheckResponse(
        status="healthy" if redis_connected else "degraded",
        version=__version__,
        redis_connected=redis_connected,
    )

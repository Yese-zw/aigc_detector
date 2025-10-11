"""
Redis client management
Redis客户端管理模块
"""
import redis
from typing import Optional
from app.core.config import settings
from app.core.logger import logger
from app.core.exceptions import RedisConnectionException


class RedisClient:
    """Redis客户端封装类"""
    
    def __init__(self):
        self._client: Optional[redis.Redis] = None
    
    def get_client(self) -> redis.Redis:
        """获取Redis客户端实例"""
        if self._client is None:
            try:
                self._client = redis.Redis(
                    host=settings.REDIS_HOST,
                    port=settings.REDIS_PORT,
                    password=settings.REDIS_PASSWORD,
                    db=settings.REDIS_DB,
                    decode_responses=settings.REDIS_DECODE_RESPONSES,
                    socket_connect_timeout=5,
                    socket_timeout=5,
                    retry_on_timeout=True
                )
                # 测试连接
                self._client.ping()
                logger.info(f"Redis连接成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            except Exception as e:
                logger.error(f"Redis连接失败: {str(e)}")
                raise RedisConnectionException()
        
        return self._client
    
    def close(self):
        """关闭Redis连接"""
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Redis连接已关闭")


# 全局Redis客户端实例
redis_client_manager = RedisClient()


def get_redis_client() -> redis.Redis:
    """获取Redis客户端（依赖注入用）"""
    return redis_client_manager.get_client()


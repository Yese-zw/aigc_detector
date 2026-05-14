"""Redis client factory."""

from typing import Optional

import redis

from app.core.config import settings
from app.core.exceptions import RedisConnectionException
from app.core.logger import logger


class RedisClientManager:
    def __init__(self):
        self._client: Optional[redis.Redis] = None

    def get_client(self) -> redis.Redis:
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
                    retry_on_timeout=True,
                )
                self._client.ping()
                logger.info(f"Redis连接成功: {settings.REDIS_HOST}:{settings.REDIS_PORT}")
            except Exception as exc:
                logger.error(f"Redis连接失败: {str(exc)}")
                raise RedisConnectionException()
        return self._client

    def close(self) -> None:
        if self._client:
            self._client.close()
            self._client = None
            logger.info("Redis连接已关闭")


redis_manager = RedisClientManager()


def get_redis_client() -> redis.Redis:
    return redis_manager.get_client()

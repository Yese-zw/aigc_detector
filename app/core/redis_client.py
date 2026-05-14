"""Backward-compatible Redis imports."""

from app.clients.redis import get_redis_client, redis_manager as redis_client_manager

__all__ = ["get_redis_client", "redis_client_manager"]

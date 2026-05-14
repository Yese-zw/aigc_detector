"""API key management service."""

import secrets
from datetime import datetime
from typing import Any, Optional

from app.core.logger import logger
from app.clients.redis import get_redis_client
from app.schemas.apikey import APIKey, APIKeyCreate


class APIKeyService:
    def __init__(self):
        self.redis_client = get_redis_client()
        self.key_prefix = "apikey:"
        self.key_list = "apikeys:list"

    def _generate_key(self) -> str:
        return f"sk_{secrets.token_urlsafe(32)}"

    def _get_redis_key(self, api_key: str) -> str:
        return f"{self.key_prefix}{api_key}"

    def create_apikey(self, create_data: APIKeyCreate) -> APIKey:
        api_key = self._generate_key()
        key_data = APIKey(
            key=api_key,
            name=create_data.name,
            quota=create_data.quota,
            total_quota=create_data.quota,
            is_active=True,
            created_at=datetime.now().isoformat(),
            last_used_at=None,
            description=create_data.description,
        )

        self.redis_client.set(self._get_redis_key(api_key), key_data.model_dump_json())
        self.redis_client.sadd(self.key_list, api_key)
        logger.info(f"创建新的API Key - 名称: {create_data.name}, 额度: {create_data.quota}")
        return key_data

    def get_apikey(self, api_key: str) -> Optional[APIKey]:
        data = self.redis_client.get(self._get_redis_key(api_key))
        if not data:
            return None

        try:
            return APIKey.model_validate_json(data)
        except Exception as exc:
            logger.error(f"解析API Key数据失败: {str(exc)}")
            return None

    def list_apikeys(self) -> list[APIKey]:
        api_keys = []
        for api_key in self.redis_client.smembers(self.key_list):
            key_data = self.get_apikey(api_key)
            if key_data:
                api_keys.append(key_data)
        return sorted(api_keys, key=lambda item: item.created_at, reverse=True)

    def verify_and_consume_quota(self, api_key: str, usage: int) -> dict[str, Any]:
        key_data = self.get_apikey(api_key)
        if not key_data:
            logger.warning(f"API Key 不存在: {api_key[:10]}...")
            return {"valid": False, "message": "API Key 不存在", "remaining_quota": 0}
        if not key_data.is_active:
            logger.warning(f"API Key 已禁用: {key_data.name}")
            return {"valid": False, "message": "API Key 已禁用", "remaining_quota": key_data.quota}
        if key_data.quota < usage:
            logger.warning(f"API Key 额度不足: {key_data.name}, 剩余: {key_data.quota}, 需要: {usage}")
            return {
                "valid": False,
                "message": f"额度不足，剩余: {key_data.quota}, 需要: {usage}",
                "remaining_quota": key_data.quota,
            }

        key_data.quota -= usage
        key_data.last_used_at = datetime.now().isoformat()
        self.redis_client.set(self._get_redis_key(api_key), key_data.model_dump_json())
        return {
            "valid": True,
            "message": "验证成功",
            "remaining_quota": key_data.quota,
            "key_name": key_data.name,
        }

    def update_apikey(
        self,
        api_key: str,
        is_active: Optional[bool] = None,
        quota: Optional[int] = None,
        name: Optional[str] = None,
        description: Optional[str] = None,
    ) -> Optional[APIKey]:
        key_data = self.get_apikey(api_key)
        if not key_data:
            return None

        if is_active is not None:
            key_data.is_active = is_active
            logger.info(f"更新API Key状态 - {key_data.name}: {'启用' if is_active else '禁用'}")
        if quota is not None:
            key_data.quota += quota
            key_data.total_quota += quota
            logger.info(f"更新API Key额度 - {key_data.name}: +{quota}")
        if name is not None:
            key_data.name = name
        if description is not None:
            key_data.description = description

        self.redis_client.set(self._get_redis_key(api_key), key_data.model_dump_json())
        return key_data

    def delete_apikey(self, api_key: str) -> bool:
        key_data = self.get_apikey(api_key)
        if not key_data:
            return False
        self.redis_client.delete(self._get_redis_key(api_key))
        self.redis_client.srem(self.key_list, api_key)
        logger.info(f"删除API Key - 名称: {key_data.name}")
        return True

    def get_usage_stats(self, api_key: str) -> Optional[dict[str, Any]]:
        key_data = self.get_apikey(api_key)
        if not key_data:
            return None

        used_quota = key_data.total_quota - key_data.quota
        usage_percentage = (used_quota / key_data.total_quota * 100) if key_data.total_quota > 0 else 0
        return {
            "name": key_data.name,
            "total_quota": key_data.total_quota,
            "used_quota": used_quota,
            "remaining_quota": key_data.quota,
            "usage_percentage": round(usage_percentage, 2),
            "is_active": key_data.is_active,
            "created_at": key_data.created_at,
            "last_used_at": key_data.last_used_at,
        }

"""
API Key Service
API密钥管理服务
"""
import json
import secrets
from datetime import datetime
from typing import Optional, List, Dict, Any

from app.core.logger import logger
from app.core.redis_client import get_redis_client
from app.models.apikey import APIKey, APIKeyCreate


class APIKeyService:
    """API Key 管理服务"""
    
    def __init__(self):
        self.redis_client = get_redis_client()
        self.key_prefix = "apikey:"
        self.key_list = "apikeys:list"  # 存储所有API Key的列表
    
    def _generate_key(self) -> str:
        """生成唯一的 API Key"""
        return f"sk_{secrets.token_urlsafe(32)}"
    
    def _get_redis_key(self, api_key: str) -> str:
        """获取 Redis 键名"""
        return f"{self.key_prefix}{api_key}"
    
    def create_apikey(self, create_data: APIKeyCreate) -> APIKey:
        """
        创建新的 API Key
        
        Args:
            create_data: API Key 创建数据
        
        Returns:
            创建的 API Key 对象
        """
        api_key = self._generate_key()
        now = datetime.now().isoformat()
        
        key_data = APIKey(
            key=api_key,
            name=create_data.name,
            quota=create_data.quota,
            total_quota=create_data.quota,
            is_active=True,
            created_at=now,
            last_used_at=None,
            description=create_data.description
        )
        
        # 存储到 Redis
        redis_key = self._get_redis_key(api_key)
        self.redis_client.set(redis_key, key_data.model_dump_json())
        
        # 添加到 API Key 列表
        self.redis_client.sadd(self.key_list, api_key)
        
        logger.info(f"🔑 创建新的API Key - 名称: {create_data.name}, 额度: {create_data.quota}")
        
        return key_data
    
    def get_apikey(self, api_key: str) -> Optional[APIKey]:
        """
        获取 API Key 信息
        
        Args:
            api_key: API Key
        
        Returns:
            API Key 对象，如果不存在返回 None
        """
        redis_key = self._get_redis_key(api_key)
        data = self.redis_client.get(redis_key)
        
        if not data:
            return None
        
        try:
            return APIKey.model_validate_json(data)
        except Exception as e:
            logger.error(f"解析API Key数据失败: {str(e)}")
            return None
    
    def list_apikeys(self) -> List[APIKey]:
        """
        获取所有 API Key 列表
        
        Returns:
            API Key 列表
        """
        api_keys = []
        key_list = self.redis_client.smembers(self.key_list)
        
        for api_key in key_list:
            key_data = self.get_apikey(api_key)
            if key_data:
                api_keys.append(key_data)
        
        # 按创建时间排序
        api_keys.sort(key=lambda x: x.created_at, reverse=True)
        
        return api_keys
    
    def verify_and_consume_quota(self, api_key: str, usage: int) -> Dict[str, Any]:
        """
        验证 API Key 并消耗额度
        
        Args:
            api_key: API Key
            usage: 本次使用量（字符数）
        
        Returns:
            验证结果字典，包含 valid, message, remaining_quota 等信息
        """
        key_data = self.get_apikey(api_key)
        
        if not key_data:
            logger.warning(f"⚠️ API Key 不存在: {api_key[:10]}...")
            return {
                "valid": False,
                "message": "API Key 不存在",
                "remaining_quota": 0
            }
        
        if not key_data.is_active:
            logger.warning(f"⚠️ API Key 已禁用: {key_data.name}")
            return {
                "valid": False,
                "message": "API Key 已禁用",
                "remaining_quota": key_data.quota
            }
        
        if key_data.quota < usage:
            logger.warning(f"⚠️ API Key 额度不足: {key_data.name}, 剩余: {key_data.quota}, 需要: {usage}")
            return {
                "valid": False,
                "message": f"额度不足，剩余: {key_data.quota}, 需要: {usage}",
                "remaining_quota": key_data.quota
            }
        
        # 扣减额度
        key_data.quota -= usage
        key_data.last_used_at = datetime.now().isoformat()
        
        # 更新 Redis
        redis_key = self._get_redis_key(api_key)
        self.redis_client.set(redis_key, key_data.model_dump_json())
        

        
        return {
            "valid": True,
            "message": "验证成功",
            "remaining_quota": key_data.quota,
            "key_name": key_data.name
        }
    
    def update_apikey(self, api_key: str, is_active: Optional[bool] = None, 
                     quota: Optional[int] = None, name: Optional[str] = None,
                     description: Optional[str] = None) -> Optional[APIKey]:
        """
        更新 API Key 信息
        
        Args:
            api_key: API Key
            is_active: 是否激活
            quota: 新的额度（会累加到现有额度）
            name: 新的名称
            description: 新的描述
        
        Returns:
            更新后的 API Key 对象
        """
        key_data = self.get_apikey(api_key)
        
        if not key_data:
            return None
        
        if is_active is not None:
            key_data.is_active = is_active
            logger.info(f"🔧 更新API Key状态 - {key_data.name}: {'启用' if is_active else '禁用'}")
        
        if quota is not None:
            old_quota = key_data.quota
            key_data.quota += quota
            key_data.total_quota += quota
            logger.info(f"🔧 更新API Key额度 - {key_data.name}: {old_quota} -> {key_data.quota} (+{quota})")
        
        if name is not None:
            old_name = key_data.name
            key_data.name = name
            logger.info(f"🔧 更新API Key名称 - {old_name} -> {name}")
        
        if description is not None:
            key_data.description = description
        
        # 更新 Redis
        redis_key = self._get_redis_key(api_key)
        self.redis_client.set(redis_key, key_data.model_dump_json())
        
        return key_data
    
    def delete_apikey(self, api_key: str) -> bool:
        """
        删除 API Key
        
        Args:
            api_key: API Key
        
        Returns:
            是否删除成功
        """
        key_data = self.get_apikey(api_key)
        
        if not key_data:
            return False
        
        redis_key = self._get_redis_key(api_key)
        self.redis_client.delete(redis_key)
        self.redis_client.srem(self.key_list, api_key)
        
        logger.info(f"🗑️ 删除API Key - 名称: {key_data.name}")
        
        return True
    
    def get_usage_stats(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        获取 API Key 使用统计
        
        Args:
            api_key: API Key
        
        Returns:
            使用统计信息
        """
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
            "last_used_at": key_data.last_used_at
        }


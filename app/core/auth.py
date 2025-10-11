"""
Authentication and authorization
认证和授权模块
"""
from typing import Optional
from fastapi import Header, HTTPException, status
from fastapi.security import APIKeyHeader

from app.core.logger import logger
from app.services.apikey_service import APIKeyService


# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


class AuthService:
    """认证服务"""
    
    def __init__(self):
        self.apikey_service = APIKeyService()
    
    async def verify_api_key(self, x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
        """
        验证 API Key
        
        Args:
            x_api_key: 请求头中的 API Key
        
        Returns:
            验证通过的 API Key
        
        Raises:
            HTTPException: 验证失败时抛出
        """
        if not x_api_key:
            logger.warning("⚠️ 缺少 API Key")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="缺少 API Key，请在请求头中提供 X-API-Key",
                headers={"WWW-Authenticate": "ApiKey"}
            )
        
        # 验证 API Key 是否存在且有效
        key_data = self.apikey_service.get_apikey(x_api_key)
        
        if not key_data:
            logger.warning(f"⚠️ 无效的 API Key: {x_api_key[:10]}...")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的 API Key",
                headers={"WWW-Authenticate": "ApiKey"}
            )
        
        if not key_data.is_active:
            logger.warning(f"⚠️ API Key 已禁用: {key_data.name}")
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="API Key 已禁用"
            )
        
        logger.debug(f"✓ API Key 验证通过: {key_data.name}")
        
        return x_api_key
    
    async def verify_and_consume_quota(
        self, 
        usage: int,
        x_api_key: Optional[str] = Header(None, alias="X-API-Key")
    ) -> str:
        """
        验证 API Key 并检查额度（不消耗，实际消耗在请求成功后）
        
        Args:
            usage: 预计使用量
            x_api_key: API Key
        
        Returns:
            验证通过的 API Key
        """
        # 先验证 API Key
        api_key = await self.verify_api_key(x_api_key)
        
        # 检查额度是否足够
        key_data = self.apikey_service.get_apikey(api_key)
        
        if key_data and key_data.quota < usage:
            logger.warning(f"⚠️ API Key 额度不足: {key_data.name}, 剩余: {key_data.quota}, 需要: {usage}")
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"额度不足，剩余: {key_data.quota} 字符，需要: {usage} 字符"
            )
        
        return api_key


# 全局认证服务实例
auth_service = AuthService()


# 依赖函数
async def get_current_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")) -> str:
    """获取并验证当前 API Key（依赖注入用）"""
    return await auth_service.verify_api_key(x_api_key)


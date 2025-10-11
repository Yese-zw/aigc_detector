"""
API Key models
API密钥数据模型
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class APIKey(BaseModel):
    """API Key 数据模型"""
    key: str = Field(..., description="API密钥")
    name: str = Field(..., description="密钥名称")
    quota: int = Field(..., description="剩余额度（字符数）")
    total_quota: int = Field(..., description="总额度（字符数）")
    is_active: bool = Field(default=True, description="是否激活")
    created_at: str = Field(..., description="创建时间")
    last_used_at: Optional[str] = Field(None, description="最后使用时间")
    description: Optional[str] = Field(None, description="描述")


class APIKeyCreate(BaseModel):
    """创建 API Key 请求模型"""
    name: str = Field(..., description="密钥名称", min_length=1, max_length=100)
    quota: int = Field(..., description="总额度（字符数）", gt=0)
    description: Optional[str] = Field(None, description="描述", max_length=500)


class APIKeyResponse(BaseModel):
    """API Key 响应模型"""
    status: str = Field(..., description="响应状态")
    data: Optional[APIKey] = Field(None, description="API Key数据")
    message: Optional[str] = Field(None, description="响应消息")


class APIKeyListResponse(BaseModel):
    """API Key 列表响应模型"""
    status: str = Field(..., description="响应状态")
    data: list[APIKey] = Field(..., description="API Key列表")
    total: int = Field(..., description="总数量")


class APIKeyUsageUpdate(BaseModel):
    """API Key 使用情况更新"""
    key: str
    usage: int  # 本次使用的字符数
    timestamp: str


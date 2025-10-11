"""
Pydantic models for request/response validation
请求和响应数据模型
"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any


class AIDetectorRequest(BaseModel):
    """AI检测请求模型"""
    text: str = Field(..., description="待检测的文本内容", min_length=1)
    language: str = Field(..., description="文本语言类型：zh(中文) 或 en(英文)")
    
    @field_validator('language')
    @classmethod
    def validate_language(cls, v: str) -> str:
        """验证语言类型"""
        if v not in ['zh', 'en']:
            raise ValueError('语言类型仅支持 zh 或 en')
        return v
    
    @field_validator('text')
    @classmethod
    def validate_text(cls, v: str) -> str:
        """验证文本内容"""
        if not v.strip():
            raise ValueError('文本内容不能为空')
        return v.strip()

class AIRewrite(BaseModel):
    """AI请求模型"""
    text: str = Field(..., description="待检测的文本内容", min_length=1)
    combination_id: str = Field(..., description="文本语言类型：zh(中文) 或 en(英文)")

class QuotaInfo(BaseModel):
    """额度信息模型"""
    used: int = Field(..., description="本次使用的额度（字符数）")
    remaining: int = Field(..., description="剩余额度（字符数）")


class AIDetectorResponse(BaseModel):
    """AI检测响应模型"""
    status: str = Field(..., description="响应状态")
    result: Optional[Dict[str, Any]] = Field(None, description="检测结果")
    message: Optional[str] = Field(None, description="响应消息")
    quota_info: Optional[QuotaInfo] = Field(None, description="额度使用信息")


class HealthCheckResponse(BaseModel):
    """健康检查响应模型"""
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="应用版本")
    redis_connected: bool = Field(..., description="Redis连接状态")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    status: str = Field(default="error", description="响应状态")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(None, description="详细错误信息")


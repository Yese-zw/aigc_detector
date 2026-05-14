"""Shared request and response schemas."""

from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class AIDetectorRequest(BaseModel):
    text: str = Field(..., description="待检测的文本内容", min_length=1)
    language: str = Field(..., description="文本语言类型：zh(中文) 或 en(英文)")

    @field_validator("language")
    @classmethod
    def validate_language(cls, value: str) -> str:
        if value not in ["zh", "en"]:
            raise ValueError("语言类型仅支持 zh 或 en")
        return value

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("文本内容不能为空")
        return value.strip()


class AIRewrite(BaseModel):
    text: str = Field(..., description="待检测的文本内容", min_length=1)
    combination_id: str = Field(..., description="文本语言类型：zh(中文) 或 en(英文)")


class QuotaInfo(BaseModel):
    used: int = Field(..., description="本次使用的额度（字符数）")
    remaining: int = Field(..., description="剩余额度（字符数）")


class AIDetectorResponse(BaseModel):
    status: str = Field(..., description="响应状态")
    result: Optional[dict[str, Any]] = Field(None, description="检测结果")
    message: Optional[str] = Field(None, description="响应消息")
    quota_info: Optional[QuotaInfo] = Field(None, description="额度使用信息")


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="服务状态")
    version: str = Field(..., description="应用版本")
    redis_connected: bool = Field(..., description="Redis连接状态")


class ErrorResponse(BaseModel):
    status: str = Field(default="error", description="响应状态")
    message: str = Field(..., description="错误消息")
    detail: Optional[str] = Field(None, description="详细错误信息")

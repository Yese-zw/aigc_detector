"""
Configuration management
配置管理模块
"""
import os
from typing import List, Tuple
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """应用配置"""
    
    # 应用信息
    APP_NAME: str = "AIGC Detector API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI检测服务"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4  # Uvicorn worker进程数
    RELOAD: bool = False  # 是否启用热重载（开发环境设为True）
    
    # 后台管理密码
    ADMIN_PASSWORD: str = "zw123"
    
    # Redis配置
    REDIS_HOST: str = "124.221.97.191"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "960777365"
    REDIS_DB: int = 3
    REDIS_DECODE_RESPONSES: bool = True
    
    # 登录态配置
    AUTH_EXPIRE_SECONDS: int = 7200 * 3  # 6小时
    REDIS_AUTH_KEY: str = "ai_detector_auth"
    
    # 邮件通知配置
    MAIL_SERVER: str = "smtp.163.com"
    MAIL_PORT: int = 465
    MAIL_USERNAME: str = "aipaper2025@163.com"  # 发件人邮箱账号
    MAIL_PASSWORD: str = "NRwSx36YhWfpkL4q"  # 发件人邮箱授权码
    MAIL_FROM: str = "aipaper2025@163.com"  # 发件人地址
    MAIL_TO: List[str] = ['1762389546@qq.com']  # 接收通知的邮箱列表

    # 连续通知冷却时间（秒，防止短时间发送大量邮件）
    MAIL_COOLDOWN_SECONDS: int = 3600
    
    # AI检测服务配置
    AI_DETECTOR_BASE_URL: str = "https://xrzbk.lanbeike.online"
    AI_DETECTOR_TIMEOUT: int = 1500000
    LOGIN_TIMEOUT: int = 10
    
    # 上游登录凭据
    UPSTREAM_EMAIL: str = "1762389546@qq.com"
    UPSTREAM_PASSWORD: str = "xrz1762389546"
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/ai_detector.log"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_BACKUP_COUNT: int = 30  # 保留最近30天的日志
    
    # CORS配置
    CORS_ORIGINS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: List[str] = ["*"]
    CORS_ALLOW_HEADERS: List[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings()


# 导出配置实例
settings = get_settings()


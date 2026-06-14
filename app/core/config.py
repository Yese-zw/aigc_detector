"""Application configuration."""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "AIGC Detector API"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "AI检测服务"

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    RELOAD: bool = False

    ADMIN_PASSWORD: str = "zw123"

    REDIS_HOST: str = "43.142.181.147"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str = "960777365"
    REDIS_DB: int = 3
    REDIS_DECODE_RESPONSES: bool = True

    AUTH_EXPIRE_SECONDS: int = 7200 * 3
    REDIS_AUTH_KEY: str = "ai_detector_auth"

    MAIL_SERVER: str = "smtp.163.com"
    MAIL_PORT: int = 465
    MAIL_USERNAME: str = "aipaper2025@163.com"
    MAIL_PASSWORD: str = "NRwSx36YhWfpkL4q"
    MAIL_FROM: str = "aipaper2025@163.com"
    MAIL_TO: List[str] = ["1762389546@qq.com"]
    MAIL_COOLDOWN_SECONDS: int = 3600

    AI_DETECTOR_BASE_URL: str = "https://ai.lanbeike.online"
    AI_DETECTOR_TIMEOUT: int = 1500000
    LOGIN_TIMEOUT: int = 120

    UPSTREAM_EMAIL: str = "1762389546@qq.com"
    UPSTREAM_PASSWORD: str = "xrz1762389546"

    LOG_LEVEL: str = "INFO"
    LOG_FILE: str = "logs/ai_detector.log"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    LOG_BACKUP_COUNT: int = 30

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
    return Settings()


settings = get_settings()

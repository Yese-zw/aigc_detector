"""
Logging configuration
日志配置模块
"""
import logging
import os
from logging.handlers import TimedRotatingFileHandler
from app.core.config import settings


def setup_logger() -> logging.Logger:
    """配置并返回日志记录器"""
    
    # 创建日志目录
    log_dir = os.path.dirname(settings.LOG_FILE)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建logger
    logger = logging.getLogger("aigc_detector")
    logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # 避免重复添加handler
    if logger.handlers:
        return logger
    
    # 创建格式化器
    formatter = logging.Formatter(settings.LOG_FORMAT)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器（按天轮转）
    file_handler = TimedRotatingFileHandler(
        settings.LOG_FILE,
        when='midnight',  # 每天午夜轮转
        interval=1,  # 间隔1天
        backupCount=settings.LOG_BACKUP_COUNT,  # 保留最近N天的日志
        encoding='utf-8',
        utc=False  # 使用本地时间
    )
    # 设置日志文件名后缀格式（例如：ai_detector.log.2024-10-12）
    file_handler.suffix = "%Y-%m-%d"
    file_handler.setLevel(getattr(logging, settings.LOG_LEVEL))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger


# 导出全局logger实例
logger = setup_logger()


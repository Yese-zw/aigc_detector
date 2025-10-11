#!/usr/bin/env python
"""
应用启动脚本
Quick start script for the application
"""
import uvicorn
from app.core.config import settings

if __name__ == "__main__":
    uvicorn.run(
        app="app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        workers=settings.WORKERS,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower()
    )


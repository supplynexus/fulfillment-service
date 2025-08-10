"""
日志配置模块
"""
import os
import sys
import logging
import structlog
from pathlib import Path
from app.core.config import settings


def setup_logging():
    """配置结构化日志"""
    
    # 创建日志目录
    log_dir = Path("/app/logs")
    if not log_dir.exists():
        log_dir.mkdir(parents=True, exist_ok=True)
    
    # 配置标准库日志
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            # 控制台输出
            logging.StreamHandler(sys.stdout),
            # 文件输出
            logging.FileHandler(log_dir / "app.log"),
        ]
    )
    
    # 配置 structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            # 根据环境选择输出格式
            structlog.processors.JSONRenderer() if settings.ENVIRONMENT in ["prod", "stg"] 
            else structlog.dev.ConsoleRenderer()
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None):
    """获取日志记录器"""
    return structlog.get_logger(name)

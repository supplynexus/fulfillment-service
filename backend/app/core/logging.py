"""
日志配置模块
"""
import os
import sys
import logging
import structlog
import uuid
from pathlib import Path
from typing import Optional
from contextvars import ContextVar
from app.core.config import settings

# 请求ID上下文变量
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


def get_request_id() -> Optional[str]:
    """获取当前请求的ID"""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """设置当前请求的ID"""
    request_id_var.set(request_id)


def generate_request_id() -> str:
    """生成新的请求ID"""
    return str(uuid.uuid4())


def setup_logging():
    """配置结构化日志"""
    
    # 创建日志目录 - 根据环境选择路径
    if settings.ENVIRONMENT in ["local", "development"]:
        # 本地开发环境使用相对路径
        log_dir = Path("logs-local")
    elif settings.ENVIRONMENT == "dev":
        # 开发服务器环境
        log_dir = Path("logs-dev")
    else:
        # 生产环境使用绝对路径
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
    
    # 自定义处理器：添加请求ID到日志记录
    def add_request_id(logger, method_name, event_dict):
        """添加请求ID到日志记录"""
        request_id = get_request_id()
        if request_id:
            event_dict['request_id'] = request_id
        return event_dict
    
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
            add_request_id,  # 添加请求ID
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


class RequestLogger:
    """请求日志记录器，自动包含请求ID"""
    
    def __init__(self, name: str = None):
        self.logger = get_logger(name)
    
    def info(self, message: str, **kwargs):
        """记录信息日志"""
        try:
            self.logger.info(message, **kwargs)
        except Exception as e:
            # 如果结构化日志失败，回退到简单日志
            self.logger.info(f"{message} - {kwargs}")
    
    def error(self, message: str, **kwargs):
        """记录错误日志"""
        try:
            self.logger.error(message, **kwargs)
        except Exception as e:
            # 如果结构化日志失败，回退到简单日志
            self.logger.error(f"{message} - {kwargs}")
    
    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        try:
            self.logger.warning(message, **kwargs)
        except Exception as e:
            # 如果结构化日志失败，回退到简单日志
            self.logger.warning(f"{message} - {kwargs}")
    
    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        try:
            self.logger.debug(message, **kwargs)
        except Exception as e:
            # 如果结构化日志失败，回退到简单日志
            self.logger.debug(f"{message} - {kwargs}")
    
    def exception(self, message: str, **kwargs):
        """记录异常日志（包含堆栈跟踪）"""
        try:
            self.logger.exception(message, **kwargs)
        except Exception as e:
            # 如果结构化日志失败，回退到简单日志
            self.logger.exception(f"{message} - {kwargs}")

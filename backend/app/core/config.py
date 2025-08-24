"""
应用配置设置
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用设置"""
    
    # 数据库配置
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://localhost:5433/supplynexus")
    
    # Redis 配置
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")
    
    # Shopify API 配置（多租户系统 - 每个租户的配置存储在数据库中）
    # 注意：不要使用环境变量配置 Shopify 凭据
    
    # 安全配置
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "dev-webhook-secret-change-in-prod")
    
    # System API Key for system-level endpoints
    SYSTEM_API_KEY: str = os.getenv("SYSTEM_API_KEY", "system-api-key-change-in-prod")
    
    # 应用配置
    ENVIRONMENT: str = "dev"
    # 开发环境：允许所有来源和主机
    ALLOWED_ORIGINS: str = "*"
    ALLOWED_HOSTS: str = "*"
    
    # API 配置
    API_V1_STR: str = "/api/v1"
    
    # Sentry 配置（可选）
    SENTRY_DSN: Optional[str] = os.getenv("SENTRY_DSN")
    
    # 健康检查配置
    HEALTH_CHECK_API_KEY: Optional[str] = os.getenv("HEALTH_CHECK_API_KEY")  # 必须配置，无缺省值
    HEALTH_CHECK_RATE_LIMIT: int = int(os.getenv("HEALTH_CHECK_RATE_LIMIT", "10"))  # 每分钟请求数
    HEALTH_CHECK_RATE_WINDOW: int = int(os.getenv("HEALTH_CHECK_RATE_WINDOW", "60"))  # 时间窗口（秒）
    
    # Hashids 配置
    HASHIDS_SALT: str = os.getenv("HASHIDS_SALT", "dev-hashids-salt-change-in-prod")
    HASHIDS_MIN_LENGTH: int = int(os.getenv("HASHIDS_MIN_LENGTH", "8"))
    
    class Config:
        # 支持从ENV_FILE环境变量读取配置文件
        # 如果没有指定ENV_FILE，则按优先级查找：
        # 1. .env.local (本地开发)
        # 2. ../deployment/environments/env.local (统一配置)
        # 3. .env (默认)
        env_file = os.getenv("ENV_FILE") or ".env.local"
        extra = "ignore"  # Ignore extra fields instead of raising validation error

    def get_env_file_path(self) -> str:
        """获取当前使用的环境文件绝对路径"""
        env_file = os.getenv("ENV_FILE") or ".env.local"
        
        # 如果是绝对路径，直接返回
        if os.path.isabs(env_file):
            return env_file
        
        # 获取当前工作目录
        current_dir = os.getcwd()
        
        # 尝试在当前目录查找
        local_path = os.path.join(current_dir, env_file)
        if os.path.exists(local_path):
            return os.path.abspath(local_path)
        
        # 尝试在上级目录的 deployment/environments/backend 查找
        deployment_path = os.path.join(current_dir, "..", "deployment", "environments", "backend", env_file)
        if os.path.exists(deployment_path):
            return os.path.abspath(deployment_path)
        
        # 如果都找不到，返回预期的路径
        return os.path.abspath(local_path)

    def get_important_env_vars(self) -> dict:
        """获取重要的环境变量（显示完整值）"""
        return {
            "ENVIRONMENT": self.ENVIRONMENT,
            "DATABASE_URL": self.DATABASE_URL,
            "REDIS_URL": self.REDIS_URL,
            "CELERY_BROKER_URL": self.CELERY_BROKER_URL,
            "CELERY_RESULT_BACKEND": self.CELERY_RESULT_BACKEND,
            "WEBHOOK_SECRET": self.WEBHOOK_SECRET,
            "HEALTH_CHECK_API_KEY": self.HEALTH_CHECK_API_KEY,
            "HEALTH_CHECK_RATE_LIMIT": self.HEALTH_CHECK_RATE_LIMIT,
            "HEALTH_CHECK_RATE_WINDOW": self.HEALTH_CHECK_RATE_WINDOW,
            "SYSTEM_API_KEY": self.SYSTEM_API_KEY,
            "HASHIDS_SALT": self.HASHIDS_SALT,
            "HASHIDS_MIN_LENGTH": self.HASHIDS_MIN_LENGTH,
            "ALLOWED_ORIGINS": self.ALLOWED_ORIGINS,
            "ALLOWED_HOSTS": self.ALLOWED_HOSTS,
            "API_V1_STR": self.API_V1_STR,
            "BACKEND_PORT": getattr(self, 'BACKEND_PORT', 8000),
        }


settings = Settings()
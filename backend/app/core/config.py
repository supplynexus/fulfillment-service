"""
应用配置设置
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用设置"""
    
    # 数据库配置
    DATABASE_URL: str = "postgresql+asyncpg://supplynexus_admin:IVzrm2bKlWyxWzhU3KVJUOdwU6IEwG32@localhost:5433/supplynexus"
    
    # Redis 配置
    REDIS_URL: str = "redis://localhost:6380/0"
    CELERY_BROKER_URL: str = "redis://localhost:6380/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6380/2"
    
    # Shopify API 配置
    SHOPIFY_SHOP_NAME: Optional[str] = os.getenv("SHOPIFY_SHOP_NAME")
    SHOPIFY_ACCESS_TOKEN: Optional[str] = os.getenv("SHOPIFY_ACCESS_TOKEN")
    SHOPIFY_API_KEY: Optional[str] = os.getenv("SHOPIFY_API_KEY")
    SHOPIFY_API_SECRET: Optional[str] = os.getenv("SHOPIFY_API_SECRET")
    
    # Printify API 配置
    PRINTIFY_API_TOKEN: Optional[str] = os.getenv("PRINTIFY_API_TOKEN")
    
    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-jwt-secret-key-change-in-prod")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "dev-webhook-secret-change-in-prod")
    
    # 应用配置
    ENVIRONMENT: str = "dev"
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:3001"
    ALLOWED_HOSTS: str = "localhost,127.0.0.1"
    
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
    
    # Swagger 调试模式配置
    SWAGGER_DEBUG_MODE: bool = os.getenv("SWAGGER_DEBUG_MODE", "false").lower() == "true"
    
    class Config:
        env_file = os.getenv("ENV_FILE", ".env")
        extra = "ignore"  # Ignore extra fields instead of raising validation error


settings = Settings()
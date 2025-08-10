"""
SupplyNexus Fulfillment Service - Main FastAPI Application
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.utils import get_openapi
import structlog
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from datetime import datetime

from app.core.config import settings
from app.core.database import init_db
from app.api.v1.api import api_router

# Configure structured logging
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
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    wrapper_class=structlog.stdlib.BoundLogger,
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()

# Initialize Sentry for error tracking
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        integrations=[
            FastApiIntegration(auto_enabling_integrations=False),
            SqlalchemyIntegration(),
        ],
        environment=settings.ENVIRONMENT,
        traces_sample_rate=0.1,
    )

# Create FastAPI app
app = FastAPI(
    title="SupplyNexus Fulfillment Service",
    description="Shopify to Printify Order Fulfillment Automation",
    version="1.0.0",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
)

# Convert string configurations to lists
allowed_hosts = settings.ALLOWED_HOSTS.split(",") if isinstance(settings.ALLOWED_HOSTS, str) else settings.ALLOWED_HOSTS
allowed_origins = settings.ALLOWED_ORIGINS.split(",") if isinstance(settings.ALLOWED_ORIGINS, str) else settings.ALLOWED_ORIGINS

# Security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=allowed_hosts
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors"""
    logger.error(
        "Unhandled exception occurred",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error_id": f"error_{hash(str(exc))}"
        }
    )


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting SupplyNexus Fulfillment Service")
    # Temporarily skip database initialization for quick start
    # await init_db()
    logger.info("Application started successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on application shutdown"""
    logger.info("Shutting down SupplyNexus Fulfillment Service")


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "SupplyNexus Fulfillment Service",
        "version": "1.0.0",
        "status": "healthy"
    }


# Health check endpoints are now handled by the dedicated health router
# See /api/v1/health for detailed health checks

def custom_openapi():
    """自定义 OpenAPI 配置，添加 API Key 安全模式"""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # 确保 components 存在
    if "components" not in openapi_schema:
        openapi_schema["components"] = {}
    
    # 添加 API Key 安全模式
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API Key for health check endpoints"
        }
    }
    
    # 为健康检查端点添加安全要求
    for path in openapi_schema["paths"]:
        if path.startswith("/api/v1/health/") and path != "/api/v1/health":
            if "get" in openapi_schema["paths"][path]:
                openapi_schema["paths"][path]["get"]["security"] = [{"ApiKeyAuth": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_config=None  # Use structlog instead
    )

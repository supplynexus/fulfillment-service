"""
Health check endpoints
"""

from datetime import datetime
from fastapi import APIRouter, Depends, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import structlog

from app.core.health_auth import require_health_check_auth

# 创建安全模式
security = HTTPBearer(auto_error=False)

logger = structlog.get_logger()

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint - 基本健康检查，无需认证"""
    return {
        "status": "healthy",
        "service": "fulfillment-service",
        "version": "1.0.0"
    }


@router.get(
    "/health/db", 
    dependencies=[Depends(require_health_check_auth)],
    responses={
        200: {"description": "Database is healthy"},
        401: {"description": "Invalid API key"},
        503: {"description": "Database is unhealthy"}
    }
)
async def health_check_db():
    """Database health check endpoint"""
    try:
        from app.core.database import get_async_db
        from sqlalchemy import text
        
        # Get database session
        async for db in get_async_db():
            # Execute a simple query to test database connection
            result = await db.execute(text("SELECT 1"))
            row = result.fetchone()
            await db.close()
            break
        
        return {
            "status": "healthy",
            "service": "database",
            "message": "Database connection successful"
        }
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "database",
                "message": f"Database connection failed: {str(e)}"
            }
        )


@router.get(
    "/health/redis", 
    dependencies=[Depends(require_health_check_auth)],
    responses={
        200: {"description": "Redis is healthy"},
        401: {"description": "Invalid API key"},
        503: {"description": "Redis is unhealthy"}
    }
)
async def health_check_redis():
    """Redis health check endpoint"""
    try:
        import redis.asyncio as redis
        from app.core.config import settings
        
        # Parse Redis URL
        redis_url = settings.REDIS_URL
        if redis_url.startswith("redis://"):
            redis_url = redis_url[8:]  # Remove redis:// prefix
        
        # Extract password if present
        password = None
        if "@" in redis_url:
            auth_part, rest = redis_url.split("@", 1)
            if ":" in auth_part:
                password = auth_part.split(":", 1)[1]
            redis_url = rest
        
        # Extract host and port
        if ":" in redis_url:
            host_port, db_part = redis_url.split("/", 1)
            host, port = host_port.split(":")
            port = int(port)
        else:
            host = redis_url
            port = 6379
        
        # Create Redis client and test connection
        r = redis.Redis(host=host, port=port, password=password, decode_responses=True)
        await r.ping()
        await r.close()
        
        return {
            "status": "healthy",
            "service": "redis",
            "message": "Redis connection successful"
        }
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "redis",
                "message": f"Redis connection failed: {str(e)}"
            }
        )


@router.get(
    "/health/full", 
    dependencies=[Depends(require_health_check_auth)],
    responses={
        200: {"description": "All services are healthy"},
        401: {"description": "Invalid API key"},
        503: {"description": "One or more services are unhealthy"}
    }
)
async def health_check_full():
    """Full health check endpoint - checks all services"""
    health_status = {
        "status": "healthy",
        "service": "fulfillment-service",
        "version": "1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }
    
    # Check database
    try:
        from app.core.database import get_async_db
        from sqlalchemy import text
        
        async for db in get_async_db():
            result = await db.execute(text("SELECT 1"))
            row = result.fetchone()
            await db.close()
            break
        
        health_status["checks"]["database"] = {
            "status": "healthy",
            "message": "Database connection successful"
        }
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "message": f"Database connection failed: {str(e)}"
        }
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        import redis.asyncio as redis
        from app.core.config import settings
        
        redis_url = settings.REDIS_URL
        if redis_url.startswith("redis://"):
            redis_url = redis_url[8:]
        
        password = None
        if "@" in redis_url:
            auth_part, rest = redis_url.split("@", 1)
            if ":" in auth_part:
                password = auth_part.split(":", 1)[1]
            redis_url = rest
        
        if ":" in redis_url:
            host_port, db_part = redis_url.split("/", 1)
            host, port = host_port.split(":")
            port = int(port)
        else:
            host = redis_url
            port = 6379
        
        r = redis.Redis(host=host, port=port, password=password, decode_responses=True)
        await r.ping()
        await r.close()
        
        health_status["checks"]["redis"] = {
            "status": "healthy",
            "message": "Redis connection successful"
        }
    except Exception as e:
        health_status["checks"]["redis"] = {
            "status": "unhealthy",
            "message": f"Redis connection failed: {str(e)}"
        }
        health_status["status"] = "unhealthy"
    
    # Return appropriate status code
    status_code = 200 if health_status["status"] == "healthy" else 503
    return JSONResponse(
        status_code=status_code,
        content=health_status
    )

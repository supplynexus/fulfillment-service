"""
Dashboard and analytics endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.core.database import get_async_db
from app.services.analytics_service import AnalyticsService

router = APIRouter()


@router.get("/stats")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get dashboard statistics
    """
    analytics_service = AnalyticsService(db)
    stats = await analytics_service.get_dashboard_stats()
    return stats


@router.get("/orders/recent")
async def get_recent_orders(
    limit: int = 10,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get recent orders for dashboard
    """
    analytics_service = AnalyticsService(db)
    orders = await analytics_service.get_recent_orders(limit=limit)
    return orders


@router.get("/metrics")
async def get_metrics(
    days: int = 30,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get metrics for specified period
    """
    analytics_service = AnalyticsService(db)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    metrics = await analytics_service.get_metrics(
        start_date=start_date,
        end_date=end_date
    )
    return metrics

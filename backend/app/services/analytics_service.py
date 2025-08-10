"""
Analytics service for dashboard metrics and insights
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.order import Order

logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for generating analytics and dashboard metrics"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_dashboard_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get dashboard metrics for the specified period"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get total orders count
            total_orders_result = await self.db.execute(
                select(func.count(Order.id)).where(
                    Order.created_at >= start_date
                )
            )
            total_orders = total_orders_result.scalar() or 0
            
            # Get total revenue
            total_revenue_result = await self.db.execute(
                select(func.sum(Order.total_price)).where(
                    Order.created_at >= start_date
                )
            )
            total_revenue = float(total_revenue_result.scalar() or 0)
            
            # Get orders by status
            fulfilled_orders_result = await self.db.execute(
                select(func.count(Order.id)).where(
                    Order.created_at >= start_date,
                    Order.fulfillment_status == "fulfilled"
                )
            )
            fulfilled_orders = fulfilled_orders_result.scalar() or 0
            
            pending_orders_result = await self.db.execute(
                select(func.count(Order.id)).where(
                    Order.created_at >= start_date,
                    Order.fulfillment_status.in_(["pending", "partial"])
                )
            )
            pending_orders = pending_orders_result.scalar() or 0
            
            return {
                "total_orders": total_orders,
                "total_revenue": total_revenue,
                "fulfilled_orders": fulfilled_orders,
                "pending_orders": pending_orders,
                "fulfillment_rate": (fulfilled_orders / total_orders * 100) if total_orders > 0 else 0,
                "period_days": days
            }
            
        except Exception as e:
            logger.error(f"Failed to get dashboard metrics: {e}")
            return {
                "total_orders": 0,
                "total_revenue": 0.0,
                "fulfilled_orders": 0,
                "pending_orders": 0,
                "fulfillment_rate": 0.0,
                "period_days": days
            }
    
    async def get_order_trends(self, days: int = 30) -> List[Dict[str, Any]]:
        """Get order trends for the specified period"""
        try:
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get daily order counts
            daily_orders = await self.db.execute(
                select(
                    func.date(Order.created_at).label('date'),
                    func.count(Order.id).label('count'),
                    func.sum(Order.total_price).label('revenue')
                ).where(
                    Order.created_at >= start_date
                ).group_by(
                    func.date(Order.created_at)
                ).order_by(
                    func.date(Order.created_at)
                )
            )
            
            return [
                {
                    "date": str(row.date),
                    "orders": row.count,
                    "revenue": float(row.revenue or 0)
                }
                for row in daily_orders
            ]
            
        except Exception as e:
            logger.error(f"Failed to get order trends: {e}")
            return []

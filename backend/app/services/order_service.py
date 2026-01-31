"""
Order service for mixed model approach
"""

from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import joinedload

from app.models.order import Order, OrderStatus
from app.core.logging import get_logger

logger = get_logger(__name__)


class OrderService:
    """Order service for mixed model operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_orders(
        self, 
        tenant_id: int, 
        limit: int = 50, 
        offset: int = 0,
        status: Optional[str] = None,
        external_system_id: Optional[int] = None
    ) -> List[Order]:
        """Get orders with filtering and pagination"""
        try:
            query = select(Order).where(Order.tenant_id == tenant_id)
            
            # Apply filters
            if status:
                query = query.where(Order.status == status)
            if external_system_id:
                query = query.where(Order.external_system_id == external_system_id)
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            # Execute query
            result = await self.db.execute(query)
            orders = result.scalars().all()
            
            logger.info(f"Retrieved {len(orders)} orders for tenant {tenant_id}")
            return orders
            
        except Exception as e:
            logger.error(f"Error getting orders for tenant {tenant_id}: {e}")
            return []
    
    async def get_order_by_id(self, order_id: int, tenant_id: int) -> Optional[Order]:
        """Get order by ID with tenant validation"""
        try:
            result = await self.db.execute(
                select(Order).where(
                    and_(
                        Order.id == order_id,
                        Order.tenant_id == tenant_id
                    )
                )
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting order {order_id}: {e}")
            return None
    
    async def get_order_by_external_id(
        self, 
        external_order_id: str, 
        tenant_id: int,
        external_system_id: Optional[int] = None
    ) -> Optional[Order]:
        """Get order by external system ID"""
        try:
            query = select(Order).where(
                and_(
                    Order.external_order_id == external_order_id,
                    Order.tenant_id == tenant_id
                )
            )
            
            if external_system_id:
                query = query.where(Order.external_system_id == external_system_id)
            
            result = await self.db.execute(query)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting order by external ID {external_order_id}: {e}")
            return None
    
    async def create_order(self, order: Order) -> Optional[Order]:
        """Create a new order"""
        try:
            self.db.add(order)
            await self.db.commit()
            await self.db.refresh(order)
            
            logger.info(f"Created order {order.id} for tenant {order.tenant_id}")
            return order
            
        except Exception as e:
            logger.error(f"Error creating order: {e}")
            await self.db.rollback()
            return None
    
    async def update_order_status(
        self, 
        order_id: int, 
        tenant_id: int, 
        status: str
    ) -> bool:
        """Update order status"""
        try:
            result = await self.db.execute(
                select(Order).where(
                    and_(
                        Order.id == order_id,
                        Order.tenant_id == tenant_id
                    )
                )
            )
            order = result.scalar_one_or_none()
            
            if not order:
                logger.warning(f"Order {order_id} not found for tenant {tenant_id}")
                return False
            
            order.status = status
            await self.db.commit()
            
            logger.info(f"Updated order {order_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating order {order_id} status: {e}")
            await self.db.rollback()
            return False
    
    async def get_shopify_orders(
        self, 
        tenant_id: int, 
        limit: int = 50,
        offset: int = 0
    ) -> List[Order]:
        """Get Shopify orders specifically"""
        try:
            result = await self.db.execute(
                select(Order).where(
                    and_(
                        Order.tenant_id == tenant_id,
                        Order.external_system_id == 1,  # Shopify system ID
                        Order.shopify_raw_data.isnot(None)
                    )
                ).offset(offset).limit(limit)
            )
            
            orders = result.scalars().all()
            logger.info(f"Retrieved {len(orders)} Shopify orders for tenant {tenant_id}")
            return orders
            
        except Exception as e:
            logger.error(f"Error getting Shopify orders for tenant {tenant_id}: {e}")
            return []
    
    async def get_order_statistics(self, tenant_id: int) -> Dict[str, Any]:
        """Get order statistics for tenant"""
        try:
            # Get total orders
            total_result = await self.db.execute(
                select(Order).where(Order.tenant_id == tenant_id)
            )
            total_orders = len(total_result.scalars().all())
            
            # Get orders by status
            status_stats = {}
            for status in OrderStatus:
                result = await self.db.execute(
                    select(Order).where(
                        and_(
                            Order.tenant_id == tenant_id,
                            Order.status == status.value
                        )
                    )
                )
                status_stats[status.value] = len(result.scalars().all())
            
            # Get Shopify orders count
            shopify_result = await self.db.execute(
                select(Order).where(
                    and_(
                        Order.tenant_id == tenant_id,
                        Order.external_system_id == 1
                    )
                )
            )
            shopify_orders = len(shopify_result.scalars().all())
            
            return {
                "total_orders": total_orders,
                "status_breakdown": status_stats,
                "shopify_orders": shopify_orders
            }
            
        except Exception as e:
            logger.error(f"Error getting order statistics for tenant {tenant_id}: {e}")
            return {
                "total_orders": 0,
                "status_breakdown": {},
                "shopify_orders": 0
            }

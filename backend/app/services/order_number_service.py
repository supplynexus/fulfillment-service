"""
订单编号生成服务
为不同类型的订单生成人类可读的编号
"""

from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.logging import get_logger

logger = get_logger(__name__)


class OrderNumberService:
    """订单编号生成服务"""
    
    @staticmethod
    async def generate_order_number(
        db: AsyncSession, 
        tenant_id: int, 
        order_type: str = "ORD"
    ) -> str:
        """
        生成订单编号
        
        Args:
            db: 数据库会话
            tenant_id: 租户ID
            order_type: 订单类型前缀 (ORD, SCM, PAY, INV)
            
        Returns:
            格式化的订单编号，如 ORD-2025-001
        """
        try:
            logger.info(f"🔍 开始生成订单编号: tenant_id={tenant_id}, order_type={order_type}")
            
            # 获取当前年份
            current_year = datetime.now().year
            
            # 查询该租户当年该类型订单的最大编号
            from app.models.order import Order
            
            # 构建查询条件：租户ID + 订单编号前缀匹配
            prefix_pattern = f"{order_type}-{current_year}-%"
            
            # 查询该租户当年该类型订单的最大编号
            query = select(Order.order_number).where(
                Order.tenant_id == tenant_id,
                Order.order_number.like(prefix_pattern)
            ).order_by(Order.order_number.desc())
            
            result = await db.execute(query)
            max_order_number = result.scalar()
            
            # 生成新编号
            if max_order_number:
                # 提取编号中的数字部分
                try:
                    # 格式: ORD-2025-001 -> 提取 001
                    number_part = max_order_number.split('-')[-1]
                    next_number = int(number_part) + 1
                except (ValueError, IndexError):
                    # 如果解析失败，从1开始
                    next_number = 1
            else:
                # 没有找到匹配的编号，从1开始
                next_number = 1
            
            # 格式化编号：ORD-2025-001
            new_order_number = f"{order_type}-{current_year}-{next_number:03d}"
            
            logger.info(f"✅ 订单编号生成成功: {new_order_number}")
            return new_order_number
            
        except Exception as e:
            logger.error(f"❌ 订单编号生成失败: {str(e)}")
            # 降级方案：使用时间戳
            timestamp = int(datetime.now().timestamp())
            fallback_number = f"{order_type}-{current_year}-{timestamp % 1000:03d}"
            logger.warning(f"⚠️ 使用降级方案: {fallback_number}")
            return fallback_number
    
    @staticmethod
    async def generate_scm_order_number(db: AsyncSession, tenant_id: int) -> str:
        """生成 SCM 订单编号"""
        try:
            logger.info(f"🔍 开始生成SCM订单编号: tenant_id={tenant_id}")
            
            # 获取当前年份
            current_year = datetime.now().year
            
            # 查询该租户当年SCM订单的最大编号
            from app.models.scm_order import SCMOrder
            
            # 构建查询条件：租户ID + 订单编号前缀匹配
            prefix_pattern = f"SCM-{current_year}-%"
            
            # 查询该租户当年SCM订单的最大编号
            query = select(SCMOrder.scm_order_number).where(
                SCMOrder.tenant_id == tenant_id,
                SCMOrder.scm_order_number.like(prefix_pattern)
            ).order_by(SCMOrder.scm_order_number.desc())
            
            result = await db.execute(query)
            max_order_number = result.scalar()
            
            # 生成新编号
            if max_order_number:
                # 提取编号中的数字部分
                try:
                    # 格式: SCM-2025-001 -> 提取 001
                    number_part = max_order_number.split('-')[-1]
                    next_number = int(number_part) + 1
                except (ValueError, IndexError):
                    # 如果解析失败，从1开始
                    next_number = 1
            else:
                # 没有找到匹配的编号，从1开始
                next_number = 1
            
            # 格式化编号：SCM-2025-001
            new_order_number = f"SCM-{current_year}-{next_number:03d}"
            
            logger.info(f"✅ SCM订单编号生成成功: {new_order_number}")
            return new_order_number
            
        except Exception as e:
            logger.error(f"❌ SCM订单编号生成失败: {str(e)}")
            # 降级方案：使用时间戳
            timestamp = int(datetime.now().timestamp())
            fallback_number = f"SCM-{current_year}-{timestamp % 1000:03d}"
            logger.warning(f"⚠️ 使用降级方案: {fallback_number}")
            return fallback_number
    
    @staticmethod
    async def generate_payment_number(db: AsyncSession, tenant_id: int) -> str:
        """生成支付编号"""
        return await OrderNumberService.generate_order_number(db, tenant_id, "PAY")
    
    @staticmethod
    async def generate_invoice_number(db: AsyncSession, tenant_id: int) -> str:
        """生成发票编号"""
        return await OrderNumberService.generate_order_number(db, tenant_id, "INV")
    
    @staticmethod
    def generate_order_number_sync(db, tenant_id: int, order_type: str = "ORD") -> str:
        """
        生成订单编号（同步版本，用于Celery任务）
        
        Args:
            db: 同步数据库会话
            tenant_id: 租户ID
            order_type: 订单类型前缀 (ORD, SCM, PAY, INV)
            
        Returns:
            格式化的订单编号，如 ORD-2025-001
        """
        try:
            logger.info(f"🔍 开始生成订单编号: tenant_id={tenant_id}, order_type={order_type}")
            
            # 获取当前年份
            current_year = datetime.now().year
            
            # 查询该租户当年该类型订单的最大编号
            from app.models.order import Order
            
            # 构建查询条件：租户ID + 订单编号前缀匹配
            prefix_pattern = f"{order_type}-{current_year}-%"
            
            # 查询该租户当年该类型订单的最大编号
            max_order_number_result = db.query(Order.order_number).filter(
                Order.tenant_id == tenant_id,
                Order.order_number.like(prefix_pattern)
            ).order_by(Order.order_number.desc()).first()
            
            # 生成新编号
            if max_order_number_result:
                # max_order_number_result 是一个标量值（字符串），不是元组
                max_order_number = max_order_number_result
                # 提取编号中的数字部分
                try:
                    # 格式: ORD-2025-001 -> 提取 001
                    number_part = max_order_number.split('-')[-1]
                    next_number = int(number_part) + 1
                except (ValueError, IndexError):
                    # 如果解析失败，从1开始
                    next_number = 1
            else:
                # 没有找到匹配的编号，从1开始
                next_number = 1
            
            # 格式化编号：ORD-2025-001
            new_order_number = f"{order_type}-{current_year}-{next_number:03d}"
            
            logger.info(f"✅ 订单编号生成成功: {new_order_number}")
            return new_order_number
            
        except Exception as e:
            logger.error(f"❌ 订单编号生成失败: {str(e)}")
            # 降级方案：使用时间戳
            timestamp = int(datetime.now().timestamp())
            fallback_number = f"{order_type}-{current_year}-{timestamp % 1000:03d}"
            logger.warning(f"⚠️ 使用降级方案: {fallback_number}")
            return fallback_number
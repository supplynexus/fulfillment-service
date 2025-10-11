"""
订单状态生命周期管理服务
提供完整的订单状态生命周期管理、状态转换验证和状态历史记录
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.order import Order, OrderStatus
from app.models.scm_order import SCMOrder, SCMOrderStatus
from app.models.shopify_order import ShopifyOrder

logger = get_logger(__name__)


class OrderLifecycleStage(Enum):
    """订单生命周期阶段"""
    CREATED = "created"           # 订单创建
    CONFIRMED = "confirmed"       # 订单确认
    PROCESSING = "processing"     # 处理中
    FULFILLED = "fulfilled"       # 已完成
    SHIPPED = "shipped"          # 已发货
    DELIVERED = "delivered"       # 已送达
    CANCELLED = "cancelled"       # 已取消
    REFUNDED = "refunded"         # 已退款
    FAILED = "failed"            # 失败


class OrderSystemType(Enum):
    """订单系统类型"""
    CORE = "core"                 # 核心订单
    SCM = "scm"                  # SCM订单
    SHOPIFY = "shopify"          # Shopify订单
    PRINTIFY = "printify"        # Printify订单


@dataclass
class StatusTransition:
    """状态转换定义"""
    from_status: str
    to_status: str
    allowed: bool
    requires_approval: bool = False
    auto_transition: bool = False
    conditions: List[str] = None  # 转换条件
    description: str = ""


@dataclass
class OrderStateHistory:
    """订单状态历史记录"""
    order_id: int
    system_type: OrderSystemType
    from_status: str
    to_status: str
    timestamp: datetime
    user_id: Optional[int] = None
    reason: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class OrderLifecycleService:
    """订单状态生命周期管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.status_transitions = self._initialize_status_transitions()
        self.lifecycle_stages = self._initialize_lifecycle_stages()
    
    def _initialize_status_transitions(self) -> Dict[str, List[StatusTransition]]:
        """初始化状态转换规则"""
        return {
            # 核心订单状态转换
            "core": [
                StatusTransition("pending", "processing", True, False, True, 
                               ["payment_confirmed"], "订单确认，开始处理"),
                StatusTransition("processing", "fulfilled", True, False, True,
                               ["all_items_processed"], "订单处理完成"),
                StatusTransition("fulfilled", "shipped", True, False, True,
                               ["tracking_available"], "订单已发货"),
                StatusTransition("shipped", "delivered", True, False, True,
                               ["delivery_confirmed"], "订单已送达"),
                StatusTransition("pending", "cancelled", True, False, False,
                               ["customer_request", "payment_failed"], "订单取消"),
                StatusTransition("processing", "cancelled", True, True, False,
                               ["customer_request", "inventory_issue"], "处理中订单取消"),
                StatusTransition("fulfilled", "cancelled", False, True, False,
                               [], "已完成订单不能取消"),
                StatusTransition("delivered", "refunded", True, True, False,
                               ["customer_request", "defective_product"], "订单退款"),
            ],
            
            # SCM订单状态转换
            "scm": [
                StatusTransition("created", "processing", True, False, True,
                               ["routing_completed"], "SCM订单开始处理"),
                StatusTransition("processing", "fulfilled", True, False, True,
                               ["production_completed"], "SCM订单处理完成"),
                StatusTransition("fulfilled", "shipped", True, False, True,
                               ["tracking_available"], "SCM订单已发货"),
                StatusTransition("shipped", "delivered", True, False, True,
                               ["delivery_confirmed"], "SCM订单已送达"),
                StatusTransition("created", "cancelled", True, False, False,
                               ["customer_request", "routing_failed"], "SCM订单取消"),
                StatusTransition("processing", "cancelled", True, True, False,
                               ["customer_request", "production_failed"], "处理中SCM订单取消"),
                StatusTransition("fulfilled", "cancelled", False, True, False,
                               [], "已完成SCM订单不能取消"),
            ],
            
            # Shopify订单状态转换
            "shopify": [
                StatusTransition("pending_payment", "paid", True, False, True,
                               ["payment_confirmed"], "Shopify订单支付确认"),
                StatusTransition("paid", "partially_fulfilled", True, False, True,
                               ["partial_fulfillment"], "Shopify订单部分履约"),
                StatusTransition("partially_fulfilled", "fulfilled", True, False, True,
                               ["all_items_fulfilled"], "Shopify订单完全履约"),
                StatusTransition("paid", "fulfilled", True, False, True,
                               ["all_items_fulfilled"], "Shopify订单直接履约"),
                StatusTransition("pending_payment", "cancelled", True, False, False,
                               ["customer_request", "payment_failed"], "Shopify订单取消"),
                StatusTransition("paid", "cancelled", True, True, False,
                               ["customer_request"], "已支付Shopify订单取消"),
                StatusTransition("fulfilled", "cancelled", False, True, False,
                               [], "已履约Shopify订单不能取消"),
            ],
            
            # Printify订单状态转换
            "printify": [
                StatusTransition("pending", "in_production", True, False, True,
                               ["order_accepted"], "Printify订单开始生产"),
                StatusTransition("in_production", "shipped", True, False, True,
                               ["production_completed", "tracking_available"], "Printify订单已发货"),
                StatusTransition("shipped", "delivered", True, False, True,
                               ["delivery_confirmed"], "Printify订单已送达"),
                StatusTransition("pending", "cancelled", True, False, False,
                               ["customer_request", "rejected"], "Printify订单取消"),
                StatusTransition("in_production", "cancelled", True, True, False,
                               ["customer_request", "production_failed"], "生产中Printify订单取消"),
                StatusTransition("shipped", "cancelled", False, True, False,
                               [], "已发货Printify订单不能取消"),
            ]
        }
    
    def _initialize_lifecycle_stages(self) -> Dict[str, List[OrderLifecycleStage]]:
        """初始化生命周期阶段"""
        return {
            "core": [
                OrderLifecycleStage.CREATED,
                OrderLifecycleStage.CONFIRMED,
                OrderLifecycleStage.PROCESSING,
                OrderLifecycleStage.FULFILLED,
                OrderLifecycleStage.SHIPPED,
                OrderLifecycleStage.DELIVERED,
                OrderLifecycleStage.CANCELLED,
                OrderLifecycleStage.REFUNDED,
                OrderLifecycleStage.FAILED
            ],
            "scm": [
                OrderLifecycleStage.CREATED,
                OrderLifecycleStage.PROCESSING,
                OrderLifecycleStage.FULFILLED,
                OrderLifecycleStage.SHIPPED,
                OrderLifecycleStage.DELIVERED,
                OrderLifecycleStage.CANCELLED,
                OrderLifecycleStage.FAILED
            ],
            "shopify": [
                OrderLifecycleStage.CREATED,
                OrderLifecycleStage.CONFIRMED,
                OrderLifecycleStage.PROCESSING,
                OrderLifecycleStage.FULFILLED,
                OrderLifecycleStage.CANCELLED,
                OrderLifecycleStage.REFUNDED
            ],
            "printify": [
                OrderLifecycleStage.CREATED,
                OrderLifecycleStage.PROCESSING,
                OrderLifecycleStage.FULFILLED,
                OrderLifecycleStage.SHIPPED,
                OrderLifecycleStage.DELIVERED,
                OrderLifecycleStage.CANCELLED,
                OrderLifecycleStage.FAILED
            ]
        }
    
    async def validate_status_transition(
        self,
        order_id: int,
        system_type: OrderSystemType,
        from_status: str,
        to_status: str,
        tenant_id: int
    ) -> Tuple[bool, str, List[str]]:
        """
        验证状态转换是否允许
        
        Args:
            order_id: 订单ID
            system_type: 系统类型
            from_status: 当前状态
            to_status: 目标状态
            tenant_id: 租户ID
            
        Returns:
            (是否允许, 错误信息, 缺失条件)
        """
        try:
            logger.info(
                "🔍 验证状态转换",
                order_id=order_id,
                system_type=system_type.value,
                from_status=from_status,
                to_status=to_status,
                tenant_id=tenant_id
            )
            
            # 获取状态转换规则
            transitions = self.status_transitions.get(system_type.value, [])
            
            # 查找匹配的转换规则
            transition = None
            for t in transitions:
                if t.from_status == from_status and t.to_status == to_status:
                    transition = t
                    break
            
            if not transition:
                return False, f"不支持的状态转换: {from_status} -> {to_status}", []
            
            if not transition.allowed:
                return False, f"状态转换被禁止: {from_status} -> {to_status}", []
            
            # 检查转换条件
            missing_conditions = []
            if transition.conditions:
                for condition in transition.conditions:
                    if not await self._check_transition_condition(
                        order_id, system_type, condition, tenant_id
                    ):
                        missing_conditions.append(condition)
            
            if missing_conditions:
                return False, f"状态转换条件不满足: {', '.join(missing_conditions)}", missing_conditions
            
            logger.info(
                "✅ 状态转换验证通过",
                order_id=order_id,
                from_status=from_status,
                to_status=to_status
            )
            
            return True, "状态转换验证通过", []
            
        except Exception as e:
            logger.error(
                "❌ 状态转换验证失败",
                order_id=order_id,
                system_type=system_type.value,
                from_status=from_status,
                to_status=to_status,
                error=str(e)
            )
            return False, f"状态转换验证失败: {str(e)}", []
    
    async def transition_order_status(
        self,
        order_id: int,
        system_type: OrderSystemType,
        to_status: str,
        tenant_id: int,
        user_id: Optional[int] = None,
        reason: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        执行订单状态转换
        
        Args:
            order_id: 订单ID
            system_type: 系统类型
            to_status: 目标状态
            tenant_id: 租户ID
            user_id: 操作用户ID
            reason: 转换原因
            metadata: 元数据
            
        Returns:
            转换结果
        """
        try:
            logger.info(
                "🔍 开始执行状态转换",
                order_id=order_id,
                system_type=system_type.value,
                to_status=to_status,
                tenant_id=tenant_id,
                user_id=user_id
            )
            
            # 获取订单
            order = await self._get_order(order_id, system_type, tenant_id)
            if not order:
                return {
                    "success": False,
                    "message": f"订单不存在: {order_id}",
                    "error": "ORDER_NOT_FOUND"
                }
            
            from_status = order.status
            
            # 验证状态转换
            is_valid, error_message, missing_conditions = await self.validate_status_transition(
                order_id, system_type, from_status, to_status, tenant_id
            )
            
            if not is_valid:
                return {
                    "success": False,
                    "message": error_message,
                    "error": "INVALID_TRANSITION",
                    "missing_conditions": missing_conditions
                }
            
            # 执行状态转换
            order.status = to_status
            order.updated_at = datetime.utcnow()
            
            # 根据系统类型更新特定字段
            await self._update_system_specific_fields(order, system_type, to_status)
            
            # 记录状态历史
            await self._record_status_history(
                order_id, system_type, from_status, to_status, 
                user_id, reason, metadata
            )
            
            await self.db.commit()
            
            logger.info(
                "✅ 状态转换成功",
                order_id=order_id,
                from_status=from_status,
                to_status=to_status
            )
            
            return {
                "success": True,
                "message": f"状态从 {from_status} 转换为 {to_status}",
                "from_status": from_status,
                "to_status": to_status,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(
                "❌ 状态转换失败",
                order_id=order_id,
                system_type=system_type.value,
                to_status=to_status,
                error=str(e)
            )
            await self.db.rollback()
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            
            return {
                "success": False,
                "message": f"状态转换失败: {str(e)}",
                "error": str(e)
            }
    
    async def get_order_lifecycle(
        self,
        order_id: int,
        system_type: OrderSystemType,
        tenant_id: int
    ) -> Dict[str, Any]:
        """
        获取订单生命周期信息
        
        Args:
            order_id: 订单ID
            system_type: 系统类型
            tenant_id: 租户ID
            
        Returns:
            生命周期信息
        """
        try:
            logger.info(
                "🔍 获取订单生命周期",
                order_id=order_id,
                system_type=system_type.value,
                tenant_id=tenant_id
            )
            
            # 获取订单
            order = await self._get_order(order_id, system_type, tenant_id)
            if not order:
                return {
                    "success": False,
                    "message": f"订单不存在: {order_id}",
                    "error": "ORDER_NOT_FOUND"
                }
            
            # 获取状态历史
            history = await self._get_status_history(order_id, system_type, tenant_id)
            
            # 获取可用的状态转换
            available_transitions = await self._get_available_transitions(
                order_id, system_type, order.status, tenant_id
            )
            
            # 计算生命周期进度
            lifecycle_progress = self._calculate_lifecycle_progress(
                system_type, order.status, history
            )
            
            return {
                "success": True,
                "order_id": order_id,
                "system_type": system_type.value,
                "current_status": order.status,
                "lifecycle_stages": [stage.value for stage in self.lifecycle_stages.get(system_type.value, [])],
                "current_stage": self._get_current_lifecycle_stage(system_type, order.status),
                "lifecycle_progress": lifecycle_progress,
                "status_history": history,
                "available_transitions": available_transitions,
                "created_at": order.created_at.isoformat() if hasattr(order, 'created_at') else None,
                "updated_at": order.updated_at.isoformat() if hasattr(order, 'updated_at') else None
            }
            
        except Exception as e:
            logger.error(
                "❌ 获取订单生命周期失败",
                order_id=order_id,
                system_type=system_type.value,
                error=str(e)
            )
            
            return {
                "success": False,
                "message": f"获取订单生命周期失败: {str(e)}",
                "error": str(e)
            }
    
    async def _get_order(self, order_id: int, system_type: OrderSystemType, tenant_id: int):
        """获取订单对象"""
        if system_type == OrderSystemType.CORE:
            result = await self.db.execute(
                select(Order).where(
                    and_(Order.id == order_id, Order.tenant_id == tenant_id)
                )
            )
            return result.scalar_one_or_none()
        elif system_type == OrderSystemType.SCM:
            result = await self.db.execute(
                select(SCMOrder).where(
                    and_(SCMOrder.id == order_id, SCMOrder.tenant_id == tenant_id)
                )
            )
            return result.scalar_one_or_none()
        elif system_type == OrderSystemType.SHOPIFY:
            result = await self.db.execute(
                select(ShopifyOrder).where(
                    and_(ShopifyOrder.id == order_id, ShopifyOrder.tenant_id == tenant_id)
                )
            )
            return result.scalar_one_or_none()
        else:
            return None
    
    async def _check_transition_condition(
        self, order_id: int, system_type: OrderSystemType, condition: str, tenant_id: int
    ) -> bool:
        """检查状态转换条件"""
        # 这里需要根据具体的业务逻辑实现条件检查
        # 例如：检查支付状态、库存状态、履约状态等
        logger.info(f"🔍 检查转换条件: {condition}")
        
        # 简化实现，实际应该根据具体条件进行判断
        return True
    
    async def _update_system_specific_fields(self, order, system_type: OrderSystemType, to_status: str):
        """更新系统特定字段"""
        if system_type == OrderSystemType.SCM:
            if to_status == "shipped":
                order.shipped_at = datetime.utcnow()
            elif to_status == "delivered":
                order.delivered_at = datetime.utcnow()
        elif system_type == OrderSystemType.SHOPIFY:
            if to_status == "fulfilled":
                order.fulfillment_status = "fulfilled"
        # 其他系统的特定字段更新逻辑
    
    async def _record_status_history(
        self, order_id: int, system_type: OrderSystemType, from_status: str, 
        to_status: str, user_id: Optional[int], reason: Optional[str], 
        metadata: Optional[Dict[str, Any]]
    ):
        """记录状态历史"""
        # 这里应该将状态历史记录到数据库
        # 简化实现，实际应该存储到状态历史表
        logger.info(
            f"📝 记录状态历史: {order_id} {from_status} -> {to_status}",
            system_type=system_type.value,
            user_id=user_id,
            reason=reason
        )
    
    async def _get_status_history(self, order_id: int, system_type: OrderSystemType, tenant_id: int) -> List[Dict[str, Any]]:
        """获取状态历史"""
        # 简化实现，实际应该从状态历史表查询
        return []
    
    async def _get_available_transitions(
        self, order_id: int, system_type: OrderSystemType, current_status: str, tenant_id: int
    ) -> List[Dict[str, Any]]:
        """获取可用的状态转换"""
        transitions = self.status_transitions.get(system_type.value, [])
        available = []
        
        for transition in transitions:
            if transition.from_status == current_status and transition.allowed:
                # 检查条件是否满足
                conditions_met = True
                if transition.conditions:
                    for condition in transition.conditions:
                        if not await self._check_transition_condition(order_id, system_type, condition, tenant_id):
                            conditions_met = False
                            break
                
                if conditions_met:
                    available.append({
                        "to_status": transition.to_status,
                        "requires_approval": transition.requires_approval,
                        "auto_transition": transition.auto_transition,
                        "description": transition.description
                    })
        
        return available
    
    def _calculate_lifecycle_progress(
        self, system_type: OrderSystemType, current_status: str, history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """计算生命周期进度"""
        stages = self.lifecycle_stages.get(system_type.value, [])
        current_stage = self._get_current_lifecycle_stage(system_type, current_status)
        
        if not current_stage:
            return {"progress_percentage": 0, "current_stage": None, "completed_stages": []}
        
        try:
            current_index = stages.index(current_stage)
            progress_percentage = int((current_index + 1) / len(stages) * 100)
            completed_stages = [stage.value for stage in stages[:current_index + 1]]
            
            return {
                "progress_percentage": progress_percentage,
                "current_stage": current_stage.value,
                "completed_stages": completed_stages,
                "total_stages": len(stages)
            }
        except ValueError:
            return {"progress_percentage": 0, "current_stage": None, "completed_stages": []}
    
    def _get_current_lifecycle_stage(self, system_type: OrderSystemType, status: str) -> Optional[OrderLifecycleStage]:
        """获取当前生命周期阶段"""
        # 根据状态映射到生命周期阶段
        status_to_stage = {
            "created": OrderLifecycleStage.CREATED,
            "pending": OrderLifecycleStage.CREATED,
            "confirmed": OrderLifecycleStage.CONFIRMED,
            "processing": OrderLifecycleStage.PROCESSING,
            "fulfilled": OrderLifecycleStage.FULFILLED,
            "shipped": OrderLifecycleStage.SHIPPED,
            "delivered": OrderLifecycleStage.DELIVERED,
            "cancelled": OrderLifecycleStage.CANCELLED,
            "refunded": OrderLifecycleStage.REFUNDED,
            "failed": OrderLifecycleStage.FAILED,
        }
        
        return status_to_stage.get(status)

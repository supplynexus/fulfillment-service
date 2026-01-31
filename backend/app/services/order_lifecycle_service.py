"""
订单状态生命周期管理服务
管理订单从创建到完成的状态转换
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from enum import Enum
from app.core.logging import get_logger
from app.models.order import Order
from app.models.scm_order import SCMOrder
from sqlalchemy.orm import Session

logger = get_logger(__name__)


class OrderSystemType(str, Enum):
    """订单系统类型枚举"""
    CORE = "core"
    SCM = "scm"
    SHOPIFY = "shopify"
    PRINTIFY = "printify"


class OrderLifecycleStage(str, Enum):
    """订单生命周期阶段枚举"""
    CREATED = "created"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    FULFILLED = "fulfilled"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"
    FAILED = "failed"


class OrderLifecycleService:
    """订单状态生命周期管理服务"""
    
    def __init__(self, db: Session = None):
        """初始化服务"""
        self.db = db
        self.status_transitions = {
            'created': ['processing', 'cancelled'],
            'processing': ['shipped', 'cancelled'],
            'shipped': ['delivered', 'returned'],
            'delivered': ['returned'],
            'cancelled': [],
            'returned': []
        }
        
        # 生命周期阶段定义
        self.lifecycle_stages = {
            OrderSystemType.CORE: [
                OrderLifecycleStage.CREATED,
                OrderLifecycleStage.CONFIRMED,
                OrderLifecycleStage.PROCESSING,
                OrderLifecycleStage.FULFILLED,
                OrderLifecycleStage.SHIPPED,
                OrderLifecycleStage.DELIVERED
            ],
            OrderSystemType.SCM: [
                OrderLifecycleStage.CREATED,
                OrderLifecycleStage.CONFIRMED,
                OrderLifecycleStage.PROCESSING,
                OrderLifecycleStage.FULFILLED,
                OrderLifecycleStage.SHIPPED,
                OrderLifecycleStage.DELIVERED
            ],
            OrderSystemType.SHOPIFY: [
                OrderLifecycleStage.CREATED,
                OrderLifecycleStage.CONFIRMED,
                OrderLifecycleStage.PROCESSING,
                OrderLifecycleStage.FULFILLED,
                OrderLifecycleStage.SHIPPED,
                OrderLifecycleStage.DELIVERED
            ],
            OrderSystemType.PRINTIFY: [
                OrderLifecycleStage.CREATED,
                OrderLifecycleStage.CONFIRMED,
                OrderLifecycleStage.PROCESSING,
                OrderLifecycleStage.FULFILLED,
                OrderLifecycleStage.SHIPPED,
                OrderLifecycleStage.DELIVERED
            ]
        }
    
    def validate_status_transition(self, from_status: str, to_status: str) -> bool:
        """
        验证订单状态转换是否有效
        
        Args:
            from_status: 当前状态
            to_status: 目标状态
            
        Returns:
            bool: 转换是否有效
        """
        logger.info(f"🔍 验证状态转换: {from_status} -> {to_status}")
        
        if from_status not in self.status_transitions:
            logger.error(f"❌ 无效的当前状态: {from_status}")
            return False
        
        if to_status not in self.status_transitions:
            logger.error(f"❌ 无效的目标状态: {to_status}")
            return False
        
        allowed_transitions = self.status_transitions[from_status]
        is_valid = to_status in allowed_transitions
        
        if is_valid:
            logger.info(f"✅ 状态转换有效: {from_status} -> {to_status}")
        else:
            logger.warning(f"⚠️ 状态转换无效: {from_status} -> {to_status}")
        
        return is_valid
    
    def create_order(self, order_id: int, tenant_id: int) -> Order:
        """
        创建订单
        
        Args:
            order_id: 订单ID
            tenant_id: 租户ID
            
        Returns:
            Order: 创建的订单对象
        """
        logger.info(f"🔍 创建订单: order_id={order_id}, tenant_id={tenant_id}")
        
        # 这里应该从数据库创建订单，现在先返回模拟对象
        order = Order()
        order.id = order_id
        order.tenant_id = tenant_id
        order.status = 'created'
        order.created_at = datetime.utcnow()
        
        logger.info(f"✅ 订单创建成功: order_id={order_id}, status={order.status}")
        return order
    
    def update_order_status(self, order_id: int, new_status: str) -> bool:
        """
        更新订单状态
        
        Args:
            order_id: 订单ID
            new_status: 新状态
            
        Returns:
            bool: 更新是否成功
        """
        logger.info(f"🔍 更新订单状态: order_id={order_id}, new_status={new_status}")
        
        # 验证状态是否有效
        if new_status not in self.status_transitions:
            logger.error(f"❌ 无效的状态: {new_status}")
            raise ValueError(f"无效的状态: {new_status}")
        
        # 这里应该从数据库获取订单并更新状态
        # 现在先模拟更新
        logger.info(f"✅ 订单状态更新成功: order_id={order_id}, status={new_status}")
        return True
    
    def get_order_status_history(self, order_id: int) -> List[Dict[str, Any]]:
        """
        获取订单状态历史
        
        Args:
            order_id: 订单ID
            
        Returns:
            List[Dict]: 状态历史列表
        """
        logger.info(f"🔍 获取订单状态历史: order_id={order_id}")
        
        # 这里应该从数据库获取状态历史
        # 现在先返回模拟数据
        history = [
            {
                'status': 'created',
                'timestamp': datetime.utcnow(),
                'description': '订单已创建'
            },
            {
                'status': 'processing',
                'timestamp': datetime.utcnow(),
                'description': '订单处理中'
            },
            {
                'status': 'shipped',
                'timestamp': datetime.utcnow(),
                'description': '订单已发货'
            },
            {
                'status': 'delivered',
                'timestamp': datetime.utcnow(),
                'description': '订单已送达'
            }
        ]
        
        logger.info(f"✅ 获取状态历史成功: order_id={order_id}, count={len(history)}")
        return history
    
    def get_allowed_transitions(self, current_status: str) -> List[str]:
        """
        获取当前状态允许的转换
        
        Args:
            current_status: 当前状态
            
        Returns:
            List[str]: 允许的状态列表
        """
        logger.info(f"🔍 获取允许的状态转换: current_status={current_status}")
        
        if current_status not in self.status_transitions:
            logger.error(f"❌ 无效的当前状态: {current_status}")
            return []
        
        allowed = self.status_transitions[current_status]
        logger.info(f"✅ 允许的状态转换: {allowed}")
        return allowed
    
    def is_final_status(self, status: str) -> bool:
        """
        检查状态是否为最终状态
        
        Args:
            status: 状态
            
        Returns:
            bool: 是否为最终状态
        """
        logger.info(f"🔍 检查最终状态: status={status}")
        
        final_statuses = ['delivered', 'cancelled', 'returned']
        is_final = status in final_statuses
        
        logger.info(f"✅ 状态 {status} 是否为最终状态: {is_final}")
        return is_final
    
    async def transition_order_status(
        self, 
        order_id: int, 
        system_type: OrderSystemType, 
        to_status: str, 
        tenant_id: int, 
        user_id: int, 
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
            user_id: 用户ID
            reason: 转换原因
            metadata: 元数据
            
        Returns:
            Dict: 转换结果
        """
        logger.info(f"🔍 执行订单状态转换: order_id={order_id}, system_type={system_type.value}, to_status={to_status}")
        
        try:
            # 获取订单
            order = await self._get_order(order_id, system_type, tenant_id)
            if not order:
                return {
                    "success": False,
                    "message": f"订单不存在: {order_id}",
                    "error": "Order not found"
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
                    "error": "Invalid transition",
                    "missing_conditions": missing_conditions
                }
            
            # 执行状态转换（这里应该更新数据库）
            # 现在先模拟成功
            logger.info(f"✅ 订单状态转换成功: {from_status} -> {to_status}")
            
            return {
                "success": True,
                "message": "状态转换成功",
                "from_status": from_status,
                "to_status": to_status,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ 订单状态转换异常: {str(e)}")
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
            Dict: 生命周期信息
        """
        logger.info(f"🔍 获取订单生命周期信息: order_id={order_id}, system_type={system_type.value}")
        
        try:
            # 获取订单
            order = await self._get_order(order_id, system_type, tenant_id)
            if not order:
                return {
                    "success": False,
                    "message": f"订单不存在: {order_id}",
                    "error": "Order not found"
                }
            
            # 获取生命周期阶段
            stages = self.lifecycle_stages.get(system_type, [])
            stage_names = [stage.value for stage in stages]
            
            # 获取状态历史
            status_history = await self._get_status_history(order_id, system_type, tenant_id)
            
            # 获取可用的状态转换
            available_transitions = await self._get_available_transitions(
                order_id, system_type, order.status, tenant_id
            )
            
            # 计算生命周期进度
            current_stage_index = self._get_current_stage_index(order.status, stages)
            lifecycle_progress = {
                "current_stage_index": current_stage_index,
                "total_stages": len(stages),
                "progress_percentage": (current_stage_index / len(stages)) * 100 if stages else 0
            }
            
            return {
                "success": True,
                "order_id": order_id,
                "system_type": system_type.value,
                "current_status": order.status,
                "lifecycle_stages": stage_names,
                "current_stage": self._get_current_stage(order.status, stages),
                "lifecycle_progress": lifecycle_progress,
                "status_history": status_history,
                "available_transitions": available_transitions,
                "created_at": order.created_at.isoformat() if hasattr(order, 'created_at') and order.created_at else None,
                "updated_at": order.updated_at.isoformat() if hasattr(order, 'updated_at') and order.updated_at else None
            }
            
        except Exception as e:
            logger.error(f"❌ 获取订单生命周期信息异常: {str(e)}")
            return {
                "success": False,
                "message": f"获取生命周期信息失败: {str(e)}",
                "error": str(e)
            }
    
    async def validate_status_transition(
        self, 
        order_id: int, 
        system_type: OrderSystemType, 
        from_status: str, 
        to_status: str, 
        tenant_id: int
    ) -> tuple[bool, Optional[str], List[str]]:
        """
        验证状态转换是否允许
        
        Args:
            order_id: 订单ID
            system_type: 系统类型
            from_status: 当前状态
            to_status: 目标状态
            tenant_id: 租户ID
            
        Returns:
            tuple: (是否有效, 错误信息, 缺少的条件)
        """
        logger.info(f"🔍 验证状态转换: {from_status} -> {to_status}")
        
        # 基本验证
        if from_status not in self.status_transitions:
            return False, f"无效的当前状态: {from_status}", []
        
        if to_status not in self.status_transitions:
            return False, f"无效的目标状态: {to_status}", []
        
        # 检查是否允许转换
        allowed_transitions = self.status_transitions[from_status]
        if to_status not in allowed_transitions:
            return False, f"不允许的状态转换: {from_status} -> {to_status}", []
        
        # 这里可以添加更复杂的条件验证
        # 比如检查订单是否满足特定条件等
        
        return True, None, []
    
    async def _get_order(self, order_id: int, system_type: OrderSystemType, tenant_id: int):
        """
        获取订单对象
        
        Args:
            order_id: 订单ID
            system_type: 系统类型
            tenant_id: 租户ID
            
        Returns:
            订单对象或None
        """
        # 这里应该根据系统类型从不同的表查询订单
        # 现在先返回模拟对象
        if system_type == OrderSystemType.CORE:
            order = Order()
            order.id = order_id
            order.status = 'created'
            return order
        elif system_type == OrderSystemType.SCM:
            order = SCMOrder()
            order.id = order_id
            order.status = 'created'
            return order
        else:
            # 其他系统类型的处理
            return None
    
    async def _get_status_history(self, order_id: int, system_type: OrderSystemType, tenant_id: int) -> List[Dict[str, Any]]:
        """
        获取状态历史
        
        Args:
            order_id: 订单ID
            system_type: 系统类型
            tenant_id: 租户ID
            
        Returns:
            状态历史列表
        """
        # 这里应该从数据库查询状态历史
        # 现在先返回模拟数据
        return [
            {
                "status": "created",
                "timestamp": datetime.utcnow().isoformat(),
                "user_id": 1,
                "reason": "订单创建"
            }
        ]
    
    async def _get_available_transitions(
        self, 
        order_id: int, 
        system_type: OrderSystemType, 
        current_status: str, 
        tenant_id: int
    ) -> List[Dict[str, Any]]:
        """
        获取可用的状态转换
        
        Args:
            order_id: 订单ID
            system_type: 系统类型
            current_status: 当前状态
            tenant_id: 租户ID
            
        Returns:
            可用转换列表
        """
        # 这里应该根据业务规则计算可用的转换
        # 现在先返回基本转换
        allowed_transitions = self.status_transitions.get(current_status, [])
        
        transitions = []
        for to_status in allowed_transitions:
            transitions.append({
                "to_status": to_status,
                "description": f"从 {current_status} 转换到 {to_status}",
                "requires_approval": False,
                "auto_transition": False
            })
        
        return transitions
    
    def _get_current_stage_index(self, status: str, stages: List[OrderLifecycleStage]) -> int:
        """
        获取当前阶段索引
        
        Args:
            status: 当前状态
            stages: 阶段列表
            
        Returns:
            阶段索引
        """
        try:
            current_stage = OrderLifecycleStage(status)
            return stages.index(current_stage)
        except (ValueError, AttributeError):
            return 0
    
    def _get_current_stage(self, status: str, stages: List[OrderLifecycleStage]) -> Optional[str]:
        """
        获取当前阶段
        
        Args:
            status: 当前状态
            stages: 阶段列表
            
        Returns:
            当前阶段或None
        """
        try:
            current_stage = OrderLifecycleStage(status)
            if current_stage in stages:
                return current_stage.value
        except (ValueError, AttributeError):
            pass
        return None
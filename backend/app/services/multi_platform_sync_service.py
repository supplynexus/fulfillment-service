"""
多平台状态同步服务
提供跨平台的状态同步机制，支持Shopify、Core、SCM、Printify之间的状态同步
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass
import asyncio

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc
from sqlalchemy.orm import selectinload

from app.core.logging import get_logger
from app.models.order import Order, OrderStatus
from app.models.scm_order import SCMOrder, SCMOrderStatus
from app.models.shopify_order import ShopifyOrder
from app.services.enhanced_order_status_sync_service import EnhancedOrderStatusSyncService, SyncDirection
from app.services.order_lifecycle_service import OrderLifecycleService, OrderSystemType

logger = get_logger(__name__)


class SyncPriority(Enum):
    """同步优先级"""
    HIGH = "high"           # 高优先级
    NORMAL = "normal"       # 普通优先级
    LOW = "low"            # 低优先级


class SyncStatus(Enum):
    """同步状态"""
    PENDING = "pending"     # 待同步
    IN_PROGRESS = "in_progress"  # 同步中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"      # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class SyncTask:
    """同步任务"""
    task_id: str
    order_id: int
    system_type: OrderSystemType
    sync_direction: SyncDirection
    priority: SyncPriority
    status: SyncStatus
    created_at: datetime
    updated_at: datetime
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class MultiPlatformSyncService:
    """多平台状态同步服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.sync_service = EnhancedOrderStatusSyncService(db)
        self.lifecycle_service = OrderLifecycleService(db)
        self.sync_tasks = {}  # 同步任务队列
        self.sync_history = {}  # 同步历史记录
        self.sync_rules = self._initialize_sync_rules()
    
    def _initialize_sync_rules(self) -> Dict[str, Dict[str, Any]]:
        """初始化同步规则"""
        return {
            # Shopify到Core的同步规则
            "shopify_to_core": {
                "enabled": True,
                "auto_sync": True,
                "status_mapping": {
                    "pending_payment": "pending",
                    "paid": "processing",
                    "partially_fulfilled": "processing",
                    "fulfilled": "fulfilled",
                    "cancelled": "cancelled"
                },
                "conditions": ["payment_confirmed", "order_created"],
                "priority": SyncPriority.HIGH
            },
            
            # Core到SCM的同步规则
            "core_to_scm": {
                "enabled": True,
                "auto_sync": True,
                "status_mapping": {
                    "processing": "created",
                    "fulfilled": "processing",
                    "cancelled": "cancelled"
                },
                "conditions": ["routing_completed", "inventory_available"],
                "priority": SyncPriority.HIGH
            },
            
            # SCM到Printify的同步规则
            "scm_to_printify": {
                "enabled": True,
                "auto_sync": True,
                "status_mapping": {
                    "processing": "pending",
                    "fulfilled": "in_production",
                    "cancelled": "cancelled"
                },
                "conditions": ["printify_credentials_available", "product_mapped"],
                "priority": SyncPriority.NORMAL
            },
            
            # Printify到SCM的同步规则
            "printify_to_scm": {
                "enabled": True,
                "auto_sync": True,
                "status_mapping": {
                    "pending": "processing",
                    "in_production": "processing",
                    "shipped": "fulfilled",
                    "delivered": "fulfilled",
                    "cancelled": "cancelled"
                },
                "conditions": ["printify_order_created"],
                "priority": SyncPriority.NORMAL
            },
            
            # SCM到Shopify的同步规则
            "scm_to_shopify": {
                "enabled": True,
                "auto_sync": True,
                "status_mapping": {
                    "fulfilled": "fulfilled",
                    "cancelled": "cancelled"
                },
                "conditions": ["shopify_order_exists", "fulfillment_ready"],
                "priority": SyncPriority.HIGH
            }
        }
    
    async def sync_order_across_platforms(
        self,
        order_id: int,
        source_system: OrderSystemType,
        target_systems: List[OrderSystemType],
        tenant_id: int,
        force_sync: bool = False
    ) -> Dict[str, Any]:
        """
        跨平台同步订单状态
        
        Args:
            order_id: 订单ID
            source_system: 源系统
            target_systems: 目标系统列表
            tenant_id: 租户ID
            force_sync: 是否强制同步
            
        Returns:
            同步结果
        """
        try:
            logger.info(
                "🔍 开始跨平台同步订单状态",
                order_id=order_id,
                source_system=source_system.value,
                target_systems=[t.value for t in target_systems],
                tenant_id=tenant_id,
                force_sync=force_sync
            )
            
            # 获取源订单
            source_order = await self._get_order(order_id, source_system, tenant_id)
            if not source_order:
                return {
                    "success": False,
                    "message": f"源订单不存在: {order_id}",
                    "error": "SOURCE_ORDER_NOT_FOUND"
                }
            
            # 创建同步任务
            sync_tasks = []
            for target_system in target_systems:
                sync_direction = self._get_sync_direction(source_system, target_system)
                if sync_direction:
                    task = await self._create_sync_task(
                        order_id, source_system, target_system, sync_direction, tenant_id
                    )
                    sync_tasks.append(task)
            
            if not sync_tasks:
                return {
                    "success": False,
                    "message": "没有可执行的同步任务",
                    "error": "NO_SYNC_TASKS"
                }
            
            # 执行同步任务
            results = []
            for task in sync_tasks:
                result = await self._execute_sync_task(task, tenant_id, force_sync)
                results.append(result)
            
            # 统计结果
            success_count = sum(1 for r in results if r.get("success"))
            error_count = len(results) - success_count
            
            return {
                "success": error_count == 0,
                "message": f"跨平台同步完成: {success_count}成功, {error_count}失败",
                "total_tasks": len(sync_tasks),
                "success_count": success_count,
                "error_count": error_count,
                "results": results
            }
            
        except Exception as e:
            logger.error(
                "❌ 跨平台同步订单状态失败",
                order_id=order_id,
                source_system=source_system.value,
                target_systems=[t.value for t in target_systems],
                error=str(e)
            )
            import traceback
            logger.error(f"   异常堆栈: {traceback.format_exc()}")
            
            return {
                "success": False,
                "message": f"跨平台同步失败: {str(e)}",
                "error": str(e)
            }
    
    async def auto_sync_order_status(
        self,
        order_id: int,
        system_type: OrderSystemType,
        new_status: str,
        tenant_id: int
    ) -> Dict[str, Any]:
        """
        自动同步订单状态变更
        
        Args:
            order_id: 订单ID
            system_type: 系统类型
            new_status: 新状态
            tenant_id: 租户ID
            
        Returns:
            自动同步结果
        """
        try:
            logger.info(
                "🔍 开始自动同步订单状态变更",
                order_id=order_id,
                system_type=system_type.value,
                new_status=new_status,
                tenant_id=tenant_id
            )
            
            # 获取自动同步规则
            auto_sync_rules = self._get_auto_sync_rules(system_type)
            
            if not auto_sync_rules:
                return {
                    "success": True,
                    "message": "没有自动同步规则",
                    "synced_count": 0
                }
            
            # 执行自动同步
            sync_results = []
            for rule in auto_sync_rules:
                if rule.get("enabled") and rule.get("auto_sync"):
                    target_system = OrderSystemType(rule["target_system"])
                    sync_direction = SyncDirection(rule["sync_direction"])
                    
                    # 检查同步条件
                    if await self._check_sync_conditions(order_id, system_type, target_system, tenant_id):
                        result = await self.sync_service.sync_order_status(
                            order_id=order_id,
                            direction=sync_direction,
                            tenant_id=tenant_id,
                            force_sync=False
                        )
                        sync_results.append(result)
            
            success_count = sum(1 for r in sync_results if r.get("success"))
            
            return {
                "success": True,
                "message": f"自动同步完成: {success_count}个系统同步成功",
                "synced_count": success_count,
                "results": sync_results
            }
            
        except Exception as e:
            logger.error(
                "❌ 自动同步订单状态变更失败",
                order_id=order_id,
                system_type=system_type.value,
                new_status=new_status,
                error=str(e)
            )
            
            return {
                "success": False,
                "message": f"自动同步失败: {str(e)}",
                "error": str(e)
            }
    
    async def batch_sync_orders(
        self,
        system_type: OrderSystemType,
        tenant_id: int,
        limit: int = 100,
        status_filter: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        批量同步订单状态
        
        Args:
            system_type: 系统类型
            tenant_id: 租户ID
            limit: 最大处理数量
            status_filter: 状态过滤器
            
        Returns:
            批量同步结果
        """
        try:
            logger.info(
                "🔍 开始批量同步订单状态",
                system_type=system_type.value,
                tenant_id=tenant_id,
                limit=limit,
                status_filter=status_filter
            )
            
            # 获取需要同步的订单
            orders = await self._get_orders_for_sync(system_type, tenant_id, limit, status_filter)
            
            if not orders:
                return {
                    "success": True,
                    "message": "没有需要同步的订单",
                    "total_processed": 0,
                    "success_count": 0,
                    "error_count": 0
                }
            
            # 并发同步订单
            sync_tasks = []
            for order in orders:
                # 获取自动同步规则
                auto_sync_rules = self._get_auto_sync_rules(system_type)
                
                for rule in auto_sync_rules:
                    if rule.get("enabled") and rule.get("auto_sync"):
                        target_system = OrderSystemType(rule["target_system"])
                        sync_direction = SyncDirection(rule["sync_direction"])
                        
                        task = self._execute_sync_task_async(
                            order.id, system_type, target_system, sync_direction, tenant_id
                        )
                        sync_tasks.append(task)
            
            # 等待所有同步任务完成
            results = await asyncio.gather(*sync_tasks, return_exceptions=True)
            
            # 统计结果
            success_count = 0
            error_count = 0
            errors = []
            
            for result in results:
                if isinstance(result, Exception):
                    error_count += 1
                    errors.append(str(result))
                elif result.get("success"):
                    success_count += 1
                else:
                    error_count += 1
                    errors.append(result.get("message", "未知错误"))
            
            return {
                "success": error_count == 0,
                "message": f"批量同步完成: {success_count}成功, {error_count}失败",
                "total_processed": len(orders),
                "success_count": success_count,
                "error_count": error_count,
                "errors": errors[:10]  # 只返回前10个错误
            }
            
        except Exception as e:
            logger.error(
                "❌ 批量同步订单状态失败",
                system_type=system_type.value,
                tenant_id=tenant_id,
                error=str(e)
            )
            
            return {
                "success": False,
                "message": f"批量同步失败: {str(e)}",
                "error": str(e)
            }
    
    async def _get_order(self, order_id: int, system_type: OrderSystemType, tenant_id: int):
        """获取订单对象"""
        return await self.lifecycle_service._get_order(order_id, system_type, tenant_id)
    
    def _get_sync_direction(self, source_system: OrderSystemType, target_system: OrderSystemType) -> Optional[SyncDirection]:
        """获取同步方向"""
        if source_system == OrderSystemType.SHOPIFY and target_system == OrderSystemType.CORE:
            return SyncDirection.SHOPIFY_TO_SCM
        elif source_system == OrderSystemType.CORE and target_system == OrderSystemType.SCM:
            return SyncDirection.SCM_TO_SHOPIFY  # 这里应该是Core到SCM，需要调整
        elif source_system == OrderSystemType.SCM and target_system == OrderSystemType.PRINTIFY:
            return SyncDirection.SCM_TO_SHOPIFY  # 这里应该是SCM到Printify，需要调整
        elif source_system == OrderSystemType.PRINTIFY and target_system == OrderSystemType.SCM:
            return SyncDirection.PRINTIFY_TO_SCM
        elif source_system == OrderSystemType.SCM and target_system == OrderSystemType.SHOPIFY:
            return SyncDirection.SCM_TO_SHOPIFY
        else:
            return None
    
    async def _create_sync_task(
        self, order_id: int, source_system: OrderSystemType, target_system: OrderSystemType,
        sync_direction: SyncDirection, tenant_id: int
    ) -> SyncTask:
        """创建同步任务"""
        task_id = f"{order_id}_{source_system.value}_{target_system.value}_{datetime.utcnow().timestamp()}"
        
        task = SyncTask(
            task_id=task_id,
            order_id=order_id,
            system_type=source_system,
            sync_direction=sync_direction,
            priority=SyncPriority.NORMAL,
            status=SyncStatus.PENDING,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        self.sync_tasks[task_id] = task
        return task
    
    async def _execute_sync_task(self, task: SyncTask, tenant_id: int, force_sync: bool = False) -> Dict[str, Any]:
        """执行同步任务"""
        try:
            task.status = SyncStatus.IN_PROGRESS
            task.updated_at = datetime.utcnow()
            
            result = await self.sync_service.sync_order_status(
                order_id=task.order_id,
                direction=task.sync_direction,
                tenant_id=tenant_id,
                force_sync=force_sync
            )
            
            if result.get("success"):
                task.status = SyncStatus.COMPLETED
            else:
                task.status = SyncStatus.FAILED
                task.error_message = result.get("message")
            
            task.updated_at = datetime.utcnow()
            
            return result
            
        except Exception as e:
            task.status = SyncStatus.FAILED
            task.error_message = str(e)
            task.updated_at = datetime.utcnow()
            
            return {
                "success": False,
                "message": f"同步任务执行失败: {str(e)}",
                "error": str(e)
            }
    
    async def _execute_sync_task_async(
        self, order_id: int, source_system: OrderSystemType, target_system: OrderSystemType,
        sync_direction: SyncDirection, tenant_id: int
    ) -> Dict[str, Any]:
        """异步执行同步任务"""
        try:
            return await self.sync_service.sync_order_status(
                order_id=order_id,
                direction=sync_direction,
                tenant_id=tenant_id,
                force_sync=False
            )
        except Exception as e:
            return {
                "success": False,
                "message": f"异步同步任务执行失败: {str(e)}",
                "error": str(e)
            }
    
    def _get_auto_sync_rules(self, system_type: OrderSystemType) -> List[Dict[str, Any]]:
        """获取自动同步规则"""
        rules = []
        for rule_name, rule_config in self.sync_rules.items():
            if rule_name.startswith(f"{system_type.value}_to_"):
                rule_config["rule_name"] = rule_name
                rule_config["source_system"] = system_type.value
                rule_config["target_system"] = rule_name.split("_to_")[1]
                rule_config["sync_direction"] = rule_name.replace("_to_", "_to_").upper()
                rules.append(rule_config)
        return rules
    
    async def _check_sync_conditions(
        self, order_id: int, source_system: OrderSystemType, target_system: OrderSystemType, tenant_id: int
    ) -> bool:
        """检查同步条件"""
        # 这里需要根据具体的业务逻辑实现条件检查
        # 例如：检查订单状态、支付状态、库存状态等
        logger.info(f"🔍 检查同步条件: {source_system.value} -> {target_system.value}")
        return True
    
    async def _get_orders_for_sync(
        self, system_type: OrderSystemType, tenant_id: int, limit: int, status_filter: Optional[List[str]]
    ) -> List[Any]:
        """获取需要同步的订单"""
        return await self.sync_service._get_orders_for_sync(
            system_type, tenant_id, limit, status_filter
        )

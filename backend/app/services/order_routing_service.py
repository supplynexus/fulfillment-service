"""
Order routing service for SCM order distribution
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.order import Order
from app.models.scm_order import SCMOrder, SCMOrderStatus, RoutingRule, RoutingStatus
from app.schemas.scm_order import SCMOrderCreate, OrderRoutingConfig
from app.core.hashids_utils import encode_id

logger = logging.getLogger(__name__)


class OrderRoutingService:
    """订单路由服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def route_order_to_scm(
        self, order: Order, routing_config: OrderRoutingConfig, tenant_id: int
    ) -> List[SCMOrder]:
        """将订单路由到SCM系统"""
        try:
            logger.info(f"开始路由订单 {order.id} 到SCM系统")

            # 1. 分析订单商品
            line_items = self._analyze_line_items(order.line_items)
            logger.info(f"订单 {order.id} 包含 {len(line_items)} 个商品")

            # 2. 应用路由规则
            routing_decisions = await self._apply_routing_rules(
                line_items, routing_config, tenant_id
            )
            logger.info(f"生成了 {len(routing_decisions)} 个路由决策")

            # 3. 创建SCM订单
            scm_orders = []
            for decision in routing_decisions:
                scm_order = await self._create_scm_order(order, decision, tenant_id)
                scm_orders.append(scm_order)

            # 4. 记录路由状态
            await self._log_routing_status(
                order.id, scm_orders, routing_config, tenant_id
            )

            logger.info(f"成功创建 {len(scm_orders)} 个SCM订单")
            return scm_orders

        except Exception as e:
            logger.error(f"路由订单 {order.id} 失败: {e}")
            raise

    def _analyze_line_items(
        self, line_items: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """分析订单商品"""
        analyzed_items = []

        for item in line_items:
            analyzed_item = {
                "id": item.get("id"),
                "title": item.get("title"),
                "variant_title": item.get("variant_title"),
                "quantity": item.get("quantity", 1),
                "price": item.get("price", 0),
                "sku": item.get("sku"),
                "vendor": item.get("vendor"),
                "product_type": item.get("product_type", "unknown"),
                "properties": item.get("properties", {}),
                "requires_shipping": item.get("requires_shipping", True),
            }
            analyzed_items.append(analyzed_item)

        return analyzed_items

    async def _apply_routing_rules(
        self,
        line_items: List[Dict[str, Any]],
        routing_config: OrderRoutingConfig,
        tenant_id: int,
    ) -> List[Dict[str, Any]]:
        """应用路由规则"""
        routing_decisions = []

        if routing_config.routing_strategy == "manual":
            # 手动路由：使用指定的目标系统
            for target_system in routing_config.target_systems:
                decision = {
                    "target_system_type": target_system.get("system_type"),
                    "target_system_id": target_system.get("system_id"),
                    "line_items": line_items,
                    "routing_metadata": {
                        "strategy": "manual",
                        "target_system": target_system,
                    },
                }
                routing_decisions.append(decision)

        elif routing_config.routing_strategy == "auto":
            # 自动路由：基于规则自动分配
            routing_decisions = await self._auto_route_by_rules(line_items, tenant_id)

        elif routing_config.routing_strategy == "hybrid":
            # 混合路由：结合自动和手动
            auto_decisions = await self._auto_route_by_rules(line_items, tenant_id)
            manual_decisions = []

            for target_system in routing_config.target_systems:
                decision = {
                    "target_system_type": target_system.get("system_type"),
                    "target_system_id": target_system.get("system_id"),
                    "line_items": line_items,
                    "routing_metadata": {
                        "strategy": "manual",
                        "target_system": target_system,
                    },
                }
                manual_decisions.append(decision)

            routing_decisions = auto_decisions + manual_decisions

        return routing_decisions

    async def _auto_route_by_rules(
        self, line_items: List[Dict[str, Any]], tenant_id: int
    ) -> List[Dict[str, Any]]:
        """基于规则自动路由"""
        # 获取活跃的路由规则
        result = await self.db.execute(
            select(RoutingRule)
            .where(RoutingRule.tenant_id == tenant_id, RoutingRule.is_active == True)
            .order_by(RoutingRule.priority.asc())
        )
        rules = result.scalars().all()

        routing_decisions = []
        remaining_items = line_items.copy()

        for rule in rules:
            matched_items = []
            unmatched_items = []

            for item in remaining_items:
                if self._item_matches_rule(item, rule.conditions):
                    matched_items.append(item)
                else:
                    unmatched_items.append(item)

            if matched_items:
                decision = {
                    "target_system_type": rule.target_system_type,
                    "target_system_id": rule.target_system_id,
                    "line_items": matched_items,
                    "routing_metadata": {
                        "strategy": "auto",
                        "rule_id": rule.id,
                        "rule_name": rule.name,
                        "conditions": rule.conditions,
                    },
                }
                routing_decisions.append(decision)

            remaining_items = unmatched_items

        # 处理未匹配的商品（使用默认规则）
        if remaining_items:
            default_decision = {
                "target_system_type": "default_fulfillment",
                "target_system_id": None,
                "line_items": remaining_items,
                "routing_metadata": {
                    "strategy": "auto",
                    "rule_id": None,
                    "rule_name": "default",
                    "conditions": {},
                },
            }
            routing_decisions.append(default_decision)

        return routing_decisions

    def _item_matches_rule(
        self, item: Dict[str, Any], conditions: Dict[str, Any]
    ) -> bool:
        """检查商品是否匹配规则条件"""
        # 产品类型匹配
        if "product_types" in conditions:
            item_type = item.get("product_type", "unknown")
            if item_type not in conditions["product_types"]:
                return False

        # 数量匹配
        if "max_quantity" in conditions:
            if item.get("quantity", 1) > conditions["max_quantity"]:
                return False

        # 供应商匹配
        if "vendors" in conditions:
            vendor = item.get("vendor", "")
            if vendor not in conditions["vendors"]:
                return False

        # SKU匹配
        if "skus" in conditions:
            sku = item.get("sku", "")
            if sku not in conditions["skus"]:
                return False

        return True

    async def _create_scm_order(
        self, order: Order, decision: Dict[str, Any], tenant_id: int
    ) -> SCMOrder:
        """创建SCM订单"""
        # 生成SCM订单号
        scm_order_number = await self._generate_scm_order_number(tenant_id)

        # 计算总金额
        total_amount = sum(
            item.get("price", 0) * item.get("quantity", 1)
            for item in decision["line_items"]
        )

        # 创建SCM订单
        scm_order = SCMOrder(
            tenant_id=tenant_id,
            source_order_id=order.id,
            target_system_type=decision["target_system_type"],
            target_system_id=decision["target_system_id"],
            scm_order_number=scm_order_number,
            status=SCMOrderStatus.CREATED.value,
            routing_strategy=decision["routing_metadata"].get("strategy"),
            line_items=decision["line_items"],
            total_amount=total_amount,
            currency=order.currency,
            customer_email=order.customer_email,
            customer_name=order.customer_name,
            customer_phone=order.customer_phone,
            shipping_address=order.shipping_address,
            billing_address=order.billing_address,
            routing_metadata=decision["routing_metadata"],
            # 添加订单追踪链字段
            shopify_order_id=order.shopify_order_id,
            shopify_fulfillment_order_id=order.shopify_fulfillment_order_id,
        )

        self.db.add(scm_order)
        await self.db.commit()
        await self.db.refresh(scm_order)

        logger.info(f"创建SCM订单 {scm_order.id} ({scm_order.scm_order_number})")
        return scm_order

    async def update_scm_order_with_printify_info(
        self,
        scm_order_id: int,
        printify_order_id: str,
        printify_shop_id: str,
        tenant_id: int,
    ) -> Optional[SCMOrder]:
        """更新SCM订单的Printify信息"""
        try:
            result = await self.db.execute(
                select(SCMOrder).where(
                    and_(SCMOrder.id == scm_order_id, SCMOrder.tenant_id == tenant_id)
                )
            )
            scm_order = result.scalar_one_or_none()

            if not scm_order:
                logger.error(f"SCM订单 {scm_order_id} 不存在")
                return None

            # 更新Printify信息
            scm_order.printify_order_id = printify_order_id
            scm_order.printify_shop_id = printify_shop_id
            scm_order.target_system_id = printify_order_id
            scm_order.updated_at = datetime.now()

            await self.db.commit()
            await self.db.refresh(scm_order)

            logger.info(
                f"✅ 更新SCM订单Printify信息成功",
                scm_order_id=scm_order_id,
                printify_order_id=printify_order_id,
            )

            return scm_order

        except Exception as e:
            logger.error(
                f"❌ 更新SCM订单Printify信息失败",
                scm_order_id=scm_order_id,
                error=str(e),
            )
            await self.db.rollback()
            return None

    async def _generate_scm_order_number(self, tenant_id: int) -> str:
        """生成SCM订单号"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        # 使用时间戳的秒数作为ID生成hashid
        timestamp_int = int(datetime.now().timestamp())
        hashid = encode_id(timestamp_int)
        return f"SCM-{timestamp}-{hashid[:8].upper()}"

    async def _log_routing_status(
        self,
        order_id: int,
        scm_orders: List[SCMOrder],
        routing_config: OrderRoutingConfig,
        tenant_id: int,
    ):
        """记录路由状态"""
        for scm_order in scm_orders:
            routing_status = RoutingStatus(
                tenant_id=tenant_id,
                order_id=order_id,
                scm_order_id=scm_order.id,
                status="completed",
                routing_metadata={
                    "routing_config": routing_config.dict(),
                    "scm_order_number": scm_order.scm_order_number,
                },
            )
            self.db.add(routing_status)

        await self.db.commit()

    async def get_scm_orders_by_order_id(
        self, order_id: int, tenant_id: int
    ) -> List[SCMOrder]:
        """根据订单ID获取SCM订单"""
        result = await self.db.execute(
            select(SCMOrder).where(
                SCMOrder.source_order_id == order_id, SCMOrder.tenant_id == tenant_id
            )
        )
        return result.scalars().all()

    async def update_scm_order_status(
        self, scm_order_id: int, status: str, tenant_id: int, **kwargs
    ) -> Optional[SCMOrder]:
        """更新SCM订单状态"""
        result = await self.db.execute(
            select(SCMOrder).where(
                SCMOrder.id == scm_order_id, SCMOrder.tenant_id == tenant_id
            )
        )
        scm_order = result.scalar_one_or_none()

        if not scm_order:
            return None

        scm_order.status = status
        scm_order.updated_at = datetime.now()

        # 更新其他字段
        for key, value in kwargs.items():
            if hasattr(scm_order, key):
                setattr(scm_order, key, value)

        await self.db.commit()
        await self.db.refresh(scm_order)

        return scm_order

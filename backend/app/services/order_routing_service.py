"""
Order routing service for SCM order distribution
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_
from sqlalchemy.orm import selectinload

from app.models.order import Order
from app.models.scm_order import SCMOrder, SCMOrderStatus, RoutingRule, RoutingStatus, ScmOrderSource
from app.schemas.scm_order import SCMOrderCreate, OrderRoutingConfig

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

            # 1. 从 OrderItem 关系获取订单商品并转换为字典格式
            line_items_dict = []
            if order.items:
                for item in order.items:
                    line_items_dict.append({
                        "id": item.id,
                        "title": item.title or "",
                        "variant_title": item.variant_title or "",
                        "quantity": item.quantity or 1,
                        "price": float(item.unit_price) if item.unit_price else 0.0,
                        "sku": item.sku or "",
                        "vendor": item.item_metadata.get("vendor") if item.item_metadata else None,
                        "product_type": item.item_metadata.get("product_type") if item.item_metadata else "unknown",
                        "properties": item.item_metadata.get("properties", {}) if item.item_metadata else {},
                        "requires_shipping": True,
                        "core_variant_id": item.core_variant_id,
                        "core_product_id": item.core_product_id,
                        "external_product_id": item.external_product_id,
                        "external_variant_id": item.external_variant_id,
                    })
            
            # 2. 分析订单商品
            line_items = self._analyze_line_items(line_items_dict)
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
        # 默认路由到 Printify（如果没有任何规则匹配）
        if remaining_items:
            default_decision = {
                "target_system_type": "PRINTIFY",  # 改为 PRINTIFY，而不是 default_fulfillment
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

    async def _normalize_line_items_for_scm(
        self, line_items: List[Dict[str, Any]], tenant_id: int, order_id: int = None
    ) -> List[Dict[str, Any]]:
        """规范化 line_items 用于 SCM 订单存储"""
        from app.models.product import Product, ProductVariant, ProductMapping
        from app.models.order import OrderItem
        from app.models.external_system import ExternalSystem, ExternalSystemType
        from sqlalchemy import or_
        
        # 如果有关联的核心订单，从 OrderItem 中获取 core_variant_id 和 sku
        order_items_map = {}  # key: OrderItem.id, external_variant_id or sku, value: OrderItem
        if order_id:
            logger.info(f"🔍 从核心订单获取 OrderItem 信息: order_id={order_id}")
            order_items_result = await self.db.execute(
                select(OrderItem).where(
                    and_(
                        OrderItem.order_id == order_id,
                        OrderItem.tenant_id == tenant_id
                    )
                )
            )
            order_items = order_items_result.scalars().all()
            for order_item in order_items:
                # 必须用 OrderItem.id 作为 key：line_items 的 item.get("id") 来自 line_items_dict 的 item.id（即 OrderItem.id）
                order_items_map[order_item.id] = order_item
                order_items_map[str(order_item.id)] = order_item
                # 使用 external_variant_id 作为 key（如果存在）
                if order_item.external_variant_id:
                    order_items_map[str(order_item.external_variant_id)] = order_item
                # 也使用 sku 作为 key（如果存在）
                if order_item.sku:
                    order_items_map[order_item.sku] = order_item
            logger.info(f"✅ 找到 {len(order_items_map)} 个 OrderItem 映射")
        
        normalized_items = []
        
        for item in line_items:
            try:
                # 提取基本信息
                title = item.get("title", "")
                variant_title = item.get("variant_title", "")
                sku = item.get("sku", "")
                quantity = int(item.get("quantity", 1))
                price = float(item.get("price", 0))
                
                # 尝试查找对应的产品和变体
                core_product_id = None
                core_variant_id = None
                
                # 如果有关联的核心订单，优先从 OrderItem 中获取
                order_item = None
                if order_id and order_items_map:
                    match_key = item.get("id")  # line_items_dict 的 id 即 OrderItem.id
                    if match_key is not None and str(match_key) in order_items_map:
                        order_item = order_items_map[str(match_key)]
                    elif match_key is not None and match_key in order_items_map:
                        order_item = order_items_map[match_key]
                    elif sku and sku in order_items_map:
                        order_item = order_items_map[sku]
                    if order_item:
                        if order_item.core_variant_id:
                            core_variant_id = order_item.core_variant_id
                            core_product_id = order_item.core_product_id
                            sku = order_item.sku or sku
                            logger.info(f"✅ 从 OrderItem 获取 core_variant_id: {core_variant_id} (order_item_id={order_item.id})")
                        elif order_item.external_variant_id:
                            # OrderItem.core_variant_id 为空时，通过 Shopify ProductMapping 反查（Shopify 同步可能只做了 SKU 匹配，SKU 空则丢失）
                            shopify_result = await self.db.execute(
                                select(ExternalSystem).where(
                                    and_(
                                        ExternalSystem.tenant_id == tenant_id,
                                        ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                                        ExternalSystem.is_active == True
                                    )
                                )
                            )
                            shopify_system = shopify_result.scalar_one_or_none()
                            if shopify_system:
                                ev_id = str(order_item.external_variant_id).strip()
                                if "ProductVariant/" in ev_id:
                                    ev_id = ev_id.split("ProductVariant/")[-1].split("?")[0]
                                pm_result = await self.db.execute(
                                    select(ProductMapping).where(
                                        and_(
                                            ProductMapping.tenant_id == tenant_id,
                                            ProductMapping.external_system_id == shopify_system.id,
                                            ProductMapping.core_variant_id.isnot(None),
                                            or_(
                                                ProductMapping.external_variant_id == ev_id,
                                                ProductMapping.external_variant_id.like(f"%{ev_id}%")
                                            )
                                        )
                                    ).limit(1)
                                )
                                pm = pm_result.scalar_one_or_none()
                                if pm and pm.core_variant_id:
                                    core_variant_id = pm.core_variant_id
                                    core_product_id = pm.core_product_id
                                    sku = order_item.sku or sku
                                    logger.info(f"✅ 从 Shopify ProductMapping 解析 core_variant_id: external_variant_id={order_item.external_variant_id} -> core_variant_id={core_variant_id}")
                
                # 如果还没找到，通过 SKU 查找变体
                if not core_variant_id and sku:
                    variant_result = await self.db.execute(
                        select(ProductVariant).where(
                            ProductVariant.sku == sku,
                            ProductVariant.tenant_id == tenant_id
                        )
                    )
                    variant = variant_result.scalar_one_or_none()
                    if variant:
                        core_variant_id = variant.id
                        core_product_id = variant.product_id
                
                # 构建规范化项目
                normalized_item = {
                    "core_product_id": core_product_id,
                    "core_variant_id": core_variant_id,  # 确保包含 core_variant_id
                    "quantity": max(1, quantity),
                    "metadata": {
                        "sku": sku,  # 确保包含 sku
                        "title": title,
                        "variant_label": variant_title,
                        "price": price,
                        "source_line_item_id": item.get("id"),
                        "vendor": item.get("vendor"),
                        "product_type": item.get("product_type"),
                    }
                }
                
                normalized_items.append(normalized_item)
                
            except Exception as e:
                logger.error(f"规范化商品项目失败: {item}, 错误: {str(e)}")
                # 添加基本的商品信息
                normalized_items.append({
                    "core_product_id": None,
                    "core_variant_id": None,
                    "quantity": int(item.get("quantity", 1)),
                    "metadata": {
                        "sku": item.get("sku", ""),
                        "title": item.get("title", "未知商品"),
                        "variant_label": item.get("variant_title", ""),
                        "price": float(item.get("price", 0)),
                        "source_line_item_id": item.get("id"),
                    }
                })
        
        return normalized_items

    async def _create_scm_order(
        self, order: Order, decision: Dict[str, Any], tenant_id: int
    ) -> SCMOrder:
        """创建SCM订单"""
        # 生成SCM订单号（使用统一的编号生成服务）
        from app.services.order_number_service import OrderNumberService
        scm_order_number = await OrderNumberService.generate_scm_order_number(self.db, tenant_id)

        # 规范化 line_items（传入 order.id 以便从 OrderItem 获取 core_variant_id）
        normalized_line_items = await self._normalize_line_items_for_scm(
            decision["line_items"], tenant_id, order.id
        )

        # 计算总金额
        total_amount = sum(
            item.get("price", 0) * item.get("quantity", 1)
            for item in decision["line_items"]
        )

        # 提取客户姓名，如果为空则尝试从shipping_address获取
        customer_name = order.customer_name
        if not customer_name and order.shipping_address:
            # 尝试从shipping_address获取客户姓名
            first_name = order.shipping_address.get("firstName") or order.shipping_address.get("first_name", "")
            last_name = order.shipping_address.get("lastName") or order.shipping_address.get("last_name", "")
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                customer_name = full_name
                logger.info(f"从shipping_address提取客户姓名: {customer_name}")
        
        # 如果还是没有，尝试从billing_address获取
        if not customer_name and order.billing_address:
            first_name = order.billing_address.get("firstName") or order.billing_address.get("first_name", "")
            last_name = order.billing_address.get("lastName") or order.billing_address.get("last_name", "")
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                customer_name = full_name
                logger.info(f"从billing_address提取客户姓名: {customer_name}")

        # 创建SCM订单
        # 将 target_system_type 和 target_system_id 添加到 routing_metadata 中
        routing_metadata = decision["routing_metadata"].copy() if decision.get("routing_metadata") else {}
        routing_metadata["target_system_type"] = decision["target_system_type"]
        routing_metadata["target_system_id"] = decision["target_system_id"]
        
        scm_order = SCMOrder(
            tenant_id=tenant_id,
            source_order_id=order.id,  # 兼容：单订单创建时保留，多对多以 ScmOrderSource 为准
            scm_order_number=scm_order_number,
            status=SCMOrderStatus.CREATED.value,
            routing_strategy=decision["routing_metadata"].get("strategy") if decision.get("routing_metadata") else None,
            line_items=normalized_line_items,
            currency=order.currency,
            customer_email=order.customer_email,
            customer_name=customer_name,
            customer_phone=order.customer_phone,
            shipping_address=order.shipping_address,
            billing_address=order.billing_address,
            routing_metadata=routing_metadata,
            # 添加订单追踪链字段
            shopify_order_id=order.shopify_order_id,
            shopify_fulfillment_order_id=order.shopify_fulfillment_order_id,
        )

        self.db.add(scm_order)
        await self.db.flush()
        # 写入多来源关联
        self.db.add(
            ScmOrderSource(
                tenant_id=tenant_id,
                scm_order_id=scm_order.id,
                source_order_id=order.id,
            )
        )
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
            select(SCMOrder)
            .join(ScmOrderSource, ScmOrderSource.scm_order_id == SCMOrder.id)
            .where(
                ScmOrderSource.source_order_id == order_id,
                SCMOrder.tenant_id == tenant_id,
                ScmOrderSource.tenant_id == tenant_id,
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

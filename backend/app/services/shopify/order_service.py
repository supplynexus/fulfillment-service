"""
Shopify 订单同步服务
用于从 Shopify 获取订单并同步到本地数据库
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.order import Order, OrderStatus
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.schemas.order import OrderCreate
from app.core.security import decrypt_data
from app.services.shopify.client import ShopifyGraphQLClient

logger = logging.getLogger(__name__)


class ShopifyOrderService:
    """Shopify 订单同步服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_shopify_credentials(self, tenant_id: int) -> Optional[Dict[str, str]]:
        """从数据库获取 Shopify 凭据"""
        try:
            # 查找 Shopify 外部系统
            result = await self.db.execute(
                select(ExternalSystem).where(
                    ExternalSystem.tenant_id == tenant_id,
                    ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                    ExternalSystem.is_active == True,
                )
            )
            external_system = result.scalar_one_or_none()

            if not external_system:
                logger.warning(
                    f"未找到活跃的 Shopify 外部系统 (tenant_id: {tenant_id})"
                )
                return None

            # 处理凭据 - 支持加密和未加密两种格式
            credentials = {}
            for key, value in external_system.credentials.items():
                try:
                    # 尝试解密（如果是加密的）
                    credentials[key] = decrypt_data(value)
                except Exception:
                    # 如果解密失败，假设是未加密的
                    credentials[key] = value

            return credentials

        except Exception as e:
            logger.error(f"获取 Shopify 凭据失败: {e}")
            return None

    def _convert_shopify_order_to_schema(
        self, order_data: Dict[str, Any]
    ) -> OrderCreate:
        """将 Shopify 订单数据转换为 OrderCreate schema"""

        # 提取基本信息
        shopify_order_id = str(order_data.get("id", ""))
        order_name = order_data.get("name", "")
        email = order_data.get("email", "")

        # 提取客户信息
        customer = order_data.get("customer", {})
        customer_name = (
            f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip()
        )
        customer_phone = customer.get("phone", "")

        # 提取地址信息
        shipping_address = order_data.get("shippingAddress", {})
        billing_address = order_data.get("billingAddress", {})

        # 提取商品信息
        line_items = []
        for item in order_data.get("lineItems", {}).get("edges", []):
            node = item.get("node", {})
            line_items.append(
                {
                    "id": node.get("id"),
                    "title": node.get("title"),
                    "quantity": node.get("quantity"),
                    "variant_title": node.get("variantTitle"),
                    "sku": node.get("sku"),
                    "vendor": node.get("vendor"),
                    "price": node.get("originalUnitPriceSet", {})
                    .get("shopMoney", {})
                    .get("amount"),
                    "currency": node.get("originalUnitPriceSet", {})
                    .get("shopMoney", {})
                    .get("currencyCode"),
                }
            )

        # 提取金额信息
        total_price_set = order_data.get("totalPriceSet", {}).get("shopMoney", {})
        total_amount = float(total_price_set.get("amount", 0))
        currency = total_price_set.get("currencyCode", "USD")

        # 提取状态信息
        financial_status = order_data.get("displayFinancialStatus", "pending")
        fulfillment_status = order_data.get("displayFulfillmentStatus", "unfulfilled")

        # 提取时间信息
        created_at = order_data.get("createdAt")
        if created_at:
            order_date = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        else:
            order_date = datetime.utcnow()

        # 提取备注和其他外部数据
        external_data = {
            "note": order_data.get("note"),
            "tags": order_data.get("tags"),
            "updated_at": order_data.get("updatedAt"),
            "created_at": order_data.get("createdAt"),
        }

        return OrderCreate(
            external_order_id=shopify_order_id,
            external_order_number=order_name,
            external_order_name=order_name,
            status=financial_status,
            total_amount=total_amount,
            currency=currency,
            customer_email=email,
            customer_name=customer_name,
            customer_phone=customer_phone,
            shipping_address=shipping_address,
            billing_address=billing_address,
            line_items=line_items,
            order_date=order_date,
            fulfillment_status=fulfillment_status,
            external_data=external_data,
        )

    async def _get_smart_sync_timestamp(
        self, tenant_id: int, buffer_minutes: int = 5
    ) -> datetime:
        """
        获取智能同步时间戳，防止漏单

        策略：
        1. 优先使用外部系统的 last_sync_at
        2. 如果没有，使用数据库中该租户最新订单的 updated_at
        3. 如果都没有，使用当前时间减去 buffer_minutes
        4. 为了防漏单，将时间戳往前推 buffer_minutes 分钟
        """
        try:
            # 1. 获取外部系统的最后同步时间
            result = await self.db.execute(
                select(ExternalSystem.last_sync_at).where(
                    ExternalSystem.tenant_id == tenant_id,
                    ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                    ExternalSystem.is_active == True,
                )
            )
            external_sync_time = result.scalar_one_or_none()

            if external_sync_time:
                # 往前推 buffer_minutes 分钟，防止漏单
                sync_time = external_sync_time - timedelta(minutes=buffer_minutes)
                logger.info(
                    f"使用外部系统同步时间: {external_sync_time} -> {sync_time}"
                )
                return sync_time

            # 2. 获取数据库中该租户最新订单的更新时间
            result = await self.db.execute(
                select(Order.updated_at)
                .where(Order.tenant_id == tenant_id)
                .order_by(Order.updated_at.desc())
                .limit(1)
            )
            latest_order_time = result.scalar_one_or_none()

            if latest_order_time:
                # 往前推 buffer_minutes 分钟，防止漏单
                sync_time = latest_order_time - timedelta(minutes=buffer_minutes)
                logger.info(f"使用最新订单时间: {latest_order_time} -> {sync_time}")
                return sync_time

            # 3. 默认使用当前时间减去 buffer_minutes
            sync_time = datetime.utcnow() - timedelta(minutes=buffer_minutes)
            logger.info(f"使用默认时间: {sync_time}")
            return sync_time

        except Exception as e:
            logger.error(f"获取智能同步时间戳失败: {e}")
            # 出错时使用保守的时间
            return datetime.utcnow() - timedelta(hours=1)

    async def sync_orders(
        self,
        tenant_id: int,
        query_filter: Optional[str] = None,
        max_orders: Optional[int] = None,
        sync_recent_only: bool = True,
    ) -> Dict[str, Any]:
        """同步 Shopify 订单到本地数据库"""

        try:
            # 获取 Shopify 凭据
            credentials = await self.get_shopify_credentials(tenant_id)
            if not credentials:
                return {
                    "success": False,
                    "error": "无法获取 Shopify 凭据",
                    "orders_fetched": 0,
                    "orders_saved": 0,
                    "orders_updated": 0,
                    "errors": [],
                }

            access_token = credentials.get("access_token")
            store_url = credentials.get("store_url", "")

            # 从 store_url 中提取 shop_name
            if store_url.startswith("https://"):
                shop_name = store_url.replace("https://", "").replace(
                    ".myshopify.com", ""
                )
            else:
                shop_name = store_url.replace(".myshopify.com", "")

            if not access_token or not shop_name:
                return {
                    "success": False,
                    "error": "缺少必要的 Shopify 配置",
                    "orders_fetched": 0,
                    "orders_saved": 0,
                    "orders_updated": 0,
                    "errors": [],
                }

            # 创建 Shopify 客户端
            client = ShopifyGraphQLClient(shop_name, access_token)

            # 设置查询过滤条件
            if sync_recent_only:
                # 使用智能时间戳，防止漏单
                since_time = await self._get_smart_sync_timestamp(
                    tenant_id, buffer_minutes=5
                )
                # 使用带时区的精确时间格式
                time_filter = f"updated_at:>={since_time.isoformat()}"
                if query_filter:
                    query_filter = f"{query_filter} AND {time_filter}"
                else:
                    query_filter = time_filter

                logger.info(f"智能同步时间戳: {since_time.isoformat()}")

            logger.info(
                f"开始同步 Shopify 订单 (tenant_id: {tenant_id}, filter: {query_filter})"
            )

            orders_fetched = 0
            orders_saved = 0
            orders_updated = 0
            errors = []

            # 获取订单
            async for order_data in client.get_all_orders(
                query_filter=query_filter, max_orders=max_orders
            ):
                orders_fetched += 1

                try:
                    # 转换为 schema
                    order_create = self._convert_shopify_order_to_schema(order_data)

                    # 检查订单是否已存在
                    existing_order = await self.db.execute(
                        select(Order).where(
                            Order.external_order_id == order_create.external_order_id,
                            Order.tenant_id == tenant_id,
                        )
                    )
                    existing_order = existing_order.scalar_one_or_none()

                    if existing_order:
                        # 更新现有订单
                        order_dict = order_create.dict(exclude_unset=True)

                        # 确保 external_data 字段被正确处理
                        if "external_data" in order_dict:
                            existing_order.external_data = order_dict["external_data"]
                            logger.debug(
                                f"更新订单 external_data: {order_dict['external_data']}"
                            )

                        # 更新其他字段
                        for field, value in order_dict.items():
                            if field != "external_data":  # external_data 已经单独处理
                                setattr(existing_order, field, value)

                        existing_order.updated_at = datetime.utcnow()
                        orders_updated += 1
                        logger.debug(f"更新订单: {order_create.external_order_id}")
                    else:
                        # 创建新订单
                        order_data_dict = order_create.dict()
                        new_order = Order(tenant_id=tenant_id, **order_data_dict)
                        self.db.add(new_order)
                        orders_saved += 1
                        logger.debug(f"创建新订单: {order_create.external_order_id}")

                    # 提交事务
                    await self.db.commit()

                except Exception as e:
                    await self.db.rollback()
                    error_msg = f"处理订单 {order_data.get('id')} 时出错: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # 更新外部系统的最后同步时间
            await self._update_sync_timestamp(tenant_id)

            result = {
                "success": True,
                "orders_fetched": orders_fetched,
                "orders_saved": orders_saved,
                "orders_updated": orders_updated,
                "errors": errors,
            }

            logger.info(f"订单同步完成: {result}")
            return result

        except Exception as e:
            logger.error(f"订单同步失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "orders_fetched": 0,
                "orders_saved": 0,
                "orders_updated": 0,
                "errors": [str(e)],
            }

    async def _update_sync_timestamp(self, tenant_id: int):
        """更新外部系统的最后同步时间"""
        try:
            await self.db.execute(
                update(ExternalSystem)
                .where(
                    ExternalSystem.tenant_id == tenant_id,
                    ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                    ExternalSystem.is_active == True,
                )
                .values(last_sync_at=datetime.now(timezone.utc))
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"更新同步时间戳失败: {e}")

    async def get_recent_orders(
        self, tenant_id: int, hours: int = 24, limit: int = 100
    ) -> List[Order]:
        """获取最近的订单"""
        try:
            since_time = datetime.utcnow() - timedelta(hours=hours)

            result = await self.db.execute(
                select(Order)
                .where(Order.tenant_id == tenant_id, Order.order_date >= since_time)
                .order_by(Order.order_date.desc())
                .limit(limit)
            )

            return result.scalars().all()

        except Exception as e:
            logger.error(f"获取最近订单失败: {e}")
            return []

    async def get_all_orders(self, tenant_id: int, limit: int = 100) -> List[Order]:
        """获取所有订单"""
        try:
            result = await self.db.execute(
                select(Order)
                .where(Order.tenant_id == tenant_id)
                .order_by(Order.order_date.desc())
                .limit(limit)
            )

            return result.scalars().all()

        except Exception as e:
            logger.error(f"获取所有订单失败: {e}")
            return []

    async def get_orders_by_status(
        self, tenant_id: int, status: str, limit: int = 100
    ) -> List[Order]:
        """根据状态获取订单"""
        try:
            result = await self.db.execute(
                select(Order)
                .where(Order.tenant_id == tenant_id, Order.status == status)
                .order_by(Order.order_date.desc())
                .limit(limit)
            )

            return result.scalars().all()

        except Exception as e:
            logger.error(f"根据状态获取订单失败: {e}")
            return []

    async def get_order_by_id(self, order_id: int, tenant_id: int) -> Optional[Order]:
        """根据ID获取单个订单"""
        try:
            result = await self.db.execute(
                select(Order).where(Order.id == order_id, Order.tenant_id == tenant_id)
            )

            return result.scalar_one_or_none()

        except Exception as e:
            logger.error(f"根据ID获取订单失败: {e}")
            return None

    async def get_orders_paginated(
        self,
        tenant_id: int,
        skip: int = 0,
        limit: int = 20,
        status: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> tuple[List[Order], int]:
        """获取分页订单列表"""
        try:
            from sqlalchemy import func, or_

            # 构建基础查询
            query = select(Order).where(Order.tenant_id == tenant_id)

            # 应用状态过滤
            if status:
                query = query.where(Order.status == status)

            # 应用搜索过滤
            if search:
                search_filter = or_(
                    Order.customer_email.ilike(f"%{search}%"),
                    Order.external_order_id.ilike(f"%{search}%"),
                    Order.external_order_name.ilike(f"%{search}%"),
                    Order.shopify_order_id.ilike(f"%{search}%"),
                    Order.shopify_order_number.ilike(f"%{search}%"),
                )
                query = query.where(search_filter)

            # 获取总数
            count_query = select(func.count()).select_from(query.subquery())
            count_result = await self.db.execute(count_query)
            total = count_result.scalar()

            # 应用排序
            if sort_by == "order_date":
                order_column = Order.order_date
            elif sort_by == "created_at":
                order_column = Order.created_at
            else:
                order_column = Order.created_at  # 默认按创建时间排序

            if sort_order.lower() == "asc":
                query = query.order_by(order_column.asc())
            else:
                query = query.order_by(order_column.desc())

            # 获取分页数据
            orders_result = await self.db.execute(query.offset(skip).limit(limit))

            orders = orders_result.scalars().all()

            return orders, total

        except Exception as e:
            logger.error(f"获取分页订单失败: {e}")
            return [], 0

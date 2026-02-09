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

from app.models.order import Order, OrderItem, OrderStatus
from app.models.shopify_order import ShopifyOrder
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.schemas.order import OrderCreate
from app.core.security import decrypt_data
from app.services.shopify.client import ShopifyGraphQLClient
from app.services.address_validation_service import validate_address
from sqlalchemy import func

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

        # 地址验证（只针对 shipping_address）
        address_validation_status: Optional[str] = None
        address_validation_reason_code: Optional[str] = None
        address_validation_message: Optional[str] = None
        address_last_validated_at: Optional[datetime] = None

        try:
            if shipping_address:
                validation_result = validate_address(shipping_address)
                address_validation_status = validation_result.status
                address_validation_reason_code = validation_result.reason_code
                address_validation_message = validation_result.message
                address_last_validated_at = validation_result.validated_at
            else:
                address_validation_status = "suspicious"
                address_validation_reason_code = "MISSING_SHIPPING_ADDRESS"
                address_validation_message = "缺少收货地址信息，无法完成地址验证"
                address_last_validated_at = datetime.now(timezone.utc)

        except Exception as e:
            # 地址验证失败不能阻断订单同步，只记录状态
            logger.error(f"地址验证失败: {e}")
            address_validation_status = "failed"
            address_validation_reason_code = "VALIDATION_EXCEPTION"
            address_validation_message = str(e)
            address_last_validated_at = datetime.now(timezone.utc)

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
            address_validation_status=address_validation_status,
            address_validation_reason_code=address_validation_reason_code,
            address_validation_message=address_validation_message,
            address_last_validated_at=address_last_validated_at,
        )

    async def _get_smart_sync_timestamp(
        self, tenant_id: int, buffer_minutes: int = 1440, max_days: int = 7
    ) -> datetime:
        """
        获取智能同步时间戳，防止漏单
        
        注意：
        - buffer_minutes 默认设置为 1440 分钟（24小时/1天），以应对：
          * 时区差异问题
          * 系统时间不同步
          * 订单创建时间延迟
          * 跨天订单同步
        - max_days 默认设置为 7 天（一周），确保只同步一周以内的订单

        策略：
        1. 优先使用外部系统的 last_sync_at
        2. 如果没有，使用数据库中该租户最新订单的 updated_at
        3. 如果都没有，使用当前时间减去 buffer_minutes
        4. 为了防漏单，将时间戳往前推 buffer_minutes 分钟
        5. 无论使用哪种策略，最终时间戳不能早于 max_days 天前（确保只同步一周以内的订单）
        """
        try:
            # 计算最大允许的时间戳（一周前）
            max_allowed_time = datetime.now(timezone.utc) - timedelta(days=max_days)
            
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
                # 确保时区正确（如果 last_sync_at 没有时区信息，假设是 UTC）
                if external_sync_time.tzinfo is None:
                    external_sync_time = external_sync_time.replace(tzinfo=timezone.utc)
                sync_time = external_sync_time - timedelta(minutes=buffer_minutes)
                
                # 确保不超过最大时间限制（一周）
                if sync_time < max_allowed_time:
                    sync_time = max_allowed_time
                    logger.info(
                        f"使用外部系统同步时间，但被限制在一周内: {external_sync_time} -> {sync_time} (最大限制: {max_days}天)"
                    )
                else:
                    logger.info(
                        f"使用外部系统同步时间: {external_sync_time} -> {sync_time} (缓冲: {buffer_minutes}分钟)"
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
                # 确保时区正确
                if latest_order_time.tzinfo is None:
                    latest_order_time = latest_order_time.replace(tzinfo=timezone.utc)
                sync_time = latest_order_time - timedelta(minutes=buffer_minutes)
                
                # 确保不超过最大时间限制（一周）
                if sync_time < max_allowed_time:
                    sync_time = max_allowed_time
                    logger.info(
                        f"使用最新订单时间，但被限制在一周内: {latest_order_time} -> {sync_time} (最大限制: {max_days}天)"
                    )
                else:
                    logger.info(
                        f"使用最新订单时间: {latest_order_time} -> {sync_time} (缓冲: {buffer_minutes}分钟)"
                    )
                return sync_time

            # 3. 默认使用当前时间减去 buffer_minutes，但不超过一周
            # 使用 UTC 时间并确保有时区信息
            sync_time = datetime.now(timezone.utc) - timedelta(minutes=buffer_minutes)
            
            # 确保不超过最大时间限制（一周）
            if sync_time < max_allowed_time:
                sync_time = max_allowed_time
                logger.info(
                    f"使用默认时间，但被限制在一周内: {sync_time} (最大限制: {max_days}天)"
                )
            else:
                logger.info(
                    f"使用默认时间: {sync_time} (缓冲: {buffer_minutes}分钟)"
                )
            return sync_time

        except Exception as e:
            logger.error(f"获取智能同步时间戳失败: {e}")
            # 出错时使用保守的时间（一周前），确保只同步一周以内的订单
            max_allowed_time = datetime.now(timezone.utc) - timedelta(days=max_days)
            logger.info(f"出错时使用最大限制时间: {max_allowed_time} (最大限制: {max_days}天)")
            return max_allowed_time

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
                # 默认缓冲 1440 分钟（24小时/1天），以应对时区差异和系统时间不同步
                # 最大限制 7 天（一周），确保只同步一周以内的订单
                since_time = await self._get_smart_sync_timestamp(
                    tenant_id, buffer_minutes=1440, max_days=7
                )
                # 确保时间戳有时区信息（Shopify API 需要 ISO 格式）
                if since_time.tzinfo is None:
                    since_time = since_time.replace(tzinfo=timezone.utc)
                
                # 使用 created_at 和 updated_at 的 OR 条件来获取新创建或更新的订单
                # 这样可以确保不会漏掉新订单（created_at）和更新的订单（updated_at）
                # 格式化为 ISO 格式，确保时区信息正确
                since_time_iso = since_time.isoformat().replace('+00:00', 'Z')
                time_filter = f"created_at:>={since_time_iso} OR updated_at:>={since_time_iso}"
                if query_filter:
                    query_filter = f"{query_filter} AND ({time_filter})"
                else:
                    query_filter = time_filter

                logger.info(f"智能同步时间戳: {since_time_iso}, 查询条件: {query_filter}")
                logger.info(f"⏰ 同步时间范围: 从 {since_time_iso} 到现在 (缓冲: 1440分钟/1天, 最大限制: 7天)")

            logger.info(
                f"开始同步 Shopify 订单 (tenant_id: {tenant_id}, filter: {query_filter})"
            )
            logger.info(f"📋 同步参数: sync_recent_only={sync_recent_only}, max_orders={max_orders}")

            orders_fetched = 0
            orders_saved = 0
            orders_updated = 0
            errors = []

            # 获取订单
            async for order_data in client.get_all_orders(
                query_filter=query_filter, max_orders=max_orders
            ):
                orders_fetched += 1
                
                # 记录获取到的订单信息（用于调试）
                order_id = order_data.get("id", "unknown")
                order_name = order_data.get("name", "unknown")
                created_at = order_data.get("createdAt", "unknown")
                logger.info(f"📦 获取到订单: ID={order_id}, Name={order_name}, CreatedAt={created_at}")

                try:
                    # 转换为 schema（用于 Order 表）
                    order_create = self._convert_shopify_order_to_schema(order_data)

                    # 检查 Order 表中是否已存在
                    existing_order = await self.db.execute(
                        select(Order).where(
                            Order.external_order_id == order_create.external_order_id,
                            Order.tenant_id == tenant_id,
                        )
                    )
                    existing_order = existing_order.scalar_one_or_none()

                    if existing_order:
                        # 更新现有订单
                        logger.info(
                            f"🔄 订单已存在，准备更新: "
                            f"订单ID={existing_order.id}, "
                            f"external_order_id={existing_order.external_order_id}, "
                            f"external_order_number={existing_order.external_order_number}, "
                            f"external_order_name={existing_order.external_order_name}, "
                            f"shopify_order_id={existing_order.shopify_order_id}, "
                            f"tenant_id={existing_order.tenant_id}"
                        )
                        
                        order_dict = order_create.dict(exclude_unset=True)

                        # 处理 line_items：将其存储到 external_data 中
                        line_items = order_dict.pop("line_items", None)
                        if line_items:
                            if not existing_order.external_data:
                                existing_order.external_data = {}
                            existing_order.external_data["line_items"] = line_items
                            logger.debug(f"更新订单 line_items: {len(line_items)} 个商品")

                        # 确保 shopify_order_id 被更新
                        shopify_order_id = order_dict.get("external_order_id")
                        if shopify_order_id:
                            existing_order.shopify_order_id = shopify_order_id
                            logger.info(f"✅ 更新订单 shopify_order_id: {shopify_order_id}")

                        # 确保 external_data 字段被正确处理
                        if "external_data" in order_dict:
                            # 合并 external_data，保留已有的 line_items
                            if existing_order.external_data and "line_items" in existing_order.external_data:
                                order_dict["external_data"]["line_items"] = existing_order.external_data["line_items"]
                            existing_order.external_data = order_dict["external_data"]
                            logger.debug(
                                f"更新订单 external_data: {order_dict['external_data']}"
                            )

                        # 更新其他字段
                        for field, value in order_dict.items():
                            if field not in ["external_data", "external_order_id"]:  # external_data 和 external_order_id 已经单独处理
                                setattr(existing_order, field, value)

                        existing_order.updated_at = datetime.utcnow()
                        orders_updated += 1
                        logger.info(
                            f"✅ 订单更新完成: "
                            f"订单ID={existing_order.id}, "
                            f"external_order_id={existing_order.external_order_id}, "
                            f"external_order_number={existing_order.external_order_number}, "
                            f"external_order_name={existing_order.external_order_name}, "
                            f"shopify_order_id={existing_order.shopify_order_id}"
                        )
                    else:
                        # 创建新订单
                        order_data_dict = order_create.dict()
                        
                        # 处理 line_items：将其存储到 external_data 中，而不是直接传递给 Order 模型
                        line_items = order_data_dict.pop("line_items", None)
                        if line_items and order_data_dict.get("external_data"):
                            # 如果 external_data 已存在，将 line_items 添加到其中
                            order_data_dict["external_data"]["line_items"] = line_items
                        elif line_items:
                            # 如果 external_data 不存在，创建它并添加 line_items
                            if not order_data_dict.get("external_data"):
                                order_data_dict["external_data"] = {}
                            order_data_dict["external_data"]["line_items"] = line_items
                        
                        # 重要：设置 shopify_order_id 字段
                        # external_order_id 是 Shopify 的订单 ID（gid://shopify/Order/xxx）
                        # 需要将其设置为 shopify_order_id
                        shopify_order_id = order_data_dict.get("external_order_id")
                        if shopify_order_id:
                            order_data_dict["shopify_order_id"] = shopify_order_id
                            logger.debug(f"设置 shopify_order_id: {shopify_order_id}")
                        
                        new_order = Order(tenant_id=tenant_id, **order_data_dict)
                        self.db.add(new_order)
                        
                        # 在提交前记录订单信息，用于诊断
                        logger.info(
                            f"📝 准备创建订单: "
                            f"tenant_id={tenant_id}, "
                            f"external_order_id={order_create.external_order_id}, "
                            f"shopify_order_id={shopify_order_id}, "
                            f"external_order_number={order_create.external_order_number}, "
                            f"order_name={order_create.external_order_name}"
                        )
                        
                        orders_saved += 1
                        logger.info(f"✅ 创建新订单: external_order_id={order_create.external_order_id}, shopify_order_id={shopify_order_id}")

                    # 提交事务
                    await self.db.commit()
                    
                    # 提交后验证订单是否真的被保存
                    if not existing_order:
                        # 对于新创建的订单，验证它是否真的在数据库中
                        verify_result = await self.db.execute(
                            select(Order).where(
                                Order.tenant_id == tenant_id,
                                Order.external_order_id == order_create.external_order_id
                            )
                        )
                        verified_order = verify_result.scalar_one_or_none()
                        if verified_order:
                            logger.info(
                                f"✅ 订单验证成功: ID={verified_order.id}, "
                                f"shopify_order_id={verified_order.shopify_order_id}, "
                                f"external_order_id={verified_order.external_order_id}"
                            )
                        else:
                            logger.error(
                                f"❌ 订单验证失败: 订单未找到！"
                                f"external_order_id={order_create.external_order_id}, "
                                f"tenant_id={tenant_id}"
                            )

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
        core_product_id: Optional[int] = None,
    ) -> tuple[List[Order], int]:
        """获取分页订单列表。core_product_id 表示只返回包含该商品的订单。"""
        try:
            from sqlalchemy import func, or_

            # 按商品筛选时用「仅订单 ID」子查询，避免 SELECT DISTINCT 含 JSON 列导致 PostgreSQL 报错
            if core_product_id is not None:
                order_ids_subq = (
                    select(Order.id)
                    .join(OrderItem, Order.id == OrderItem.order_id)
                    .where(
                        Order.tenant_id == tenant_id,
                        OrderItem.tenant_id == tenant_id,
                        OrderItem.core_product_id == core_product_id,
                    )
                    .distinct()
                )
                if status:
                    order_ids_subq = order_ids_subq.where(Order.status == status)
                if search:
                    search_filter = or_(
                        Order.customer_email.ilike(f"%{search}%"),
                        Order.external_order_id.ilike(f"%{search}%"),
                        Order.external_order_name.ilike(f"%{search}%"),
                        Order.external_order_number.ilike(f"%{search}%"),
                        Order.shopify_order_id.ilike(f"%{search}%"),
                        Order.order_number.ilike(f"%{search}%"),
                    )
                    order_ids_subq = order_ids_subq.where(search_filter)
                count_result = await self.db.execute(
                    select(func.count()).select_from(order_ids_subq.subquery())
                )
                total = count_result.scalar() or 0
                # 主查询：只按 ID 过滤，避免 JSON 列参与 DISTINCT
                query = select(Order).where(
                    Order.tenant_id == tenant_id,
                    Order.id.in_(order_ids_subq),
                )
            else:
                query = select(Order).where(Order.tenant_id == tenant_id)
                if status:
                    query = query.where(Order.status == status)
                if search:
                    search_filter = or_(
                        Order.customer_email.ilike(f"%{search}%"),
                        Order.external_order_id.ilike(f"%{search}%"),
                        Order.external_order_name.ilike(f"%{search}%"),
                        Order.external_order_number.ilike(f"%{search}%"),
                        Order.shopify_order_id.ilike(f"%{search}%"),
                        Order.order_number.ilike(f"%{search}%"),
                    )
                    query = query.where(search_filter)
                count_result = await self.db.execute(
                    select(func.count()).select_from(query.subquery())
                )
                total = count_result.scalar() or 0

            # 应用排序
            if sort_by == "order_date":
                order_column = Order.order_date
            elif sort_by == "created_at":
                order_column = Order.created_at
            else:
                order_column = Order.created_at
            if sort_order.lower() == "asc":
                query = query.order_by(order_column.asc())
            else:
                query = query.order_by(order_column.desc())

            orders_result = await self.db.execute(query.offset(skip).limit(limit))
            orders = orders_result.scalars().all()
            return orders, total

        except Exception as e:
            logger.error(f"获取分页订单失败: {e}")
            return [], 0

    async def sync_orders_to_shopify_table(
        self,
        tenant_id: int,
        query_filter: Optional[str] = None,
        max_orders: Optional[int] = None,
        sync_recent_only: bool = True,
    ) -> Dict[str, Any]:
        """
        同步 Shopify 订单到 shopify_orders 表（步骤1）
        这是独立的步骤，只同步到 shopify_orders 表，不涉及 orders 表
        """
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
                # 默认缓冲 1440 分钟（24小时/1天），以应对时区差异和系统时间不同步
                # 最大限制 7 天（一周），确保只同步一周以内的订单
                since_time = await self._get_smart_sync_timestamp(
                    tenant_id, buffer_minutes=1440, max_days=7
                )
                if since_time.tzinfo is None:
                    since_time = since_time.replace(tzinfo=timezone.utc)
                
                since_time_iso = since_time.isoformat().replace('+00:00', 'Z')
                time_filter = f"created_at:>={since_time_iso} OR updated_at:>={since_time_iso}"
                if query_filter:
                    query_filter = f"{query_filter} AND ({time_filter})"
                else:
                    query_filter = time_filter

                logger.info(f"智能同步时间戳: {since_time_iso}, 查询条件: {query_filter}")
                logger.info(f"⏰ 同步时间范围: 从 {since_time_iso} 到现在 (缓冲: 1440分钟/1天, 最大限制: 7天)")

            logger.info(
                f"开始同步 Shopify 订单到 shopify_orders 表 (tenant_id: {tenant_id}, filter: {query_filter})"
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
                
                order_id = order_data.get("id", "unknown")
                order_name = order_data.get("name", "unknown")
                logger.info(f"📦 获取到订单: ID={order_id}, Name={order_name}")

                try:
                    # 准备 ShopifyOrder 表的数据
                    shopify_order_id = order_data.get("id", "")
                    shopify_order_data = self._prepare_shopify_order_data_for_table(order_data, tenant_id)
                    
                    # 检查 ShopifyOrder 表中是否已存在
                    existing_shopify_order = await self.db.execute(
                        select(ShopifyOrder).where(
                            ShopifyOrder.shopify_order_id == shopify_order_id,
                            ShopifyOrder.tenant_id == tenant_id,
                        )
                    )
                    existing_shopify_order = existing_shopify_order.scalar_one_or_none()

                    if existing_shopify_order:
                        # 更新现有的 ShopifyOrder
                        for key, value in shopify_order_data.items():
                            if hasattr(existing_shopify_order, key):
                                setattr(existing_shopify_order, key, value)
                        existing_shopify_order.last_synced_at = datetime.now(timezone.utc)
                        orders_updated += 1
                        logger.info(f"✅ 更新 ShopifyOrder: shopify_order_id={shopify_order_id}, name={shopify_order_data.get('name')}")
                    else:
                        # 创建新的 ShopifyOrder
                        new_shopify_order = ShopifyOrder(**shopify_order_data)
                        self.db.add(new_shopify_order)
                        orders_saved += 1
                        logger.info(f"✅ 创建 ShopifyOrder: shopify_order_id={shopify_order_id}, name={shopify_order_data.get('name')}")

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

            logger.info(f"Shopify 订单同步到 shopify_orders 表完成: {result}")
            return result

        except Exception as e:
            logger.error(f"同步 Shopify 订单到 shopify_orders 表失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "orders_fetched": 0,
                "orders_saved": 0,
                "orders_updated": 0,
                "errors": [str(e)],
            }

    def _prepare_shopify_order_data_for_table(
        self, order_data: Dict[str, Any], tenant_id: int
    ) -> Dict[str, Any]:
        """准备 ShopifyOrder 表的数据"""
        try:
            shopify_order_id = order_data.get("id", "")  # 完整的 GraphQL ID
            order_name = order_data.get("name", "")
            
            # 提取价格信息
            total_price_set = order_data.get("totalPriceSet", {}).get("shopMoney", {})
            total_price = float(total_price_set.get("amount", 0))
            currency = total_price_set.get("currencyCode", "USD")
            
            # 提取客户信息
            customer = order_data.get("customer", {})
            customer_data = {}
            if customer:
                customer_data = {
                    "id": customer.get("id", ""),
                    "email": customer.get("email", ""),
                    "firstName": customer.get("firstName", ""),
                    "lastName": customer.get("lastName", ""),
                    "phone": customer.get("phone", ""),
                    "name": f"{customer.get('firstName', '')} {customer.get('lastName', '')}".strip(),
                }
            
            # 提取地址信息
            shipping_address = order_data.get("shippingAddress", {})
            billing_address = order_data.get("billingAddress", {})
            
            # 提取商品信息（含 variant_id/product_id 用于 ProductMapping 反查核心变体）
            line_items = []
            for item in order_data.get("lineItems", {}).get("edges", []):
                node = item.get("node", {})
                variant_node = node.get("variant") or {}
                product_node = variant_node.get("product") or {}
                sku_value = node.get("sku") or variant_node.get("sku")
                line_items.append({
                    "id": node.get("id"),
                    "variant_id": variant_node.get("id"),  # Shopify ProductVariant GID，用于 ProductMapping 反查 core_variant_id
                    "product_id": product_node.get("id"),  # Shopify Product GID，用于产品级别映射兜底
                    "title": node.get("title"),
                    "quantity": node.get("quantity"),
                    "variant_title": node.get("variantTitle"),
                    "sku": sku_value,
                    "vendor": node.get("vendor"),
                    "price": node.get("originalUnitPriceSet", {})
                    .get("shopMoney", {})
                    .get("amount"),
                    "currency": node.get("originalUnitPriceSet", {})
                    .get("shopMoney", {})
                    .get("currencyCode"),
                })
            
            # 提取状态信息
            financial_status = order_data.get("displayFinancialStatus", "pending")
            fulfillment_status = order_data.get("displayFulfillmentStatus", "unfulfilled")
            
            # 提取标签
            tags = []
            tags_str = order_data.get("tags", [])
            if isinstance(tags_str, list):
                tags = tags_str
            elif isinstance(tags_str, str):
                tags = [tag.strip() for tag in tags_str.split(",") if tag.strip()]
            
            # 提取其他价格信息
            subtotal_price = None
            total_tax = None
            total_shipping = None
            
            if "subtotalPriceSet" in order_data:
                subtotal_price = float(order_data.get("subtotalPriceSet", {}).get("shopMoney", {}).get("amount", 0))
            if "totalTaxSet" in order_data:
                total_tax = float(order_data.get("totalTaxSet", {}).get("shopMoney", {}).get("amount", 0))
            if "totalShippingPriceSet" in order_data:
                total_shipping = float(order_data.get("totalShippingPriceSet", {}).get("shopMoney", {}).get("amount", 0))
            
            return {
                "tenant_id": tenant_id,
                "shopify_order_id": shopify_order_id,
                "name": order_name,
                "confirmation_number": order_data.get("confirmationNumber", ""),
                "financial_status": financial_status,
                "fulfillment_status": fulfillment_status,
                "confirmed": order_data.get("confirmed", False),
                "closed": order_data.get("closed", False),
                "cancelled": bool(
                    order_data.get("cancelledAt") or order_data.get("cancelReason")
                ),
                "currency_code": currency,
                "total_price": total_price,
                "subtotal_price": subtotal_price,
                "total_tax": total_tax,
                "total_shipping": total_shipping,
                "tags": tags,
                "note": order_data.get("note", ""),
                "customer_data": customer_data,
                "billing_address": billing_address,
                "shipping_address": shipping_address,
                "line_items": line_items,
                "fulfillments": order_data.get("fulfillments", []),
                "refunds": order_data.get("refunds", []),
                "raw_data": order_data,
                "last_synced_at": datetime.now(timezone.utc),
            }
        except Exception as e:
            logger.error(f"准备 ShopifyOrder 数据失败: {e}")
            raise

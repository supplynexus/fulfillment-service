"""
Shopify integration service
"""

import httpx
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models.external_system import ExternalSystem, ExternalSystemType
from app.models.order import Order, OrderStatus
from app.models.shopify_order import ShopifyOrder
from app.models.customer import Customer
from app.models.product import Product
from app.core.logging import get_logger

logger = get_logger(__name__)


class ShopifyService:
    """Shopify integration service"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_shopify_system(
        self, tenant_id: int, external_system_id: Optional[int] = None
    ) -> Optional[ExternalSystem]:
        """Get Shopify external system for tenant"""
        try:
            query = select(ExternalSystem).where(
                ExternalSystem.tenant_id == tenant_id,
                ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                ExternalSystem.is_active == True,
            )

            # If specific external_system_id is provided, filter by it
            if external_system_id:
                query = query.where(ExternalSystem.id == external_system_id)

            result = await self.db.execute(query)

            if external_system_id:
                # For specific ID, return one or none
                return result.scalar_one_or_none()
            else:
                # For general query, return the first active one
                return result.scalars().first()

        except Exception as e:
            logger.error(f"Error getting Shopify system for tenant {tenant_id}: {e}")
            return None

    async def fetch_orders(
        self, tenant_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Fetch orders from Shopify"""
        try:
            # Get Shopify system configuration
            shopify_system = await self.get_shopify_system(tenant_id)
            if not shopify_system:
                logger.error(f"No active Shopify system found for tenant {tenant_id}")
                return []

            # Prepare GraphQL query
            query = """
            query($first: Int!) {
                orders(first: $first) {
                    edges {
                        cursor
                        node {
                            id
                            name
                            createdAt
                            updatedAt
                            cancelledAt
                            cancelReason
                            currencyCode
                            currentTotalPriceSet {
                                shopMoney {
                                    amount
                                    currencyCode
                                }
                            }
                            currentSubtotalPriceSet {
                                shopMoney {
                                    amount
                                    currencyCode
                                }
                            }
                            currentTotalTaxSet {
                                shopMoney {
                                    amount
                                    currencyCode
                                }
                            }
                            shippingAddress {
                                country
                                province
                                city
                            }
                            billingAddress {
                                country
                                province
                                city
                            }
                            lineItems(first: 50) {
                                edges {
                                    node {
                                        id
                                        name
                                        quantity
                                        sku
                                        variant {
                                            id
                                            title
                                            sku
                                            price
                                            product {
                                                id
                                                title
                                                handle
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    pageInfo {
                        hasNextPage
                        hasPreviousPage
                        startCursor
                        endCursor
                    }
                }
            }
            """

            # Prepare headers
            headers = {
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": shopify_system.credentials.get(
                    "access_token"
                ),
            }

            # Make API request
            url = f"{shopify_system.base_url}/admin/api/{shopify_system.settings.get('api_version', 'unstable')}/graphql.json"

            response = await self.client.post(
                url,
                headers=headers,
                json={"query": query, "variables": {"first": limit}},
            )

            if response.status_code != 200:
                logger.error(
                    f"Shopify API error: {response.status_code} - {response.text}"
                )
                return []

            data = response.json()

            if "errors" in data:
                logger.error(f"Shopify GraphQL errors: {data['errors']}")
                return []

            # Extract orders
            orders = []
            for edge in data.get("data", {}).get("orders", {}).get("edges", []):
                order_data = edge["node"]
                orders.append(order_data)

            logger.info(f"Successfully fetched {len(orders)} orders from Shopify")
            return orders

        except Exception as e:
            logger.error(f"Error fetching orders from Shopify: {e}")
            return []

    async def parse_order(
        self, order_data: Dict[str, Any], tenant_id: int
    ) -> Optional[Order]:
        """Parse Shopify order data into our Order model"""
        try:
            # 添加详细的调试日志
            logger.info(
                f"🔍 开始解析订单数据: {order_data.get('name', 'unknown') if order_data else 'None'}"
            )

            # 检查 order_data 是否为空
            if not order_data:
                logger.error("❌ 订单数据为空")
                return None

            # Extract basic order information with safe access
            shopify_order_id = ""
            if order_data.get("id"):
                try:
                    shopify_order_id = order_data.get("id", "").split("/")[-1]
                except (AttributeError, IndexError):
                    shopify_order_id = str(order_data.get("id", ""))

            order_name = order_data.get("name", "")
            email = ""  # Not available in Basic plan
            phone = ""  # Not available in Basic plan

            # Parse dates
            created_at = order_data.get("createdAt")
            updated_at = order_data.get("updatedAt")
            cancelled_at = order_data.get("cancelledAt")

            # Parse order_date (required field)
            order_date = None
            try:
                if created_at:
                    from datetime import datetime

                    # Parse ISO format date string
                    order_date = datetime.fromisoformat(
                        created_at.replace("Z", "+00:00")
                    )
                    logger.info(f"✅ 解析订单日期成功: {order_date}")
                else:
                    # Fallback to current time if no date available
                    from datetime import datetime, timezone

                    order_date = datetime.now(timezone.utc)
                    logger.warning(f"⚠️ 订单日期不可用，使用当前时间: {order_date}")
            except Exception as e:
                # Fallback to current time if parsing fails
                from datetime import datetime, timezone

                order_date = datetime.now(timezone.utc)
                logger.warning(
                    f"⚠️ 订单日期解析失败，使用当前时间: {order_date}, 错误: {str(e)}"
                )

            # Parse pricing with comprehensive null checking
            total_price = "0"
            try:
                total_price_set = order_data.get("currentTotalPriceSet")
                if total_price_set and isinstance(total_price_set, dict):
                    shop_money = total_price_set.get("shopMoney")
                    if shop_money and isinstance(shop_money, dict):
                        total_price = shop_money.get("amount", "0")
            except (AttributeError, TypeError):
                logger.warning(f"⚠️ 无法解析 total_price，使用默认值 0")
                total_price = "0"

            subtotal_price = "0"
            try:
                subtotal_price_set = order_data.get("currentSubtotalPriceSet")
                if subtotal_price_set and isinstance(subtotal_price_set, dict):
                    subtotal_shop_money = subtotal_price_set.get("shopMoney")
                    if subtotal_shop_money and isinstance(subtotal_shop_money, dict):
                        subtotal_price = subtotal_shop_money.get("amount", "0")
            except (AttributeError, TypeError):
                logger.warning(f"⚠️ 无法解析 subtotal_price，使用默认值 0")
                subtotal_price = "0"

            total_tax = "0"
            try:
                total_tax_set = order_data.get("currentTotalTaxSet")
                if total_tax_set and isinstance(total_tax_set, dict):
                    tax_shop_money = total_tax_set.get("shopMoney")
                    if tax_shop_money and isinstance(tax_shop_money, dict):
                        total_tax = tax_shop_money.get("amount", "0")
            except (AttributeError, TypeError):
                logger.warning(f"⚠️ 无法解析 total_tax，使用默认值 0")
                total_tax = "0"

            currency = order_data.get("currencyCode", "USD")

            # Determine order status
            if cancelled_at:
                status = OrderStatus.CANCELLED
            else:
                status = OrderStatus.PENDING

            # Parse line items with comprehensive null checking
            line_items = []
            try:
                line_items_data = order_data.get("lineItems")
                if line_items_data and isinstance(line_items_data, dict):
                    edges = line_items_data.get("edges", [])
                    if isinstance(edges, list):
                        for edge in edges:
                            if edge and isinstance(edge, dict) and edge.get("node"):
                                item = edge["node"]
                                if isinstance(item, dict):
                                    variant = (
                                        item.get("variant", {})
                                        if item.get("variant")
                                        and isinstance(item.get("variant"), dict)
                                        else {}
                                    )
                                    product = (
                                        variant.get("product", {})
                                        if variant.get("product")
                                        and isinstance(variant.get("product"), dict)
                                        else {}
                                    )

                                    # 提取 SKU - 优先从 variant.sku 获取，如果没有则从 item.sku 获取
                                    sku = variant.get("sku", "") or item.get("sku", "")
                                    
                                    line_items.append(
                                        {
                                            "id": item.get("id", ""),
                                            "title": item.get("name", ""),
                                            "quantity": item.get("quantity", 0),
                                            "sku": sku,
                                            "variant_title": variant.get("title", ""),
                                            "vendor": product.get("vendor", ""),
                                            "price": item.get("price", variant.get("price", "0")),
                                            "currency": item.get("currency", "USD"),
                                            "product": {
                                                "id": product.get("id", ""),
                                                "title": product.get("title", ""),
                                                "handle": product.get("handle", ""),
                                            },
                                            "variant": {
                                                "id": variant.get("id", ""),
                                                "title": variant.get("title", ""),
                                                "sku": variant.get("sku", ""),
                                            }
                                        }
                                    )
            except (AttributeError, TypeError) as e:
                logger.warning(f"⚠️ 解析 line_items 失败: {e}")
                line_items = []

            # Parse addresses with safe access
            shipping_address = {}
            try:
                if order_data.get("shippingAddress") and isinstance(
                    order_data.get("shippingAddress"), dict
                ):
                    shipping_address = order_data.get("shippingAddress", {})
            except (AttributeError, TypeError):
                shipping_address = {}

            billing_address = {}
            try:
                if order_data.get("billingAddress") and isinstance(
                    order_data.get("billingAddress"), dict
                ):
                    billing_address = order_data.get("billingAddress", {})
            except (AttributeError, TypeError):
                billing_address = {}

            # Create order object (not saved to database yet)
            order = Order(
                tenant_id=tenant_id,
                external_system_id=1,  # Shopify system ID
                external_order_id=shopify_order_id,
                order_number=order_name,
                customer_email=email,
                customer_phone=phone,
                status=status.value,  # Convert enum to string value
                total_amount=float(total_price) if total_price else 0.0,
                subtotal_amount=float(subtotal_price) if subtotal_price else 0.0,
                tax_amount=float(total_tax) if total_tax else 0.0,
                currency=currency,
                # Required fields (NOT NULL in database)
                shipping_address=shipping_address,
                billing_address=billing_address,
                line_items=line_items,
                order_date=order_date,
                # Mixed model: store both structured and raw data
                shopify_raw_data=order_data,  # Complete raw Shopify response
                shopify_processed={
                    "shopify_order_id": shopify_order_id,
                    "line_items": line_items,
                    "shipping_address": shipping_address,
                    "billing_address": billing_address,
                    "cancel_reason": order_data.get("cancelReason"),
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "cancelled_at": cancelled_at,
                },
                external_data={
                    "system_type": "shopify",
                    "shopify_order_id": shopify_order_id,
                    "line_items": line_items,
                    "shipping_address": shipping_address,
                    "billing_address": billing_address,
                    "cancel_reason": order_data.get("cancelReason"),
                },
            )

            logger.info(f"✅ 订单解析成功: {order_name}")
            return order

        except Exception as e:
            logger.error(f"❌ 解析订单失败: {str(e)}", exc_info=True)
            logger.error(f"   订单数据类型: {type(order_data)}")
            logger.error(f"   订单数据内容: {order_data}")
            return None

    async def sync_orders(self, tenant_id: int, limit: int = 10) -> Dict[str, Any]:
        """Sync orders from Shopify"""
        try:
            logger.info(f"Starting Shopify order sync for tenant {tenant_id}")

            # Fetch orders from Shopify
            shopify_orders = await self.fetch_orders(tenant_id, limit)

            if not shopify_orders:
                return {
                    "success": False,
                    "message": "No orders fetched from Shopify",
                    "orders_processed": 0,
                }

            # Parse and process each order
            processed_count = 0
            errors = []

            for order_data in shopify_orders:
                try:
                    # Parse order
                    order = await self.parse_order(order_data, tenant_id)
                    if not order:
                        errors.append(
                            f"Failed to parse order {order_data.get('name', 'unknown')}"
                        )
                        continue

                    # Check if order already exists
                    existing_order = await self.db.execute(
                        select(Order).where(
                            Order.tenant_id == tenant_id,
                            Order.external_order_id == order.external_order_id,
                        )
                    )
                    existing_order = existing_order.scalar_one_or_none()

                    if existing_order:
                        logger.info(
                            f"Order {order.order_number} already exists, skipping"
                        )
                        continue

                    # Save order to database
                    self.db.add(order)
                    await self.db.commit()

                    processed_count += 1
                    logger.info(f"Successfully processed order {order.order_number}")

                except Exception as e:
                    error_msg = f"Error processing order {order_data.get('name', 'unknown')}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
                    await self.db.rollback()

            return {
                "success": True,
                "message": f"Successfully processed {processed_count} orders",
                "orders_processed": processed_count,
                "total_fetched": len(shopify_orders),
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Error in Shopify order sync: {e}")
            return {
                "success": False,
                "message": f"Sync failed: {e}",
                "orders_processed": 0,
            }

    async def test_connection_with_params(
        self,
        shop_id: str,
        access_token: str,
        base_url: str,
        api_version: str = "2024-10",
    ) -> Dict[str, Any]:
        """Test Shopify connection with direct parameters"""
        try:
            # Prepare GraphQL query for shop info
            query = """
            query {
                shop {
                    id
                    name
                    email
                    currencyCode
                    myshopifyDomain
                    plan {
                        displayName
                    }
                }
            }
            """

            # Prepare headers
            if not access_token:
                return {"success": False, "error": "Access Token 未配置"}

            headers = {
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": access_token,
            }

            # Make API request
            url = f"{base_url}/admin/api/{api_version}/graphql.json"

            response = await self.client.post(
                url, headers=headers, json={"query": query}
            )

            if response.status_code == 401:
                return {
                    "success": False,
                    "error": "认证失败：Access Token 无效或已过期",
                }
            elif response.status_code == 403:
                return {
                    "success": False,
                    "error": "权限不足：请检查 Access Token 的权限范围",
                }
            elif response.status_code == 404:
                return {"success": False, "error": "店铺不存在：请检查店铺URL是否正确"}
            elif response.status_code != 200:
                return {
                    "success": False,
                    "error": f"连接失败：HTTP {response.status_code}",
                }

            data = response.json()

            if "errors" in data:
                return {
                    "success": False,
                    "error": f"API错误：{data['errors'][0]['message']}",
                }

            # Extract shop info
            shop_info = data.get("data", {}).get("shop", {})
            if not shop_info:
                return {"success": False, "error": "无法获取店铺信息"}

            return {
                "success": True,
                "shop_info": {
                    "id": shop_info.get("id"),
                    "name": shop_info.get("name"),
                    "email": shop_info.get("email"),
                    "currency_code": shop_info.get("currencyCode"),
                    "myshopify_domain": shop_info.get("myshopifyDomain"),
                    "plan": shop_info.get("plan", {}).get("displayName"),
                },
            }

        except Exception as e:
            logger.error(f"Error testing Shopify connection with params: {e}")
            return {"success": False, "error": f"连接测试失败：{str(e)}"}

    async def test_connection(
        self, tenant_id: int, external_system_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Test Shopify connection by fetching shop information from database"""
        try:
            # Get Shopify system configuration
            shopify_system = await self.get_shopify_system(
                tenant_id, external_system_id
            )
            if not shopify_system:
                return {"success": False, "error": "No active Shopify system found"}

            # Extract parameters from database
            shop_id = shopify_system.external_id
            access_token = shopify_system.credentials.get("access_token")
            base_url = shopify_system.base_url
            api_version = shopify_system.settings.get("api_version", "2024-10")

            # Use the direct parameter method
            return await self.test_connection_with_params(
                shop_id, access_token, base_url, api_version
            )

        except Exception as e:
            logger.error(f"Error testing Shopify connection: {e}")
            return {"success": False, "error": f"连接测试失败：{str(e)}"}

    async def get_products(
        self, shop_id: str, access_token: str, api_version: str = "2024-10"
    ) -> Dict[str, Any]:
        """Get products from Shopify store"""
        try:
            # Prepare GraphQL query for products
            query = """
            query($first: Int!) {
                products(first: $first) {
                    edges {
                        node {
                            id
                            title
                            handle
                            status
                            createdAt
                            updatedAt
                            totalInventory
                            priceRangeV2 {
                                minVariantPrice {
                                    amount
                                    currencyCode
                                }
                            }
                            images(first: 1) {
                                edges {
                                    node {
                                        id
                                        url
                                        altText
                                        width
                                        height
                                    }
                                }
                            }
                            variants(first: 1) {
                                edges {
                                    node {
                                        id
                                        title
                                        price
                                        inventoryQuantity
                                        image {
                                            id
                                            url
                                            altText
                                        }
                                    }
                                }
                            }
                        }
                    }
                    pageInfo {
                        hasNextPage
                        hasPreviousPage
                    }
                }
            }
            """

            # Prepare headers
            if not access_token:
                return {"success": False, "error": "Access Token 未配置"}

            headers = {
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": access_token,
            }

            # Make API request
            base_url = f"https://{shop_id}.myshopify.com"
            url = f"{base_url}/admin/api/{api_version}/graphql.json"

            response = await self.client.post(
                url, headers=headers, json={"query": query, "variables": {"first": 50}}
            )

            if response.status_code == 401:
                return {
                    "success": False,
                    "error": "认证失败：Access Token 无效或已过期",
                }
            elif response.status_code != 200:
                return {
                    "success": False,
                    "error": f"获取商品失败：HTTP {response.status_code}",
                }

            data = response.json()

            if "errors" in data:
                return {
                    "success": False,
                    "error": f"API错误：{data['errors'][0]['message']}",
                }

            # Extract products info
            products_data = data.get("data", {}).get("products", {})
            products = []

            for edge in products_data.get("edges", []):
                product = edge["node"]

                # Extract image information
                images = product.get("images", {}).get("edges", [])
                main_image = None
                if images:
                    image_node = images[0]["node"]
                    main_image = {
                        "id": image_node.get("id"),
                        "url": image_node.get("url"),
                        "alt_text": image_node.get("altText"),
                        "width": image_node.get("width"),
                        "height": image_node.get("height"),
                    }

                # Extract variant information
                variants = product.get("variants", {}).get("edges", [])
                variant_info = None
                if variants:
                    variant_node = variants[0]["node"]
                    variant_image = None
                    if variant_node.get("image"):
                        variant_image = {
                            "id": variant_node["image"].get("id"),
                            "url": variant_node["image"].get("url"),
                            "alt_text": variant_node["image"].get("altText"),
                        }

                    variant_info = {
                        "id": variant_node.get("id"),
                        "title": variant_node.get("title"),
                        "price": variant_node.get("price"),
                        "inventory_quantity": variant_node.get("inventoryQuantity"),
                        "image": variant_image,
                    }

                products.append(
                    {
                        "id": product.get("id"),
                        "title": product.get("title"),
                        "handle": product.get("handle"),
                        "status": product.get("status"),
                        "created_at": product.get("createdAt"),
                        "updated_at": product.get("updatedAt"),
                        "total_inventory": product.get("totalInventory", 0),
                        "price": product.get("priceRangeV2", {})
                        .get("minVariantPrice", {})
                        .get("amount"),
                        "currency": product.get("priceRangeV2", {})
                        .get("minVariantPrice", {})
                        .get("currencyCode"),
                        "image": main_image,
                        "variant": variant_info,
                    }
                )

            return {
                "success": True,
                "products": products,
                "total_count": len(products),
                "page_info": products_data.get("pageInfo", {}),
            }

        except Exception as e:
            logger.error(f"Error getting products: {e}")
            return {"success": False, "error": f"获取商品失败：{str(e)}"}

    async def get_orders(
        self, shop_id: str, access_token: str, api_version: str = "2024-10"
    ) -> Dict[str, Any]:
        """Get orders from Shopify store"""
        try:
            # Prepare GraphQL query for orders
            query = """
            query($first: Int!) {
                orders(first: $first, sortKey: CREATED_AT, reverse: true) {
                    edges {
                        node {
                            id
                            name
                            createdAt
                            updatedAt
                            totalPriceSet {
                                shopMoney {
                                    amount
                                    currencyCode
                                }
                            }
                            displayFulfillmentStatus
                            displayFinancialStatus
                            shippingAddress {
                                country
                                province
                                city
                            }
                            billingAddress {
                                country
                                province
                                city
                            }
                            customer {
                                id
                                firstName
                                lastName
                                email
                                phone
                            }
                            lineItems(first: 10) {
                                edges {
                                    node {
                                        id
                                        title
                                        quantity
                                        sku
                                        variantTitle
                                        vendor
                                        originalUnitPriceSet {
                                            shopMoney {
                                                amount
                                                currencyCode
                                            }
                                        }
                                        product {
                                            id
                                            title
                                            handle
                                        }
                                    }
                                }
                            }
                        }
                    }
                    pageInfo {
                        hasNextPage
                        hasPreviousPage
                    }
                }
            }
            """

            # Prepare headers
            if not access_token:
                return {"success": False, "error": "Access Token 未配置"}

            headers = {
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": access_token,
            }

            # Make API request
            base_url = f"https://{shop_id}.myshopify.com"
            url = f"{base_url}/admin/api/{api_version}/graphql.json"

            response = await self.client.post(
                url, headers=headers, json={"query": query, "variables": {"first": 50}}
            )

            if response.status_code == 401:
                return {
                    "success": False,
                    "error": "认证失败：Access Token 无效或已过期",
                }
            elif response.status_code != 200:
                return {
                    "success": False,
                    "error": f"获取订单失败：HTTP {response.status_code}",
                }

            data = response.json()

            # Check for errors, but allow partial data if core information is available
            if "errors" in data:
                # Check if we have any orders data despite errors
                orders_data = data.get("data", {}).get("orders", {})
                if not orders_data.get("edges"):
                    # No orders data at all, this is a real error
                    return {
                        "success": False,
                        "error": f"API错误：{data['errors'][0]['message']}",
                    }
                # We have orders data, log the errors but continue processing
                logger.warning(
                    f"Shopify API returned errors but has data: {data['errors']}"
                )
            else:
                # Extract orders info
                orders_data = data.get("data", {}).get("orders", {})
            orders = []

            for edge in orders_data.get("edges", []):
                order = edge["node"]
                orders.append(
                    {
                        "id": order.get("id"),
                        "name": order.get("name"),
                        "email": "",  # Not available in Basic plan
                        "created_at": order.get("createdAt"),
                        "updated_at": order.get("updatedAt"),
                        "total_price": order.get("totalPriceSet", {})
                        .get("shopMoney", {})
                        .get("amount"),
                        "currency": order.get("totalPriceSet", {})
                        .get("shopMoney", {})
                        .get("currencyCode"),
                        "fulfillment_status": order.get("displayFulfillmentStatus"),
                        "financial_status": order.get("displayFinancialStatus"),
                        "shipping_address": order.get("shippingAddress"),
                        "billing_address": order.get("billingAddress"),
                        "customer": (
                            {
                                "id": order.get("customer", {}).get("id"),
                                "name": f"{order.get('customer', {}).get('firstName', '')} {order.get('customer', {}).get('lastName', '')}".strip(),
                                "email": order.get("customer", {}).get("email"),
                            }
                            if order.get("customer")
                            else None
                        ),
                        "line_items": [
                            {
                                "id": item.get("id"),
                                "title": item.get("title"),
                                "quantity": item.get("quantity"),
                                "sku": item.get("sku"),
                                "variant_title": item.get("variantTitle"),
                                "vendor": item.get("vendor"),
                                "price": item.get("originalUnitPriceSet", {})
                                .get("shopMoney", {})
                                .get("amount"),
                                "currency": item.get("originalUnitPriceSet", {})
                                .get("shopMoney", {})
                                .get("currencyCode"),
                                "product": item.get("product", {}),
                            }
                            for item in [
                                edge["node"]
                                for edge in order.get("lineItems", {}).get("edges", [])
                            ]
                        ],
                        "line_items_count": len(
                            order.get("lineItems", {}).get("edges", [])
                        ),
                    }
                )

            return {
                "success": True,
                "orders": orders,
                "total_count": len(orders),
                "page_info": orders_data.get("pageInfo", {}),
            }

        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            return {"success": False, "error": f"获取订单失败：{str(e)}"}

    async def sync_orders_to_shopify_table(
        self,
        shop_id: str,
        access_token: str,
        tenant_id: int,
        external_system_id: int,
        api_version: str = "2024-10",
    ) -> Dict[str, Any]:
        """Sync orders from Shopify to shopify_orders table (first step)"""
        try:
            logger.info(
                f"🔍 开始同步订单到 Shopify 表 - shop_id: {shop_id}, tenant_id: {tenant_id}, external_system_id: {external_system_id}"
            )

            # First, get orders from Shopify
            orders_result = await self.get_orders(shop_id, access_token, api_version)

            if not orders_result["success"]:
                logger.error(
                    f"❌ 获取订单失败 - shop_id: {shop_id}, error: {orders_result.get('error')}"
                )
                return {
                    "success": False,
                    "error": orders_result.get(
                        "error", "Failed to fetch orders from Shopify"
                    ),
                }

            orders = orders_result.get("orders", [])
            logger.info(f"✅ 从 Shopify 获取到 {len(orders)} 个订单")

            if not orders:
                return {
                    "success": True,
                    "orders_synced": 0,
                    "orders_updated": 0,
                    "total_processed": 0,
                    "message": "No orders to sync",
                }

            # Process each order
            orders_synced = 0
            orders_updated = 0
            total_processed = 0

            for order_data in orders:
                try:
                    total_processed += 1
                    shopify_order_id = order_data.get("id", "").split("/")[
                        -1
                    ]  # Remove "gid://shopify/Order/" prefix

                    logger.info(
                        f"🔍 处理订单 - shopify_order_id: {shopify_order_id}, name: {order_data.get('name')}"
                    )

                    # Check if order already exists in shopify_orders table
                    existing_order = await self.db.execute(
                        select(ShopifyOrder).where(
                            ShopifyOrder.tenant_id == tenant_id,
                            ShopifyOrder.shopify_order_id == f"gid://shopify/Order/{shopify_order_id}",
                        )
                    )
                    existing_order = existing_order.scalar_one_or_none()

                    if existing_order:
                        # Update existing order
                        logger.info(f"🔄 更新现有 Shopify 订单 - order_id: {existing_order.id}")

                        # Prepare order data for ShopifyOrder table
                        shopify_order_data = self._prepare_shopify_order_data(
                            order_data, tenant_id
                        )

                        # Update existing order
                        for key, value in shopify_order_data.items():
                            if hasattr(existing_order, key):
                                setattr(existing_order, key, value)

                        existing_order.updated_at = func.now()
                        existing_order.last_synced_at = func.now()
                        orders_updated += 1
                        logger.info(f"✅ Shopify 订单更新完成 - order_id: {existing_order.id}")
                    else:
                        # Create new Shopify order
                        logger.info(
                            f"➕ 创建新 Shopify 订单 - shopify_order_id: {shopify_order_id}"
                        )

                        # Prepare order data for ShopifyOrder table
                        shopify_order_data = self._prepare_shopify_order_data(
                            order_data, tenant_id
                        )

                        # Create new Shopify order
                        new_shopify_order = ShopifyOrder(**shopify_order_data)
                        self.db.add(new_shopify_order)
                        orders_synced += 1
                        logger.info(
                            f"✅ 新 Shopify 订单创建完成 - shopify_order_id: {shopify_order_id}"
                        )

                    # Commit after each order to ensure data consistency
                    await self.db.commit()

                except Exception as e:
                    logger.error(
                        f"❌ 处理 Shopify 订单失败 - shopify_order_id: {shopify_order_id}, error: {str(e)}",
                        exc_info=True,
                    )
                    await self.db.rollback()
                    continue

            logger.info(
                f"✅ Shopify 订单同步完成 - 新增: {orders_synced}, 更新: {orders_updated}, 总处理: {total_processed}"
            )

            return {
                "success": True,
                "orders_synced": orders_synced,
                "orders_updated": orders_updated,
                "total_processed": total_processed,
                "message": f"Successfully synced {orders_synced} new Shopify orders and updated {orders_updated} existing Shopify orders",
            }

        except Exception as e:
            logger.error(
                f"❌ Shopify 订单同步异常 - shop_id: {shop_id}, error: {str(e)}", exc_info=True
            )
            await self.db.rollback()
            return {"success": False, "error": f"Shopify sync failed: {str(e)}"}

    async def sync_orders_to_database(
        self,
        shop_id: str,
        access_token: str,
        tenant_id: int,
        external_system_id: int,
        api_version: str = "2024-10",
    ) -> Dict[str, Any]:
        """Sync orders from Shopify to database"""
        try:
            logger.info(
                f"🔍 开始同步订单到数据库 - shop_id: {shop_id}, tenant_id: {tenant_id}, external_system_id: {external_system_id}"
            )

            # First, get orders from Shopify
            orders_result = await self.get_orders(shop_id, access_token, api_version)

            if not orders_result["success"]:
                logger.error(
                    f"❌ 获取订单失败 - shop_id: {shop_id}, error: {orders_result.get('error')}"
                )
                return {
                    "success": False,
                    "error": orders_result.get(
                        "error", "Failed to fetch orders from Shopify"
                    ),
                }

            orders = orders_result.get("orders", [])
            logger.info(f"✅ 从 Shopify 获取到 {len(orders)} 个订单")

            if not orders:
                return {
                    "success": True,
                    "orders_synced": 0,
                    "orders_updated": 0,
                    "total_processed": 0,
                    "message": "No orders to sync",
                }

            # Process each order
            orders_synced = 0
            orders_updated = 0
            total_processed = 0

            for order_data in orders:
                try:
                    total_processed += 1
                    shopify_order_id = order_data.get("id", "").split("/")[
                        -1
                    ]  # Remove "gid://shopify/Order/" prefix

                    logger.info(
                        f"🔍 处理订单 - shopify_order_id: {shopify_order_id}, name: {order_data.get('name')}"
                    )

                    # Check if order already exists
                    existing_order = await self.db.execute(
                        select(Order).where(
                            Order.tenant_id == tenant_id,
                            Order.external_order_id == shopify_order_id,
                        )
                    )
                    existing_order = existing_order.scalar_one_or_none()

                    if existing_order:
                        # Update existing order
                        logger.info(f"🔄 更新现有订单 - order_id: {existing_order.id}")

                        # Prepare order data for database
                        order_db_data = self._prepare_order_for_database(
                            order_data, tenant_id, external_system_id
                        )

                        # Update existing order
                        for key, value in order_db_data.items():
                            if hasattr(existing_order, key):
                                setattr(existing_order, key, value)

                        existing_order.updated_at = func.now()
                        orders_updated += 1
                        logger.info(f"✅ 订单更新完成 - order_id: {existing_order.id}")
                    else:
                        # Create new order
                        logger.info(
                            f"➕ 创建新订单 - shopify_order_id: {shopify_order_id}"
                        )

                        # Prepare order data for database
                        order_db_data = self._prepare_order_for_database(
                            order_data, tenant_id, external_system_id
                        )

                        # Create new order
                        new_order = Order(**order_db_data)
                        self.db.add(new_order)
                        orders_synced += 1
                        logger.info(
                            f"✅ 新订单创建完成 - shopify_order_id: {shopify_order_id}"
                        )

                    # Commit after each order to ensure data consistency
                    await self.db.commit()

                except Exception as e:
                    logger.error(
                        f"❌ 处理订单失败 - shopify_order_id: {shopify_order_id}, error: {str(e)}",
                        exc_info=True,
                    )
                    await self.db.rollback()
                    continue

            logger.info(
                f"✅ 同步完成 - 新增: {orders_synced}, 更新: {orders_updated}, 总处理: {total_processed}"
            )

            return {
                "success": True,
                "orders_synced": orders_synced,
                "orders_updated": orders_updated,
                "total_processed": total_processed,
                "message": f"Successfully synced {orders_synced} new orders and updated {orders_updated} existing orders",
            }

        except Exception as e:
            logger.error(
                f"❌ 同步订单异常 - shop_id: {shop_id}, error: {str(e)}", exc_info=True
            )
            await self.db.rollback()
            return {"success": False, "error": f"Sync failed: {str(e)}"}

    def _parse_order_date(self, date_string: Optional[str]) -> datetime:
        """Parse order date string to datetime object"""
        try:
            if date_string:
                from datetime import datetime

                # Parse ISO format date string
                return datetime.fromisoformat(date_string.replace("Z", "+00:00"))
            else:
                # Fallback to current time if no date available
                from datetime import datetime, timezone

                return datetime.now(timezone.utc)
        except Exception as e:
            # Fallback to current time if parsing fails
            from datetime import datetime, timezone

            logger.warning(f"⚠️ 订单日期解析失败，使用当前时间: {str(e)}")
            return datetime.now(timezone.utc)

    def _prepare_shopify_order_data(
        self, order_data: Dict[str, Any], tenant_id: int
    ) -> Dict[str, Any]:
        """Prepare order data for ShopifyOrder table insertion"""
        try:
            shopify_order_id = order_data.get("id", "")  # Keep full GraphQL ID
            order_name = order_data.get("name", "")
            
            # Parse pricing
            if "total_price" in order_data:
                # Simplified structure from get_orders
                total_price = order_data.get("total_price", "0")
                currency = order_data.get("currency", "USD")
            else:
                # Full structure from GraphQL
                total_price = (
                    order_data.get("totalPriceSet", {})
                    .get("shopMoney", {})
                    .get("amount", "0")
                )
                currency = (
                    order_data.get("totalPriceSet", {})
                    .get("shopMoney", {})
                    .get("currencyCode", "USD")
                )

            # Parse customer info
            customer = order_data.get("customer", {})
            customer_data = {}
            if customer:
                if isinstance(customer, dict):
                    customer_data = {
                        "id": customer.get("id", ""),
                        "email": customer.get("email", ""),
                        "firstName": customer.get("firstName", ""),
                        "lastName": customer.get("lastName", ""),
                        "phone": customer.get("phone", ""),
                        "acceptsMarketing": customer.get("acceptsMarketing", False),
                    }

            # Parse addresses
            if "shipping_address" in order_data:
                # Simplified structure
                shipping_address = order_data.get("shipping_address", {})
                billing_address = order_data.get("billing_address", {})
            else:
                # Full structure
                shipping_address = order_data.get("shippingAddress", {})
                billing_address = order_data.get("billingAddress", {})

            # Parse line items
            line_items = []
            if "line_items" in order_data and order_data.get("line_items"):
                # New structure with detailed line items
                for item in order_data.get("line_items", []):
                    line_items.append({
                        "id": item.get("id", ""),
                        "title": item.get("title", ""),
                        "quantity": item.get("quantity", 0),
                        "sku": item.get("sku", ""),
                        "variant_title": item.get("variant_title", ""),
                        "vendor": item.get("vendor", ""),
                        "price": item.get("price", "0"),
                        "currency": item.get("currency", currency),
                        "product": item.get("product", {}),
                    })
            elif "lineItems" in order_data:
                # Full structure - parse line items
                for edge in order_data.get("lineItems", {}).get("edges", []):
                    item = edge["node"]
                    line_items.append({
                        "id": item.get("id", ""),
                        "title": item.get("title", ""),
                        "quantity": item.get("quantity", 0),
                        "price": item.get("originalUnitPriceSet", {})
                        .get("shopMoney", {})
                        .get("amount", "0"),
                        "currency": item.get("originalUnitPriceSet", {})
                        .get("shopMoney", {})
                        .get("currencyCode", "USD"),
                    })

            # Parse status
            if "fulfillment_status" in order_data:
                # Simplified structure
                fulfillment_status = order_data.get("fulfillment_status", "")
                financial_status = order_data.get("financial_status", "")
            else:
                # Full structure
                fulfillment_status = order_data.get("displayFulfillmentStatus", "")
                financial_status = order_data.get("displayFinancialStatus", "")

            # Parse tags
            tags = []
            if "tags" in order_data and order_data.get("tags"):
                if isinstance(order_data.get("tags"), list):
                    tags = order_data.get("tags", [])
                else:
                    # If tags is a string, split by comma
                    tags = [tag.strip() for tag in order_data.get("tags", "").split(",") if tag.strip()]

            return {
                "tenant_id": tenant_id,
                "shopify_order_id": shopify_order_id,
                "name": order_name,
                "confirmation_number": order_data.get("confirmationNumber", ""),
                "financial_status": financial_status,
                "fulfillment_status": fulfillment_status,
                "confirmed": order_data.get("confirmed", False),
                "closed": order_data.get("closed", False),
                "cancelled": order_data.get("cancelled", False),
                "currency_code": currency,
                "total_price": float(total_price) if total_price else 0.0,
                "subtotal_price": float(order_data.get("subtotalPrice", 0)) if order_data.get("subtotalPrice") else None,
                "total_tax": float(order_data.get("totalTax", 0)) if order_data.get("totalTax") else None,
                "total_shipping": float(order_data.get("totalShippingPriceSet", {}).get("shopMoney", {}).get("amount", 0)) if order_data.get("totalShippingPriceSet") else None,
                "tags": tags,
                "note": order_data.get("note", ""),
                "customer_data": customer_data,
                "billing_address": billing_address,
                "shipping_address": shipping_address,
                "line_items": line_items,
                "fulfillments": order_data.get("fulfillments", []),
                "refunds": order_data.get("refunds", []),
                "raw_data": order_data,
                "last_synced_at": func.now(),
            }

        except Exception as e:
            logger.error(f"❌ 准备 Shopify 订单数据失败 - error: {str(e)}", exc_info=True)
            raise e

    def _prepare_order_for_database(
        self, order_data: Dict[str, Any], tenant_id: int, external_system_id: int
    ) -> Dict[str, Any]:
        """Prepare order data for database insertion"""
        try:
            shopify_order_id = order_data.get("id", "").split("/")[
                -1
            ]  # Remove "gid://shopify/Order/" prefix
            order_name = order_data.get("name", "")
            email = order_data.get("email", "")  # Use email from order_data

            # Parse pricing - handle both simplified and full data structures
            if "total_price" in order_data:
                # Simplified structure from get_orders
                total_price = order_data.get("total_price", "0")
                currency = order_data.get("currency", "USD")
            else:
                # Full structure from GraphQL
                total_price = (
                    order_data.get("totalPriceSet", {})
                    .get("shopMoney", {})
                    .get("amount", "0")
                )
                currency = (
                    order_data.get("totalPriceSet", {})
                    .get("shopMoney", {})
                    .get("currencyCode", "USD")
                )

            # Parse customer info - handle both simplified and full data structures
            customer = order_data.get("customer", {})
            customer_name = ""
            customer_email = ""
            if customer:
                if isinstance(customer, dict):
                    if "name" in customer and customer.get("name"):
                        # Simplified structure with name
                        customer_name = customer.get("name", "")
                        customer_email = customer.get("email", "")
                    elif "firstName" in customer or "lastName" in customer:
                        # Full structure
                        first_name = customer.get("firstName", "")
                        last_name = customer.get("lastName", "")
                        customer_name = f"{first_name} {last_name}".strip()
                        customer_email = customer.get("email", "")
                    else:
                        # Simplified structure without name
                        customer_name = customer.get("name", "")
                        customer_email = customer.get("email", "")

            # Parse addresses - handle both simplified and full data structures
            if "shipping_address" in order_data:
                # Simplified structure (from get_orders)
                shipping_address = order_data.get("shipping_address", {})
                billing_address = order_data.get("billing_address", {})
            else:
                # Full structure (from GraphQL)
                shipping_address = order_data.get("shippingAddress", {})
                billing_address = order_data.get("billingAddress", {})

            # Parse line items - handle both simplified and full data structures
            line_items = []
            if "line_items" in order_data and order_data.get("line_items"):
                # New structure with detailed line items
                for item in order_data.get("line_items", []):
                    # 提取 SKU - 优先从 variant.sku 获取，如果没有则从 item.sku 获取
                    variant = item.get("variant", {})
                    sku = variant.get("sku", "") or item.get("sku", "")
                    
                    # 提取 variant_title - 优先从 variant.title 获取，如果没有则从 item.variant_title 获取
                    variant_title = variant.get("title", "") or item.get("variant_title", "")
                    
                    # 提取 vendor - 优先从 product.vendor 获取，如果没有则从 item.vendor 获取
                    product = item.get("product", {})
                    vendor = product.get("vendor", "") or item.get("vendor", "")
                    
                    line_items.append(
                        {
                            "id": item.get("id", ""),
                            "title": item.get("title", ""),
                            "quantity": item.get("quantity", 0),
                            "sku": sku,
                            "variant_title": variant_title,
                            "vendor": vendor,
                            "price": item.get("price", "0"),
                            "currency": item.get("currency", currency),
                            "product": product,
                        }
                    )
            elif "line_items_count" in order_data:
                # Simplified structure - create basic line items info
                line_items_count = order_data.get("line_items_count", 0)
                if line_items_count > 0:
                    # Create placeholder line items based on count
                    for i in range(line_items_count):
                        line_items.append(
                            {
                                "title": f"商品 {i+1}",
                                "quantity": 1,
                                "price": "0.00",
                                "currency": currency,
                            }
                        )
            else:
                # Full structure - parse line items
                for edge in order_data.get("lineItems", {}).get("edges", []):
                    item = edge["node"]
                    line_items.append(
                        {
                            "title": item.get("title", ""),
                            "quantity": item.get("quantity", 0),
                            "price": item.get("originalUnitPriceSet", {})
                            .get("shopMoney", {})
                            .get("amount", "0"),
                            "currency": item.get("originalUnitPriceSet", {})
                            .get("shopMoney", {})
                            .get("currencyCode", "USD"),
                        }
                    )

            # Determine order status based on fulfillment and financial status
            # Handle both simplified and full data structures
            if "fulfillment_status" in order_data:
                # Simplified structure
                fulfillment_status = order_data.get("fulfillment_status", "")
                financial_status = order_data.get("financial_status", "")
            else:
                # Full structure
                fulfillment_status = order_data.get("displayFulfillmentStatus", "")
                financial_status = order_data.get("displayFinancialStatus", "")

            if fulfillment_status == "FULFILLED":
                status = OrderStatus.FULFILLED
            elif fulfillment_status == "PARTIALLY_FULFILLED":
                status = OrderStatus.PROCESSING
            elif financial_status == "PAID":
                status = OrderStatus.PROCESSING  # 已付款但未发货的订单设为处理中
            else:
                status = OrderStatus.PENDING

            return {
                "tenant_id": tenant_id,
                "external_system_id": external_system_id,
                "external_order_id": shopify_order_id,
                "external_order_name": order_name,  # Add external_order_name field
                "order_number": order_name,
                "status": status.value,  # Convert enum to string
                "total_amount": float(total_price) if total_price else 0.0,
                "currency": currency,
                "customer_email": customer_email
                or email
                or "no-email@example.com",  # Use customer_email first, then email, then default
                "customer_name": customer_name,
                "shipping_address": shipping_address,
                "billing_address": billing_address,
                "line_items": line_items,
                "shopify_raw_data": order_data,
                "shopify_processed": {
                    "shopify_order_id": shopify_order_id,
                    "fulfillment_status": fulfillment_status,
                    "financial_status": financial_status,
                    "line_items": line_items,
                    "shipping_address": shipping_address,
                    "billing_address": billing_address,
                    "created_at": order_data.get("createdAt")
                    or order_data.get("created_at"),
                    "updated_at": order_data.get("updatedAt")
                    or order_data.get("updated_at"),
                },
                "external_data": {
                    "system_type": "shopify",
                    "shopify_order_id": shopify_order_id,
                    "fulfillment_status": fulfillment_status,
                    "financial_status": financial_status,
                    "line_items": line_items,
                    "shipping_address": shipping_address,
                    "billing_address": billing_address,
                },
                "order_date": self._parse_order_date(
                    order_data.get("createdAt")
                ),  # Parse date properly
                "fulfillment_status": fulfillment_status,
                "shopify_order_id": f"gid://shopify/Order/{shopify_order_id}",  # 添加完整的Shopify订单ID
            }

        except Exception as e:
            logger.error(f"❌ 准备订单数据失败 - error: {str(e)}", exc_info=True)
            raise e

    async def get_order_details(
        self,
        shop_id: str,
        order_id: str,
        access_token: str,
        api_version: str = "2024-10",
    ) -> Dict[str, Any]:
        """Get detailed information for a specific Shopify order"""
        try:
            logger.info(
                f"🔍 开始获取 Shopify 订单详情: shop_id={shop_id}, order_id={order_id}"
            )

            # Prepare GraphQL query for order details
            query = """
            query($id: ID!) {
                order(id: $id) {
                    id
                    name
                    email
                    phone
                    createdAt
                    updatedAt
                    processedAt
                    totalPriceSet {
                        shopMoney {
                            amount
                            currencyCode
                        }
                    }
                    subtotalPriceSet {
                        shopMoney {
                            amount
                            currencyCode
                        }
                    }
                    totalTaxSet {
                        shopMoney {
                            amount
                            currencyCode
                        }
                    }
                    totalShippingPriceSet {
                        shopMoney {
                            amount
                            currencyCode
                        }
                    }
                    displayFulfillmentStatus
                    displayFinancialStatus
                    tags
                    note
                    customer {
                        id
                        firstName
                        lastName
                        email
                        phone
                        defaultAddress {
                            id
                            firstName
                            lastName
                            company
                            address1
                            address2
                            city
                            province
                            country
                            zip
                            phone
                        }
                    }
                    shippingAddress {
                        id
                        firstName
                        lastName
                        company
                        address1
                        address2
                        city
                        province
                        country
                        zip
                        phone
                    }
                    billingAddress {
                        id
                        firstName
                        lastName
                        company
                        address1
                        address2
                        city
                        province
                        country
                        zip
                        phone
                    }
                    lineItems(first: 50) {
                        edges {
                            node {
                                id
                                title
                                quantity
                                originalUnitPriceSet {
                                    shopMoney {
                                        amount
                                        currencyCode
                                    }
                                }
                                discountedUnitPriceSet {
                                    shopMoney {
                                        amount
                                        currencyCode
                                    }
                                }
                                variant {
                                    id
                                    title
                                    sku
                                    image {
                                        id
                                        url
                                        altText
                                    }
                                }
                                product {
                                    id
                                    title
                                    handle
                                    vendor
                                }
                            }
                        }
                    }
                    fulfillments {
                        id
                        status
                        trackingInfo {
                            number
                            url
                            company
                        }
                        createdAt
                        updatedAt
                    }
                    refunds {
                        id
                        createdAt
                        note
                        totalRefundedSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                    }
                }
            }
            """

            # Prepare variables
            variables = {"id": f"gid://shopify/Order/{order_id}"}

            # Make GraphQL request
            response = await self.client.post(
                f"https://{shop_id}.myshopify.com/admin/api/{api_version}/graphql.json",
                headers={
                    "X-Shopify-Access-Token": access_token,
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables},
            )

            if response.status_code != 200:
                logger.error(f"❌ Shopify API 请求失败: status={response.status_code}")
                return {
                    "success": False,
                    "error": f"Shopify API request failed with status {response.status_code}",
                }

            data = response.json()

            if "errors" in data:
                logger.error(f"❌ Shopify GraphQL 错误: {data['errors']}")
                return {
                    "success": False,
                    "error": f"GraphQL errors: {data['errors']}",
                }

            order_data = data.get("data", {}).get("order")
            if not order_data:
                logger.error(f"❌ 未找到订单: order_id={order_id}")
                return {
                    "success": False,
                    "error": f"Order not found: {order_id}",
                }

            logger.info(f"✅ Shopify 订单详情获取成功: order_id={order_id}")

            return {
                "success": True,
                "order": order_data,
            }

        except Exception as e:
            logger.error(f"❌ 获取 Shopify 订单详情失败: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get order details: {str(e)}",
            }

    async def get_product_json(
        self,
        shop_id: str,
        product_id: str,
        access_token: str,
        api_version: str = "2024-10",
    ) -> Dict[str, Any]:
        """Get complete Shopify product JSON data"""
        try:
            logger.info(
                f"🔍 开始获取 Shopify 商品完整 JSON: shop_id={shop_id}, product_id={product_id}"
            )

            # Prepare GraphQL query for complete product data
            query = """
            query($id: ID!) {
                product(id: $id) {
                    id
                    title
                    handle
                    description
                    descriptionHtml
                    vendor
                    productType
                    createdAt
                    updatedAt
                    publishedAt
                    tags
                    status
                    onlineStoreUrl
                    onlineStorePreviewUrl
                    options {
                        id
                        name
                        values
                        position
                    }
                    images(first: 50) {
                        edges {
                            node {
                                id
                                url
                                altText
                                width
                                height
                            }
                        }
                    }
                    variants(first: 50) {
                        edges {
                            node {
                                id
                                title
                                sku
                                barcode
                                price
                                compareAtPrice
                                inventoryQuantity
                                inventoryPolicy
                                selectedOptions {
                                    name
                                    value
                                }
                                taxable
                                taxCode
                                position
                                createdAt
                                updatedAt
                                image {
                                    id
                                    url
                                    altText
                                    width
                                    height
                                }
                            }
                        }
                    }
                    seo {
                        title
                        description
                    }
                    metafields(first: 50) {
                        edges {
                            node {
                                id
                                namespace
                                key
                                value
                                type
                                description
                            }
                        }
                    }
                }
            }
            """

            # Prepare variables
            variables = {"id": f"gid://shopify/Product/{product_id}"}

            # Make GraphQL request
            response = await self.client.post(
                f"https://{shop_id}.myshopify.com/admin/api/{api_version}/graphql.json",
                headers={
                    "X-Shopify-Access-Token": access_token,
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables},
            )

            if response.status_code != 200:
                logger.error(f"❌ Shopify API 请求失败: status={response.status_code}")
                return {
                    "success": False,
                    "error": f"Shopify API request failed with status {response.status_code}",
                }

            data = response.json()

            if "errors" in data:
                logger.error(f"❌ Shopify GraphQL 错误: {data['errors']}")
                return {
                    "success": False,
                    "error": f"GraphQL errors: {data['errors']}",
                }

            product_data = data.get("data", {}).get("product")
            if not product_data:
                logger.error(f"❌ 未找到商品: product_id={product_id}")
                return {
                    "success": False,
                    "error": f"Product not found: {product_id}",
                }

            logger.info(f"✅ Shopify 商品 JSON 获取成功: product_id={product_id}")

            return {
                "success": True,
                "product": product_data,
            }

        except Exception as e:
            logger.error(f"❌ 获取 Shopify 商品 JSON 失败: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get product JSON: {str(e)}",
            }

    async def get_order_json(
        self,
        shop_id: str,
        order_id: str,
        access_token: str,
        api_version: str = "2024-10",
    ) -> Dict[str, Any]:
        """Get complete JSON data for a specific Shopify order"""
        try:
            logger.info(
                f"🔍 开始获取 Shopify 订单 JSON: shop_id={shop_id}, order_id={order_id}"
            )

            # Prepare GraphQL query for complete order data
            query = """
            query($id: ID!) {
                order(id: $id) {
                    id
                    name
                    email
                    phone
                    createdAt
                    updatedAt
                    processedAt
                    totalPriceSet {
                        shopMoney {
                            amount
                            currencyCode
                        }
                    }
                    subtotalPriceSet {
                        shopMoney {
                            amount
                            currencyCode
                        }
                    }
                    totalTaxSet {
                        shopMoney {
                            amount
                            currencyCode
                        }
                    }
                    totalShippingPriceSet {
                        shopMoney {
                            amount
                            currencyCode
                        }
                    }
                    displayFulfillmentStatus
                    displayFinancialStatus
                    tags
                    note
                    customer {
                        id
                        firstName
                        lastName
                        email
                        phone
                        defaultAddress {
                            id
                            firstName
                            lastName
                            company
                            address1
                            address2
                            city
                            province
                            country
                            zip
                            phone
                        }
                    }
                    shippingAddress {
                        id
                        firstName
                        lastName
                        company
                        address1
                        address2
                        city
                        province
                        country
                        zip
                        phone
                    }
                    billingAddress {
                        id
                        firstName
                        lastName
                        company
                        address1
                        address2
                        city
                        province
                        country
                        zip
                        phone
                    }
                    lineItems(first: 50) {
                        edges {
                            node {
                                id
                                title
                                quantity
                                originalUnitPriceSet {
                                    shopMoney {
                                        amount
                                        currencyCode
                                    }
                                }
                                variant {
                                    id
                                    title
                                    sku
                                    barcode
                                    image {
                                        url
                                        altText
                                    }
                                }
                                product {
                                    id
                                    title
                                    handle
                                    vendor
                                    productType
                                }
                            }
                        }
                    }
                    fulfillments {
                        id
                        status
                        createdAt
                        updatedAt
                    }
                    refunds {
                        id
                        createdAt
                        note
                        totalRefundedSet {
                            shopMoney {
                                amount
                                currencyCode
                            }
                        }
                    }
                }
            }
            """

            variables = {"id": f"gid://shopify/Order/{order_id}"}

            response = await self.client.post(
                f"https://{shop_id}.myshopify.com/admin/api/{api_version}/graphql.json",
                headers={
                    "X-Shopify-Access-Token": access_token,
                    "Content-Type": "application/json",
                },
                json={"query": query, "variables": variables},
            )

            if response.status_code != 200:
                logger.error(f"❌ Shopify API 请求失败: status={response.status_code}")
                return {
                    "success": False,
                    "error": f"Shopify API request failed with status {response.status_code}",
                }

            data = response.json()

            if "errors" in data:
                logger.error(f"❌ Shopify GraphQL 错误: {data['errors']}")
                return {
                    "success": False,
                    "error": f"GraphQL errors: {data['errors']}",
                }

            order_data = data.get("data", {}).get("order")
            if not order_data:
                logger.error(f"❌ 未找到订单: order_id={order_id}")
                return {
                    "success": False,
                    "error": f"Order not found: {order_id}",
                }

            logger.info(f"✅ Shopify 订单 JSON 获取成功: order_id={order_id}")

            return {
                "success": True,
                "order": order_data,
            }

        except Exception as e:
            logger.error(f"❌ 获取 Shopify 订单 JSON 失败: {str(e)}")
            return {
                "success": False,
                "error": f"Failed to get order JSON: {str(e)}",
            }

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

"""
Printify API service for product and order management
"""

import logging
from typing import List, Dict, Any, Optional
import httpx
from .printify_error_handler import execute_printify_operation

logger = logging.getLogger(__name__)


class PrintifyService:
    """Service for interacting with Printify API"""

    def __init__(self, printify_api_token: str):
        self.base_url = "https://api.printify.com/v1"
        self.headers = {
            "Authorization": f"Bearer {printify_api_token}",
            "Content-Type": "application/json",
        }

    async def test_connection(self) -> Dict[str, Any]:
        """Test Printify API connection by fetching shops"""
        async def _test_connection_operation():
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/shops.json", headers=self.headers, timeout=10.0
                )
                response.raise_for_status()
                shops_data = response.json()

                return {
                    "success": True,
                    "message": "Printify API connection successful",
                    "shops_count": (
                        len(shops_data) if isinstance(shops_data, list) else 0
                    ),
                    "shops": (
                        shops_data[:5] if isinstance(shops_data, list) else []
                    ),  # Return first 5 shops
                    "api_version": "v1",
                    "base_url": self.base_url,
                }
        
        try:
            return await execute_printify_operation(
                _test_connection_operation,
                "Printify连接测试"
            )
        except Exception as e:
            logger.error(f"❌ Printify连接测试失败: {str(e)}")
            return {
                "success": False,
                "message": f"Printify连接测试失败: {str(e)}",
                "error_code": "CONNECTION_ERROR",
            }

    async def get_shops(self) -> List[Dict[str, Any]]:
        """Get all Printify shops"""
        async def _get_shops_operation():
            logger.info("🔍 开始调用 Printify API 获取店铺列表")
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/shops.json", headers=self.headers
                )
                response.raise_for_status()
                shops_data = response.json()
                logger.info(
                    f"✅ Printify API 店铺列表获取成功: {len(shops_data) if shops_data else 0} 个店铺"
                )
                return shops_data
        
        try:
            return await execute_printify_operation(
                _get_shops_operation,
                "获取Printify店铺列表"
            )
        except Exception as e:
            logger.error(f"❌ 获取Printify店铺列表失败: {str(e)}")
            return []

    async def get_products(self, shop_id: str, limit: int = 0) -> List[Dict[str, Any]]:
        """
        Get products from a Printify shop with pagination support.
        
        Args:
            shop_id: The Printify shop ID
            limit: Maximum number of products to fetch. 0 = all products (default)
        
        Returns:
            List of product dictionaries
        """
        try:
            all_products = []
            page = 1
            page_size = 50  # Printify API max per page
            
            async with httpx.AsyncClient() as client:
                while True:
                    response = await client.get(
                        f"{self.base_url}/shops/{shop_id}/products.json",
                        headers=self.headers,
                        params={"page": page, "limit": page_size},
                        timeout=30.0,
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    products = data.get("data", [])
                    
                    if not products:
                        break
                    
                    all_products.extend(products)
                    logger.info(f"✅ 获取 Printify 商品页 {page}: {len(products)} 个商品")
                    
                    # Check if we've reached the requested limit
                    if limit > 0 and len(all_products) >= limit:
                        all_products = all_products[:limit]
                        break
                    
                    # Check if there are more pages
                    # Printify returns fewer items than page_size when on last page
                    if len(products) < page_size:
                        break
                    
                    page += 1
            
            logger.info(f"✅ 总共获取 {len(all_products)} 个 Printify 商品")
            return all_products
        except Exception as e:
            logger.error(f"Failed to get Printify products: {e}")
            return []

    async def create_order(
        self, shop_id: str, order_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create an order in Printify"""
        async def _create_order_operation():
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/shops/{shop_id}/orders.json",
                    headers=self.headers,
                    json=order_data,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
        
        try:
            result = await execute_printify_operation(
                _create_order_operation,
                "创建Printify订单"
            )
            
            if result.get("success"):
                # 提取订单ID
                order_data = result.get("data", {})
                order_id = order_data.get("id")
                
                return {
                    "success": True,
                    "order_id": order_id,
                    "data": order_data,
                    "message": "Printify订单创建成功"
                }
            else:
                return {
                    "success": False,
                    "message": result.get("message", "创建Printify订单失败"),
                    "error_code": result.get("error_code"),
                    "error_details": result.get("error_details")
                }
        except Exception as e:
            logger.error(f"❌ 创建Printify订单失败: {str(e)}")
            return {
                "success": False,
                "message": f"创建Printify订单失败: {str(e)}",
                "error_code": "CREATE_ORDER_ERROR"
            }

    async def get_orders(
        self, shop_id: str, limit: int = 50, page: int = 1
    ) -> Dict[str, Any]:
        """Get orders list from Printify"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/shops/{shop_id}/orders.json",
                    headers=self.headers,
                    params={"limit": limit, "page": page},
                )
                response.raise_for_status()
                orders_data = response.json()

                return {
                    "success": True,
                    "orders": orders_data.get("data", []),
                    "total_count": orders_data.get("total", 0),
                    "current_page": page,
                    "per_page": limit,
                    "has_more": len(orders_data.get("data", [])) == limit,
                }
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Printify API HTTP error getting orders: {e.response.status_code} - {e.response.text}"
            )
            return {
                "success": False,
                "message": f"Printify API error: {e.response.status_code}",
                "error_code": e.response.status_code,
                "error_details": e.response.text,
            }
        except Exception as e:
            logger.error(f"Failed to get Printify orders: {e}")
            return {"success": False, "message": f"Failed to get orders: {str(e)}"}

    async def get_orders_batch(
        self, shop_id: str, access_token: str, order_ids: List[str], limit: int = 100
    ) -> Dict[str, Any]:
        """
        批量获取Printify订单状态

        Args:
            shop_id: Printify店铺ID
            access_token: 访问令牌
            order_ids: 订单ID列表
            limit: 每页限制

        Returns:
            批量订单数据
        """
        try:
            logger.info(
                f"📦 开始批量获取Printify订单状态: shop_id={shop_id}, order_count={len(order_ids)}"
            )

            # 设置认证头
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            all_orders = []
            page = 1
            max_pages = 10  # 防止无限循环

            async with httpx.AsyncClient() as client:
                while page <= max_pages:
                    try:
                        # 获取订单列表
                        response = await client.get(
                            f"{self.base_url}/shops/{shop_id}/orders.json",
                            headers=headers,
                            params={"limit": limit, "page": page},
                        )
                        response.raise_for_status()

                        orders_data = response.json()
                        orders = orders_data.get("data", [])

                        if not orders:
                            break

                        # 过滤出我们需要的订单
                        target_orders = []
                        for order in orders:
                            order_id = str(order.get("id", ""))
                            if order_id in order_ids:
                                target_orders.append(order)

                        all_orders.extend(target_orders)

                        # 如果已经找到所有需要的订单，可以提前退出
                        if len(all_orders) >= len(order_ids):
                            break

                        page += 1

                    except httpx.HTTPStatusError as e:
                        logger.error(
                            f"❌ 批量获取Printify订单失败: {e.response.status_code} - {e.response.text}"
                        )
                        return {
                            "success": False,
                            "message": f"Printify API error: {e.response.status_code}",
                            "orders": [],
                        }
                    except Exception as e:
                        logger.error(f"❌ 批量获取Printify订单异常: {e}")
                        return {
                            "success": False,
                            "message": f"Failed to get orders: {str(e)}",
                            "orders": [],
                        }

            logger.info(f"✅ 批量获取Printify订单成功: 找到 {len(all_orders)} 个订单")

            return {
                "success": True,
                "orders": all_orders,
                "total_found": len(all_orders),
                "requested_count": len(order_ids),
            }

        except Exception as e:
            logger.error(f"❌ 批量获取Printify订单失败: {e}")
            return {
                "success": False,
                "message": f"Failed to get orders: {str(e)}",
                "orders": [],
            }

    async def get_order(self, shop_id: str, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order details from Printify"""
        try:
            # 尝试不同的订单 ID 格式
            # 1. 原始格式：21704929.46
            # 2. 点号后部分：46
            # 3. 点号前部分：21704929

            order_id_formats = [
                order_id,  # 原始格式
                order_id.split(".")[-1] if "." in order_id else order_id,  # 点号后部分
                order_id.split(".")[0] if "." in order_id else order_id,  # 点号前部分
            ]

            logger.info(
                f"🔍 开始调用 Printify API 获取订单详情: shop_id={shop_id}, original_order_id={order_id}, trying_formats={order_id_formats}"
            )

            async with httpx.AsyncClient() as client:
                for i, test_order_id in enumerate(order_id_formats):
                    try:
                        logger.info(f"🔍 尝试格式 {i+1}: {test_order_id}")
                        response = await client.get(
                            f"{self.base_url}/shops/{shop_id}/orders/{test_order_id}.json",
                            headers=self.headers,
                        )
                        response.raise_for_status()
                        logger.info(
                            f"✅ Printify 订单详情获取成功: order_id={test_order_id}"
                        )
                        return response.json()
                    except httpx.HTTPStatusError as e:
                        logger.info(
                            f"❌ 格式 {i+1} 失败: {e.response.status_code} - {e.response.text}"
                        )
                        continue
                    except Exception as e:
                        logger.info(f"❌ 格式 {i+1} 异常: {e}")
                        continue

                # 所有格式都失败了
                logger.error(f"❌ 所有订单 ID 格式都失败了: {order_id_formats}")
                return None

        except Exception as e:
            logger.error(f"❌ Printify 获取订单失败: {e}")
            return None

    async def create_shipping_label_from_shopify_order(
        self,
        shop_id: str,
        shopify_order: Dict[str, Any],
        printify_product_mapping: Dict[str, str] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Create a Printify order from a Shopify order

        Args:
            shop_id: Printify shop ID
            shopify_order: Shopify order data
            printify_product_mapping: Mapping from Shopify product IDs to Printify product/variant IDs
        """
        try:
            # Extract customer information
            customer = shopify_order.get("customer", {})
            shipping_address = shopify_order.get("shipping_address", {})

            # Build customer name
            first_name = customer.get(
                "first_name", shipping_address.get("first_name", "")
            )
            last_name = customer.get("last_name", shipping_address.get("last_name", ""))
            customer_name = f"{first_name} {last_name}".strip()

            # Build order data for Printify
            order_data = {
                "external_id": f"SHOPIFY_{shopify_order.get('id', '')}_{shopify_order.get('order_number', '')}",
                "line_items": [],
                "shipping_method": 1,  # Default shipping method
                "send_shipping_notification": True,
                "status": "onhold",  # Default status
                "address_to": {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": customer.get("email", ""),
                    "phone": shipping_address.get("phone") or customer.get("phone") or "+10000000000",  # Printify API 要求 phone 字段必须有值
                    "country": shipping_address.get("country_code", "").upper(),
                    "region": shipping_address.get("province", ""),
                    "city": shipping_address.get("city", ""),
                    "address1": shipping_address.get("address1", ""),
                    "address2": shipping_address.get("address2", ""),
                    "zip": shipping_address.get("zip", ""),
                },
            }

            # Process line items
            line_items = shopify_order.get("line_items", [])
            for item in line_items:
                # For now, we'll use a default product mapping
                # In a real implementation, you'd need to map Shopify products to Printify products
                if printify_product_mapping:
                    product_id = printify_product_mapping.get(
                        str(item.get("product_id", ""))
                    )
                    if product_id:
                        order_data["line_items"].append(
                            {
                                "product_id": product_id,
                                "variant_id": 1,  # Default variant
                                "quantity": item.get("quantity", 1),
                            }
                        )
                else:
                    # Use default product for testing
                    order_data["line_items"].append(
                        {
                            "product_id": "67f4a8963b41671184062a1e",  # Default product from PS script
                            "variant_id": 38191,  # Default variant from PS script
                            "quantity": item.get("quantity", 1),
                        }
                    )

            # If no line items were added, add a default one
            if not order_data["line_items"]:
                order_data["line_items"].append(
                    {
                        "product_id": "67f4a8963b41671184062a1e",
                        "variant_id": 38191,
                        "quantity": 1,
                    }
                )

            logger.info(
                f"Creating Printify order for Shopify order {shopify_order.get('id')}"
            )
            logger.info(f"Order data: {order_data}")

            # Create the order
            result = await self.create_order(shop_id, order_data)

            if result:
                logger.info(f"Successfully created Printify order: {result.get('id')}")
            else:
                logger.error(
                    f"Failed to create Printify order for Shopify order {shopify_order.get('id')}"
                )

            return result

        except Exception as e:
            logger.error(f"Failed to create shipping label from Shopify order: {e}")
            return None

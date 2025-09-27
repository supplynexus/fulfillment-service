"""
Printify API service for product and order management
"""

import logging
from typing import List, Dict, Any, Optional
import httpx

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
        try:
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
        except httpx.HTTPStatusError as e:
            logger.error(
                f"Printify API HTTP error: {e.response.status_code} - {e.response.text}"
            )
            return {
                "success": False,
                "message": f"Printify API error: {e.response.status_code}",
                "error_code": e.response.status_code,
                "error_details": e.response.text,
            }
        except httpx.TimeoutException:
            logger.error("Printify API connection timeout")
            return {
                "success": False,
                "message": "Printify API connection timeout",
                "error_code": "TIMEOUT",
            }
        except Exception as e:
            logger.error(f"Printify API connection failed: {e}")
            return {
                "success": False,
                "message": f"Printify API connection failed: {str(e)}",
                "error_code": "CONNECTION_ERROR",
            }

    async def get_shops(self) -> List[Dict[str, Any]]:
        """Get all Printify shops"""
        try:
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
        except httpx.HTTPStatusError as e:
            logger.error(
                f"❌ Printify API HTTP 错误获取店铺: {e.response.status_code} - {e.response.text}"
            )
            return []
        except Exception as e:
            logger.error(f"❌ Printify 获取店铺失败: {e}")
            return []

    async def get_products(self, shop_id: str) -> List[Dict[str, Any]]:
        """Get products from a Printify shop"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/shops/{shop_id}/products.json",
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to get Printify products: {e}")
            return []

    async def create_order(
        self, shop_id: str, order_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Create an order in Printify"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/shops/{shop_id}/orders.json",
                    headers=self.headers,
                    json=order_data,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to create Printify order: {e}")
            return None

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

    async def get_order(self, shop_id: str, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order details from Printify"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/shops/{shop_id}/orders/{order_id}.json",
                    headers=self.headers,
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get Printify order: {e}")
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
                    "phone": shipping_address.get("phone", ""),
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

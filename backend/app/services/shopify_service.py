"""
Shopify integration service
"""

import httpx
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.external_system import ExternalSystem, ExternalSystemType
from app.models.order import Order, OrderStatus
from app.models.customer import Customer
from app.models.product import Product
from app.core.logging import get_logger

logger = get_logger(__name__)


class ShopifyService:
    """Shopify integration service"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def get_shopify_system(self, tenant_id: int) -> Optional[ExternalSystem]:
        """Get Shopify external system for tenant"""
        try:
            result = await self.db.execute(
                select(ExternalSystem).where(
                    ExternalSystem.tenant_id == tenant_id,
                    ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                    ExternalSystem.is_active == True
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting Shopify system for tenant {tenant_id}: {e}")
            return None
    
    async def fetch_orders(self, tenant_id: int, limit: int = 10) -> List[Dict[str, Any]]:
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
                            email
                            phone
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
                "X-Shopify-Access-Token": shopify_system.credentials.get("access_token")
            }
            
            # Make API request
            url = f"{shopify_system.base_url}/admin/api/{shopify_system.settings.get('api_version', 'unstable')}/graphql.json"
            
            response = await self.client.post(
                url,
                headers=headers,
                json={
                    "query": query,
                    "variables": {"first": limit}
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Shopify API error: {response.status_code} - {response.text}")
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
    
    async def parse_order(self, order_data: Dict[str, Any], tenant_id: int) -> Optional[Order]:
        """Parse Shopify order data into our Order model"""
        try:
            # Extract basic order information
            shopify_order_id = order_data.get("id", "").split("/")[-1]  # Remove "gid://shopify/Order/" prefix
            order_name = order_data.get("name", "")
            email = order_data.get("email", "")
            phone = order_data.get("phone", "")
            
            # Parse dates
            created_at = order_data.get("createdAt")
            updated_at = order_data.get("updatedAt")
            cancelled_at = order_data.get("cancelledAt")
            
            # Parse pricing
            total_price = order_data.get("currentTotalPriceSet", {}).get("shopMoney", {}).get("amount", "0")
            subtotal_price = order_data.get("currentSubtotalPriceSet", {}).get("shopMoney", {}).get("amount", "0")
            total_tax = order_data.get("currentTotalTaxSet", {}).get("shopMoney", {}).get("amount", "0")
            currency = order_data.get("currencyCode", "USD")
            
            # Determine order status
            if cancelled_at:
                status = OrderStatus.CANCELLED
            else:
                status = OrderStatus.PENDING
            
            # Parse line items
            line_items = []
            for edge in order_data.get("lineItems", {}).get("edges", []):
                item = edge["node"]
                line_items.append({
                    "shopify_line_item_id": item.get("id", "").split("/")[-1],
                    "name": item.get("name", ""),
                    "quantity": item.get("quantity", 0),
                    "sku": item.get("sku", ""),
                    "variant_id": item.get("variant", {}).get("id", "").split("/")[-1],
                    "variant_title": item.get("variant", {}).get("title", ""),
                    "variant_sku": item.get("variant", {}).get("sku", ""),
                    "price": item.get("variant", {}).get("price", "0"),
                    "product_id": item.get("variant", {}).get("product", {}).get("id", "").split("/")[-1],
                    "product_title": item.get("variant", {}).get("product", {}).get("title", ""),
                    "product_handle": item.get("variant", {}).get("product", {}).get("handle", "")
                })
            
            # Parse addresses
            shipping_address = order_data.get("shippingAddress", {})
            billing_address = order_data.get("billingAddress", {})
            
            # Create order object (not saved to database yet)
            order = Order(
                tenant_id=tenant_id,
                external_system_id=1,  # Shopify system ID
                external_order_id=shopify_order_id,
                order_number=order_name,
                customer_email=email,
                customer_phone=phone,
                status=status,
                total_amount=float(total_price),
                subtotal_amount=float(subtotal_price),
                tax_amount=float(total_tax),
                currency=currency,
                external_data={
                    "shopify_order_id": shopify_order_id,
                    "line_items": line_items,
                    "shipping_address": shipping_address,
                    "billing_address": billing_address,
                    "cancel_reason": order_data.get("cancelReason"),
                    "raw_data": order_data
                }
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Error parsing Shopify order: {e}")
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
                    "orders_processed": 0
                }
            
            # Parse and process each order
            processed_count = 0
            errors = []
            
            for order_data in shopify_orders:
                try:
                    # Parse order
                    order = await self.parse_order(order_data, tenant_id)
                    if not order:
                        errors.append(f"Failed to parse order {order_data.get('name', 'unknown')}")
                        continue
                    
                    # Check if order already exists
                    existing_order = await self.db.execute(
                        select(Order).where(
                            Order.tenant_id == tenant_id,
                            Order.external_order_id == order.external_order_id
                        )
                    )
                    existing_order = existing_order.scalar_one_or_none()
                    
                    if existing_order:
                        logger.info(f"Order {order.order_number} already exists, skipping")
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
                "errors": errors
            }
            
        except Exception as e:
            logger.error(f"Error in Shopify order sync: {e}")
            return {
                "success": False,
                "message": f"Sync failed: {e}",
                "orders_processed": 0
            }
    
    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()

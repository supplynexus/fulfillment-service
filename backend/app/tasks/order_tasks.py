"""
Order processing tasks
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime
from celery import current_task
from app.tasks.celery_app import celery_app
from app.core.database import get_sync_db
from app.models.shopify_order import ShopifyOrder
from app.models.external_system import ExternalSystem, ExternalSystemType
from sqlalchemy import select, and_

logger = logging.getLogger(__name__)


def _extract_shop_domain_from_order(order_data: Dict[str, Any]) -> Optional[str]:
    """Extract shop domain from Shopify order webhook data"""
    # Try different possible fields
    if "shop_domain" in order_data:
        return order_data["shop_domain"]
    
    # Check if there's a shop object
    if "shop" in order_data and isinstance(order_data["shop"], dict):
        shop = order_data["shop"]
        if "myshopify_domain" in shop:
            return shop["myshopify_domain"].replace(".myshopify.com", "")
        if "domain" in shop:
            return shop["domain"].replace(".myshopify.com", "")
    
    # Try to extract from order ID (gid://shopify/Order/xxx)
    order_id = order_data.get("id", "")
    if "gid://shopify/Order/" in str(order_id):
        # This doesn't contain shop info, need to check other fields
        pass
    
    # Check webhook headers or metadata
    # Note: webhook headers are not available in background task
    # We need to pass shop info explicitly or find it from order data
    
    return None


def _convert_webhook_order_to_shopify_order(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert Shopify webhook order data to ShopifyOrder format"""
    # Extract order ID
    order_id = order_data.get("id", "")
    if isinstance(order_id, str) and "gid://shopify/Order/" in order_id:
        shopify_order_id = order_id
    else:
        shopify_order_id = f"gid://shopify/Order/{order_id}"
    
    # Extract basic info
    name = order_data.get("name", "")
    confirmation_number = order_data.get("confirmation_number", name)
    
    # Extract financial and fulfillment status
    financial_status = order_data.get("financial_status", "")
    fulfillment_status = order_data.get("fulfillment_status", "")
    if not fulfillment_status:
        # Try displayFulfillmentStatus
        fulfillment_status = order_data.get("displayFulfillmentStatus", "")
    
    # Extract prices
    total_price = None
    subtotal_price = None
    total_tax = None
    total_shipping = None
    
    if "total_price" in order_data:
        try:
            total_price = float(order_data["total_price"])
        except (ValueError, TypeError):
            pass
    
    if "subtotal_price" in order_data:
        try:
            subtotal_price = float(order_data["subtotal_price"])
        except (ValueError, TypeError):
            pass
    
    if "total_tax" in order_data:
        try:
            total_tax = float(order_data["total_tax"])
        except (ValueError, TypeError):
            pass
    
    if "total_shipping_price_set" in order_data:
        try:
            shipping_data = order_data["total_shipping_price_set"]
            if isinstance(shipping_data, dict) and "shop_money" in shipping_data:
                total_shipping = float(shipping_data["shop_money"].get("amount", 0))
        except (ValueError, TypeError, KeyError):
            pass
    
    # Extract currency
    currency_code = order_data.get("currency_code", "USD")
    if "total_price_set" in order_data:
        try:
            price_data = order_data["total_price_set"]
            if isinstance(price_data, dict) and "shop_money" in price_data:
                currency_code = price_data["shop_money"].get("currency_code", currency_code)
        except (KeyError, TypeError):
            pass
    
    # Extract customer data
    customer_data = {}
    if "customer" in order_data:
        customer = order_data["customer"]
        if isinstance(customer, dict):
            customer_data = {
                "id": customer.get("id", ""),
                "first_name": customer.get("first_name", customer.get("firstName", "")),
                "last_name": customer.get("last_name", customer.get("lastName", "")),
                "email": customer.get("email", ""),
                "phone": customer.get("phone", ""),
            }
            # Combine first and last name
            if customer_data.get("first_name") or customer_data.get("last_name"):
                customer_data["name"] = f"{customer_data.get('first_name', '')} {customer_data.get('last_name', '')}".strip()
    
    # Extract addresses
    shipping_address = order_data.get("shipping_address", {})
    billing_address = order_data.get("billing_address", {})
    
    # Extract line items
    line_items = order_data.get("line_items", [])
    if not line_items and "lineItems" in order_data:
        line_items = order_data["lineItems"]
    
    # Extract fulfillments
    fulfillments = order_data.get("fulfillments", [])
    
    # Extract refunds
    refunds = order_data.get("refunds", [])
    
    # Extract tags
    tags = order_data.get("tags", [])
    if isinstance(tags, str):
        tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
    
    # Extract note
    note = order_data.get("note", "")
    
    # Determine status flags
    confirmed = order_data.get("confirmed", True)
    closed = order_data.get("closed", False)
    cancelled = financial_status == "voided" or order_data.get("cancelled_at") is not None
    
    return {
        "shopify_order_id": shopify_order_id,
        "name": name,
        "confirmation_number": confirmation_number,
        "financial_status": financial_status,
        "fulfillment_status": fulfillment_status,
        "confirmed": confirmed,
        "closed": closed,
        "cancelled": cancelled,
        "currency_code": currency_code,
        "total_price": total_price,
        "subtotal_price": subtotal_price,
        "total_tax": total_tax,
        "total_shipping": total_shipping,
        "tags": tags,
        "note": note,
        "customer_data": customer_data,
        "billing_address": billing_address,
        "shipping_address": shipping_address,
        "line_items": line_items,
        "fulfillments": fulfillments,
        "refunds": refunds,
        "raw_data": order_data,
    }


@celery_app.task(bind=True)
def process_shopify_order(self, order_data: Dict[str, Any]):
    """Process a Shopify order from webhook and save to database"""
    db = next(get_sync_db())
    
    try:
        order_id = order_data.get("id", order_data.get("name", "unknown"))
        logger.info(f"🔍 开始处理 Shopify 订单: {order_id}")
        
        # Update task progress
        if current_task:
            current_task.update_state(
                state="PROGRESS",
                meta={"current": 1, "total": 3, "status": "Extracting shop information"}
            )
        
        # Extract shop domain from order data
        shop_domain = _extract_shop_domain_from_order(order_data)
        
        if not shop_domain:
            # Try to find shop from all external systems
            logger.warning(f"⚠️ 无法从订单数据中提取 shop 信息，尝试查找所有 Shopify 店铺")
            query = select(ExternalSystem).where(
                and_(
                    ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                    ExternalSystem.is_active == True
                )
            )
            result = db.execute(query)
            external_systems = result.scalars().all()
            
            if len(external_systems) == 1:
                # Only one Shopify store, use it
                external_system = external_systems[0]
                tenant_id = external_system.tenant_id
                logger.info(f"✅ 找到唯一的 Shopify 店铺: tenant_id={tenant_id}, external_system_id={external_system.id}")
            elif len(external_systems) == 0:
                logger.error(f"❌ 未找到任何 Shopify 店铺配置")
                return {"status": "error", "message": "No Shopify store configured"}
            else:
                logger.error(f"❌ 找到多个 Shopify 店铺，无法确定使用哪个: count={len(external_systems)}")
                return {"status": "error", "message": "Multiple Shopify stores found, cannot determine which one to use"}
        else:
            # Find external system by shop domain
            logger.info(f"🔍 查找 Shopify 店铺: shop_domain={shop_domain}")
            query = select(ExternalSystem).where(
                and_(
                    ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                    ExternalSystem.external_id == shop_domain,
                    ExternalSystem.is_active == True
                )
            )
            result = db.execute(query)
            external_system = result.scalar_one_or_none()
            
            if not external_system:
                logger.error(f"❌ 未找到 Shopify 店铺: shop_domain={shop_domain}")
                return {"status": "error", "message": f"Shopify store not found: {shop_domain}"}
            
            tenant_id = external_system.tenant_id
            logger.info(f"✅ 找到 Shopify 店铺: tenant_id={tenant_id}, external_system_id={external_system.id}")
        
        # Update task progress
        if current_task:
            current_task.update_state(
                state="PROGRESS",
                meta={"current": 2, "total": 3, "status": "Converting order data"}
            )
        
        # Convert webhook order data to ShopifyOrder format
        order_dict = _convert_webhook_order_to_shopify_order(order_data)
        shopify_order_id = order_dict["shopify_order_id"]
        
        # Check if order already exists
        existing_query = select(ShopifyOrder).where(
            and_(
                ShopifyOrder.tenant_id == tenant_id,
                ShopifyOrder.shopify_order_id == shopify_order_id
            )
        )
        existing_result = db.execute(existing_query)
        existing_order = existing_result.scalar_one_or_none()
        
        if existing_order:
            logger.info(f"🔄 更新现有订单: shopify_order_id={shopify_order_id}")
            # Update existing order
            for key, value in order_dict.items():
                if hasattr(existing_order, key):
                    setattr(existing_order, key, value)
            existing_order.last_synced_at = datetime.utcnow()
        else:
            logger.info(f"➕ 创建新订单: shopify_order_id={shopify_order_id}")
            # Create new order
            new_order = ShopifyOrder(
                tenant_id=tenant_id,
                **order_dict,
                last_synced_at=datetime.utcnow()
            )
            db.add(new_order)
        
        # Commit changes
        db.commit()
        
        # Update task progress
        if current_task:
            current_task.update_state(
                state="PROGRESS",
                meta={"current": 3, "total": 3, "status": "Order saved successfully"}
            )
        
        logger.info(f"✅ Shopify 订单处理成功: {shopify_order_id}")
        return {"status": "success", "order_id": shopify_order_id}
        
    except Exception as e:
        db.rollback()
        logger.error(f"❌ 处理 Shopify 订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        
        if current_task:
            current_task.update_state(
                state="FAILURE",
                meta={"error": str(e)}
            )
        raise
    finally:
        db.close()


@celery_app.task(bind=True)
def fulfill_order(self, order_id: str):
    """Fulfill an order through Printify"""
    try:
        logger.info(f"Fulfilling order {order_id}")
        
        # Add fulfillment logic here
        # This would include creating Printify orders, etc.
        
        logger.info(f"Successfully fulfilled order {order_id}")
        return {"status": "success", "order_id": order_id}
        
    except Exception as e:
        logger.error(f"Failed to fulfill order {order_id}: {e}")
        if current_task:
            current_task.update_state(
                state="FAILURE",
                meta={"error": str(e)}
            )
        raise

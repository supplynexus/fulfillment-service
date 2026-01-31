"""
Shopify订单同步服务
用于将Shopify订单同步到核心订单表
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.core.logging import get_logger
from app.models.shopify_order import ShopifyOrder
from app.models.order import Order, OrderItem
from app.models.product import ProductVariant
from app.models.tenant import Tenant
from app.services.address_validation_service import validate_address
from app.services.order_number_service import OrderNumberService

logger = get_logger(__name__)


def _get_customer_name(shopify_order: ShopifyOrder) -> str:
    """从 ShopifyOrder 中提取客户姓名"""
    logger.info(f"🔍 提取客户姓名: customer_data={shopify_order.customer_data}, shipping_address={shopify_order.shipping_address}")
    
    if not shopify_order.customer_data:
        logger.warning("⚠️ customer_data 为空，尝试从 shipping_address 获取")
        # 如果 customer_data 为空，尝试从 shipping_address 获取
        if shopify_order.shipping_address:
            first_name = shopify_order.shipping_address.get("firstName", "")
            last_name = shopify_order.shipping_address.get("lastName", "")
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                logger.info(f"✅ 从 shipping_address 获取到客户姓名: {full_name}")
                return full_name
        return ""
    
    # 尝试从 customer_data 中获取 name 字段
    if "name" in shopify_order.customer_data and shopify_order.customer_data.get("name"):
        name = shopify_order.customer_data.get("name", "")
        logger.info(f"✅ 从 customer_data.name 获取到客户姓名: {name}")
        return name
    
    # 如果没有 name 字段，组合 firstName 和 lastName
    first_name = shopify_order.customer_data.get("firstName", "")
    last_name = shopify_order.customer_data.get("lastName", "")
    full_name = f"{first_name} {last_name}".strip()
    
    if full_name:
        logger.info(f"✅ 从 customer_data (firstName + lastName) 获取到客户姓名: {full_name}")
        return full_name
    
    # 如果还是没有，尝试从 shipping_address 获取
    if shopify_order.shipping_address:
        first_name = shopify_order.shipping_address.get("firstName", "")
        last_name = shopify_order.shipping_address.get("lastName", "")
        full_name = f"{first_name} {last_name}".strip()
        if full_name:
            logger.info(f"✅ 从 shipping_address 获取到客户姓名: {full_name}")
            return full_name
    
    logger.warning("⚠️ 无法提取客户姓名")
    return ""


def _get_customer_phone(shopify_order: ShopifyOrder) -> Optional[str]:
    """从 ShopifyOrder 中提取客户电话"""
    # 优先从 customer_data 获取
    if shopify_order.customer_data and shopify_order.customer_data.get("phone"):
        return shopify_order.customer_data.get("phone")
    
    # 其次从 shipping_address 获取
    if shopify_order.shipping_address and shopify_order.shipping_address.get("phone"):
        return shopify_order.shipping_address.get("phone")
    
    # 最后从 billing_address 获取
    if shopify_order.billing_address and shopify_order.billing_address.get("phone"):
        return shopify_order.billing_address.get("phone")
    
    return None


def sync_shopify_order_to_core_sync(
    db: Session,
    shopify_order: ShopifyOrder,
    tenant: Tenant
) -> Dict[str, Any]:
    """
    同步单个Shopify订单到核心订单表（同步版本，用于Celery任务）
    
    Args:
        db: 同步数据库会话
        shopify_order: Shopify订单对象
        tenant: 租户对象
        
    Returns:
        同步结果字典
    """
    try:
        logger.info(
            f"🔍 开始同步 Shopify 订单到核心系统: shopify_order_id={shopify_order.id}, "
            f"shopify_order_name={shopify_order.name}, tenant_id={tenant.id}"
        )
        
        # 检查是否已经同步过
        existing_core_order = db.query(Order).filter(
            and_(
                Order.tenant_id == tenant.id,
                Order.external_order_id == shopify_order.shopify_order_id
            )
        ).first()
        
        # 转换 Shopify 地址格式到核心订单格式
        def convert_shopify_address(shopify_addr):
            if not shopify_addr:
                return {}

            # 合并 firstName 和 lastName
            first_name = shopify_addr.get("firstName", "")
            last_name = shopify_addr.get("lastName", "")
            full_name = f"{first_name} {last_name}".strip()

            return {
                "name": full_name,
                "address1": shopify_addr.get("address1", ""),
                "address2": shopify_addr.get("address2", ""),
                "city": shopify_addr.get("city", ""),
                "province": shopify_addr.get("province", ""),
                "country": shopify_addr.get("country", ""),
                "zip": shopify_addr.get("zip", ""),
                "phone": shopify_addr.get("phone", ""),
            }

        shipping_address_core = convert_shopify_address(shopify_order.shipping_address)
        billing_address_core = convert_shopify_address(shopify_order.billing_address)

        # 地址验证（仅针对收货地址），失败不阻断同步
        address_validation_status = None
        address_validation_reason_code = None
        address_validation_message = None
        address_last_validated_at = None

        try:
            if shipping_address_core:
                validation_result = validate_address(shipping_address_core)
                address_validation_status = validation_result.status
                address_validation_reason_code = validation_result.reason_code
                address_validation_message = validation_result.message
                address_last_validated_at = validation_result.validated_at
                logger.info(
                    "✅ 核心订单地址验证完成",
                    status=address_validation_status,
                    reason_code=address_validation_reason_code,
                )
            else:
                address_validation_status = "suspicious"
                address_validation_reason_code = "MISSING_SHIPPING_ADDRESS"
                address_validation_message = "缺少收货地址信息，无法完成地址验证"
                address_last_validated_at = datetime.now(timezone.utc)
                logger.warning("⚠️ 核心订单缺少收货地址，标记为需人工确认")
        except Exception as e:
            logger.error("❌ 核心订单地址验证失败", error=str(e))
            address_validation_status = "failed"
            address_validation_reason_code = "VALIDATION_EXCEPTION"
            address_validation_message = str(e)
            address_last_validated_at = datetime.now(timezone.utc)

        if existing_core_order:
            logger.info(f"ℹ️ 核心订单已存在，更新现有订单: {existing_core_order.id}")
            core_order = existing_core_order
            # 同步最新的地址和验证结果
            core_order.shipping_address = shipping_address_core
            core_order.billing_address = billing_address_core
            core_order.address_validation_status = address_validation_status
            core_order.address_validation_reason_code = address_validation_reason_code
            core_order.address_validation_message = address_validation_message
            core_order.address_last_validated_at = address_last_validated_at
            # 更新客户信息
            customer_name = _get_customer_name(shopify_order)
            customer_phone = _get_customer_phone(shopify_order)
            if customer_name:
                core_order.customer_name = customer_name
            if customer_phone:
                core_order.customer_phone = customer_phone
            # 更新客户邮箱（如果为空或需要更新）
            if shopify_order.customer_data and shopify_order.customer_data.get("email"):
                core_order.customer_email = shopify_order.customer_data.get("email", "")
        else:
            # 创建核心订单
            logger.info(f"➕ 创建新的核心订单")

            # 生成人类可读的订单编号（同步版本）
            order_number = OrderNumberService.generate_order_number_sync(
                db, tenant.id, "ORD"
            )
            logger.info(f"📝 生成订单编号: {order_number}")

            core_order = Order(
                tenant_id=tenant.id,
                external_system_id=None,  # 暂时不关联外部系统
                external_order_id=shopify_order.shopify_order_id,
                external_order_number=shopify_order.name,
                external_order_name=shopify_order.name,
                order_number=order_number,
                status="pending",
                total_amount=float(shopify_order.total_price) if shopify_order.total_price else 0.0,
                subtotal_amount=float(shopify_order.subtotal_price) if shopify_order.subtotal_price else None,
                tax_amount=float(shopify_order.total_tax) if shopify_order.total_tax else None,
                currency=shopify_order.currency_code or "USD",
                customer_email=shopify_order.customer_data.get("email", "") if shopify_order.customer_data else "",
                customer_name=_get_customer_name(shopify_order),
                customer_phone=_get_customer_phone(shopify_order),
                shipping_address=shipping_address_core,
                billing_address=billing_address_core,
                shopify_raw_data=shopify_order.raw_data,
                external_data=shopify_order.raw_data,
                order_date=shopify_order.created_at,
                address_validation_status=address_validation_status,
                address_validation_reason_code=address_validation_reason_code,
                address_validation_message=address_validation_message,
                address_last_validated_at=address_last_validated_at,
            )
            db.add(core_order)
            db.flush()  # 获取 ID
            logger.info(f"✅ 核心订单创建成功: ID={core_order.id}")

        # 处理订单行项目
        line_items_data = shopify_order.line_items
        logger.info(f"🔍 开始处理订单行项目: shopify_order_id={shopify_order.shopify_order_id}, line_items_data type={type(line_items_data)}")
        logger.info(f"🔍 line_items_data 是否为 None: {line_items_data is None}")
        logger.info(f"🔍 line_items_data 值: {line_items_data}")
        
        if line_items_data:
            # 确保 line_items 是列表格式
            if isinstance(line_items_data, str):
                import json
                try:
                    line_items_data = json.loads(line_items_data)
                    logger.info(f"✅ 成功解析 line_items JSON 字符串")
                except Exception as e:
                    logger.error(f"❌ 解析 line_items JSON 失败: {str(e)}")
                    line_items_data = []
            
            # 处理 None 值
            if line_items_data is None:
                logger.warning("⚠️ line_items_data 为 None")
                line_items_data = []
            
            if isinstance(line_items_data, list) and len(line_items_data) > 0:
                logger.info(f"🔍 开始处理订单行项目: {len(line_items_data)} 个")
                logger.info(f"🔍 第一个 line_item 示例: {line_items_data[0] if line_items_data else None}")

                # 删除现有的订单行项目（如果存在）
                if existing_core_order:
                    existing_items = db.query(OrderItem).filter(
                        OrderItem.order_id == core_order.id
                    ).all()
                    for item in existing_items:
                        db.delete(item)
                    logger.info(f"🗑️ 删除现有订单行项目: {len(existing_items)} 个")

                items_created = 0
                for line_item in line_items_data:
                    try:
                        logger.info(f"🔍 处理 line_item: {line_item}")
                        
                        # 尝试匹配核心 SKU
                        core_variant_id = None
                        core_product_id = None

                        # 方法1: 通过 SKU 查找核心变体
                        if line_item.get("sku"):
                            core_variant = db.query(ProductVariant).filter(
                                and_(
                                    ProductVariant.tenant_id == tenant.id,
                                    ProductVariant.sku == line_item["sku"]
                                )
                            ).first()

                            if core_variant:
                                core_variant_id = core_variant.id
                                core_product_id = core_variant.product_id
                                logger.info(
                                    f"✅ 通过SKU匹配到核心变体: SKU={line_item['sku']}, variant_id={core_variant_id}"
                                )

                        # 提取价格信息（支持多种格式）
                        price_value = 0.0
                        if "price" in line_item and line_item.get("price") is not None:
                            try:
                                price_value = float(line_item.get("price", 0))
                            except (ValueError, TypeError):
                                logger.warning(f"⚠️ 无法转换价格: {line_item.get('price')}")
                                price_value = 0.0
                        elif "originalUnitPriceSet" in line_item:
                            # Shopify GraphQL 格式
                            try:
                                amount = line_item.get("originalUnitPriceSet", {}).get("shopMoney", {}).get("amount", 0)
                                price_value = float(amount) if amount else 0.0
                            except (ValueError, TypeError):
                                logger.warning(f"⚠️ 无法转换 originalUnitPriceSet 价格")
                                price_value = 0.0
                        
                        quantity = int(line_item.get("quantity", 1)) if line_item.get("quantity") else 1
                        total_price = price_value * quantity
                        
                        logger.info(f"🔍 价格提取: price_value={price_value}, quantity={quantity}, total_price={total_price}")

                        # 创建订单行项目
                        order_item = OrderItem(
                            tenant_id=tenant.id,
                            order_id=core_order.id,
                            core_product_id=core_product_id,
                            core_variant_id=core_variant_id,
                            sku=line_item.get("sku") or "",
                            title=line_item.get("title", "") or "",
                            variant_title=(line_item.get("variant_title") or line_item.get("variantTitle") or ""),
                            quantity=quantity,
                            unit_price=price_value,
                            total_price=total_price,
                            external_product_id=line_item.get("product_id") or (line_item.get("product", {}) if isinstance(line_item.get("product"), dict) else {}).get("id") or None,
                            external_variant_id=line_item.get("variant_id") or line_item.get("id") or None,
                            item_metadata=line_item,
                        )
                        db.add(order_item)
                        db.flush()  # 立即刷新，确保数据写入
                        items_created += 1
                        logger.info(
                            f"✅ 订单行项目创建成功: order_item_id={order_item.id}, SKU={line_item.get('sku')}, title={line_item.get('title')}, 数量={quantity}, 价格={price_value}"
                        )

                    except Exception as e:
                        logger.error(f"❌ 处理订单行项目失败: {str(e)}")
                        import traceback
                        logger.error(f"   异常堆栈: {traceback.format_exc()}")
                        continue
                
                logger.info(f"✅ 订单行项目处理完成: 成功创建 {items_created} 个")
            else:
                logger.warning(f"⚠️ line_items 不是列表格式或为空: type={type(line_items_data)}, value={line_items_data}")
        else:
            logger.warning(f"⚠️ Shopify订单没有 line_items: shopify_order_id={shopify_order.shopify_order_id}")

        db.commit()
        logger.info(f"✅ Shopify 订单同步到核心系统成功: {shopify_order.name}")

        return {
            "success": True,
            "message": f"订单 {shopify_order.name} 已成功同步到核心系统",
            "core_order_id": core_order.id,
            "items_count": len(shopify_order.line_items) if shopify_order.line_items else 0,
        }

    except Exception as e:
        db.rollback()
        logger.error(f"❌ 同步 Shopify 订单到核心系统失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        return {
            "success": False,
            "message": f"同步失败: {str(e)}",
            "error": str(e),
        }





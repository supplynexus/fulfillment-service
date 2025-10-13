"""
Printify订单管理API端点
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
import httpx
import json
from datetime import datetime

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger
from app.core.security import decrypt_data
from app.models.tenant import Tenant
from app.models.user import User
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.models.printify_order import PrintifyOrder
from app.services.printify_error_handler import execute_printify_operation
from sqlalchemy import select, desc
from sqlalchemy.orm import selectinload

logger = get_logger(__name__)
router = APIRouter()

# Printify API配置 - 将从数据库获取
PRINTIFY_API_BASE = "https://api.printify.com/v1"  # 默认值，会被数据库配置覆盖


async def get_printify_config(db: AsyncSession, tenant_id: int) -> Dict[str, Any]:
    """
    从数据库获取Printify配置

    Returns:
        Dict containing:
        - api_base_url: API基础URL
        - shop_id: 商店ID
        - access_token: 访问令牌
        - default_product_id: 默认商品ID
        - default_variant_id: 默认变体ID
        - default_status: 默认订单状态
    """
    try:
        # 查询Printify外部系统配置
        from sqlalchemy import select

        stmt = select(ExternalSystem).where(
            ExternalSystem.tenant_id == tenant_id,
            ExternalSystem.system_type == ExternalSystemType.PRINTIFY,
            ExternalSystem.is_active == True,
        )
        result = await db.execute(stmt)
        printify_system = result.scalar_one_or_none()

        if not printify_system:
            logger.warning(f"未找到租户 {tenant_id} 的Printify配置")
            # 返回默认配置用于测试
            return {
                "api_base_url": PRINTIFY_API_BASE,
                "shop_id": "21704929",  # 硬编码的测试商店ID
                "access_token": None,  # 需要配置
                # 暂时使用硬编码的测试商品参数
                "default_product_id": "67f4a8963b41671184062a1e",
                "default_variant_id": 38191,
                "default_status": "onhold",
            }

        # 解密凭据
        credentials = printify_system.credentials or {}
        settings = printify_system.settings or {}

        # 解密访问令牌和商店ID
        access_token = None
        shop_id = None

        if credentials.get("access_token"):
            try:
                access_token = decrypt_data(credentials["access_token"])
                logger.info("✅ Printify访问令牌解密成功")
            except Exception as e:
                logger.error(f"❌ 解密Printify访问令牌失败: {e}")

        if credentials.get("shop_id"):
            try:
                shop_id = decrypt_data(credentials["shop_id"])
                logger.info(f"✅ Printify商店ID解密成功: {shop_id}")
            except Exception as e:
                logger.error(f"❌ 解密Printify商店ID失败: {e}")

        # 获取配置
        config = {
            "api_base_url": printify_system.base_url or PRINTIFY_API_BASE,
            "shop_id": shop_id
            or printify_system.external_system_id
            or "21704929",  # 使用解密后的shop_id，或fallback到external_system_id，最后fallback到测试ID
            "access_token": access_token,
            # 暂时使用硬编码的测试商品参数，等后续有商品映射数据后再从数据库获取
            "default_product_id": "67f4a8963b41671184062a1e",
            "default_variant_id": 63300,  # 使用实际可用的变体ID
            "default_status": "onhold",
        }

        # 如果没有有效的shop_id，尝试从Printify API获取真实的商店列表
        if not shop_id and not printify_system.external_system_id:
            logger.warning("未找到有效的商店ID，尝试从Printify API获取商店列表")
            try:
                from app.services.printify_service import PrintifyService

                if access_token:
                    printify_service = PrintifyService(printify_api_token=access_token)
                    shops = await printify_service.get_shops()
                    if shops and len(shops) > 0:
                        # 使用第一个商店的ID
                        config["shop_id"] = str(shops[0].get("id", "21704929"))
                        logger.info(
                            f"✅ 从Printify API获取到真实商店ID: {config['shop_id']}"
                        )
                    else:
                        logger.warning("从Printify API未获取到商店列表，使用默认测试ID")
                else:
                    logger.warning("没有访问令牌，无法从Printify API获取商店列表")
            except Exception as e:
                logger.error(f"从Printify API获取商店列表失败: {e}")
                logger.warning("使用默认测试ID，这可能导致订单创建失败")

        logger.info(f"成功获取Printify配置: shop_id={config['shop_id']}")
        return config

    except Exception as e:
        logger.error(f"获取Printify配置失败: {e}")
        # 返回默认配置
        return {
            "api_base_url": PRINTIFY_API_BASE,
            "shop_id": "21704929",  # 默认测试ID，实际使用时需要配置真实的商店ID
            "access_token": None,
            # 暂时使用硬编码的测试商品参数
            "default_product_id": "67f4a8963b41671184062a1e",
            "default_variant_id": 63300,  # 使用实际可用的变体ID
            "default_status": "onhold",
        }


class PrintifyOrderRequest(BaseModel):
    """Printify订单创建请求"""

    order_id: int = Field(..., description="本地订单ID")
    customer_name: str = Field(..., description="客户姓名")
    customer_email: str = Field(..., description="客户邮箱")
    address_line1: str = Field(..., description="地址第一行")
    city: str = Field(..., description="城市")
    state: str = Field(..., description="州/省")
    country: str = Field(..., description="国家代码")
    zip_code: str = Field(..., description="邮政编码")
    phone: Optional[str] = Field(None, description="电话号码")
    quantity: int = Field(1, description="数量")


class PrintifyOrderResponse(BaseModel):
    """Printify订单创建响应"""

    success: bool
    printify_order_id: Optional[str] = None
    external_id: Optional[str] = None
    status: Optional[str] = None
    total_price: Optional[float] = None
    message: str


@router.post("/orders", response_model=PrintifyOrderResponse)
async def create_printify_order(
    request: PrintifyOrderRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    创建Printify订单
    """
    tenant, user = auth

    logger.info(
        "🔍 开始创建Printify订单",
        order_id=request.order_id,
        tenant_id=tenant.id,
        user_id=user.id,
    )

    try:
        # 从数据库获取Printify配置
        printify_config = await get_printify_config(db, tenant.id)

        # 检查是否有访问令牌
        if not printify_config["access_token"]:
            logger.error("❌ Printify访问令牌未配置")
            return PrintifyOrderResponse(
                success=False,
                message="Printify访问令牌未配置，请先在外部系统管理中配置Printify",
            )

        # 构建Printify订单数据
        external_id = (
            f"ORDER_{request.order_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        # 国家代码映射
        country_mapping = {
            "中国": "CN",
            "china": "CN",
            "美国": "US",
            "usa": "US",
            "日本": "JP",
            "japan": "JP",
            "英国": "GB",
            "uk": "GB",
            "加拿大": "CA",
            "canada": "CA",
            "澳大利亚": "AU",
            "australia": "AU",
        }

        # 获取标准国家代码
        country_code = country_mapping.get(
            request.country.lower(), request.country.upper()
        )

        order_data = {
            "external_id": external_id,
            "line_items": [
                {
                    "product_id": printify_config["default_product_id"],
                    "variant_id": printify_config["default_variant_id"],
                    "quantity": request.quantity,
                }
            ],
            "shipping_method": 1,
            "send_shipping_notification": True,
            "status": printify_config["default_status"],
            "address_to": {
                "first_name": (
                    request.customer_name.split(" ")[0]
                    if request.customer_name
                    else "Customer"
                ),
                "last_name": (
                    " ".join(request.customer_name.split(" ")[1:])
                    if len(request.customer_name.split(" ")) > 1
                    else ""
                ),
                "email": request.customer_email,
                "phone": request.phone or "",
                "country": country_code,
                "region": request.state,
                "city": request.city,
                "address1": request.address_line1,
                "address2": "",
                "zip": request.zip_code,
            },
        }

        logger.info(
            "📦 Printify订单数据构建完成",
            external_id=external_id,
            product_id=printify_config["default_product_id"],
            variant_id=printify_config["default_variant_id"],
        )

        # 使用错误处理器执行Printify API调用
        async def _create_order_operation():
            api_url = f"{printify_config['api_base_url']}/shops/{printify_config['shop_id']}/orders.json"
            headers = {
                "Authorization": f"Bearer {printify_config['access_token']}",
                "Content-Type": "application/json",
                "User-Agent": "SupplyNexus/1.0",
            }

            logger.info("📡 发送请求到Printify API", api_url=api_url)

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(api_url, headers=headers, json=order_data)
                response.raise_for_status()
                return response.json()

        result = await execute_printify_operation(
            _create_order_operation,
            "创建Printify订单"
        )

        logger.info(
            "✅ Printify订单创建成功",
            printify_order_id=result.get("id"),
            external_id=result.get("external_id"),
        )

        return PrintifyOrderResponse(
            success=True,
            printify_order_id=result.get("id"),
            external_id=result.get("external_id"),
            status=result.get("status"),
            total_price=(
                result.get("total_price", 0) / 100
                if result.get("total_price")
                else 0
            ),
            message="Printify订单创建成功",
        )

    except HTTPException:
        # 重新抛出HTTPException，不要被通用异常处理捕获
        raise
    except Exception as e:
        logger.error("❌ 创建Printify订单时发生未知错误", error=str(e))
        import traceback

        logger.error("   异常堆栈", stack=traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"创建Printify订单失败: {str(e)}")


@router.get("/products")
async def get_printify_products(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取Printify商品列表（用于测试）
    """
    tenant, user = auth

    logger.info("🔍 获取Printify商品列表", tenant_id=tenant.id)

    try:
        # 从数据库获取Printify配置
        printify_config = await get_printify_config(db, tenant.id)

        if not printify_config["access_token"]:
            logger.error("❌ Printify访问令牌未配置")
            return {"success": False, "message": "Printify访问令牌未配置"}

        api_url = f"{printify_config['api_base_url']}/shops/{printify_config['shop_id']}/products.json"
        headers = {
            "Authorization": f"Bearer {printify_config['access_token']}",
            "User-Agent": "SupplyNexus/1.0",
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(api_url, headers=headers)

            if response.status_code == 200:
                products = response.json()
                logger.info("✅ Printify商品列表获取成功", count=len(products))
                return {"products": products}
            else:
                logger.error(
                    "❌ 获取Printify商品列表失败", status_code=response.status_code
                )
                raise HTTPException(
                    status_code=400,
                    detail=f"获取Printify商品列表失败: {response.status_code}",
                )

    except Exception as e:
        logger.error("❌ 获取Printify商品列表时发生错误", error=str(e))
        raise HTTPException(
            status_code=500, detail=f"获取Printify商品列表失败: {str(e)}"
        )


@router.get("/orders", response_model=dict)
async def get_printify_orders_from_db(
    page: int = 1,
    limit: int = 20,
    status: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取数据库中的 Printify 订单列表（从 SCM 订单创建的）
    """
    tenant, user = auth
    
    logger.info(
        "🔍 开始获取数据库中的 Printify 订单列表",
        tenant_id=tenant.id,
        user_id=user.id,
        page=page,
        limit=limit,
        status=status,
        search=search
    )

    try:
        # 构建查询
        query = select(PrintifyOrder).where(
            PrintifyOrder.tenant_id == tenant.id
        ).options(
            selectinload(PrintifyOrder.external_system),
            selectinload(PrintifyOrder.scm_order)
        ).order_by(desc(PrintifyOrder.created_at))

        # 添加状态过滤
        if status and status != 'all':
            query = query.where(PrintifyOrder.status == status)

        # 添加搜索过滤（搜索外部订单ID或客户邮箱）
        if search:
            search_term = f"%{search}%"
            query = query.where(
                (PrintifyOrder.external_order_id.ilike(search_term)) |
                (PrintifyOrder.customer_email.ilike(search_term))
            )

        # 计算总数
        count_query = select(PrintifyOrder.id).where(
            PrintifyOrder.tenant_id == tenant.id
        )
        if status and status != 'all':
            count_query = count_query.where(PrintifyOrder.status == status)
        if search:
            search_term = f"%{search}%"
            count_query = count_query.where(
                (PrintifyOrder.external_order_id.ilike(search_term)) |
                (PrintifyOrder.customer_email.ilike(search_term))
            )

        total_result = await db.execute(count_query)
        total_count = len(total_result.fetchall())

        # 添加分页
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit)

        # 执行查询
        result = await db.execute(query)
        orders = result.scalars().all()

        logger.info(
            "✅ Printify 订单列表获取成功",
            count=len(orders),
            total=total_count,
            page=page
        )

        # 转换为响应格式
        orders_data = []
        for order in orders:
            order_data = {
                "id": order.id,
                "external_order_id": order.external_order_id,
                "scm_order_id": order.scm_order_id,
                "status": order.status,
                "total_price": order.total_price,
                "currency": order.currency,
                "customer_email": order.customer_email,
                "customer_name": order.customer_name,
                "shipping_address": order.shipping_address,
                "billing_address": order.billing_address,
                "tracking_number": order.tracking_number,
                "tracking_url": order.tracking_url,
                "carrier": order.carrier,
                "created_at": order.created_at.isoformat() if order.created_at else None,
                "updated_at": order.updated_at.isoformat() if order.updated_at else None,
                "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
                "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
                "external_system": {
                    "id": order.external_system.id,
                    "name": order.external_system.name,
                    "system_type": order.external_system.system_type
                } if order.external_system else None,
                "scm_order": {
                    "id": order.scm_order.id,
                    "scm_order_number": order.scm_order.scm_order_number,
                    "status": order.scm_order.status
                } if order.scm_order else None,
                "printify_data": order.printify_data,
                "external_data": order.external_data
            }
            orders_data.append(order_data)

        return {
            "success": True,
            "orders": orders_data,
            "total_count": total_count,
            "current_page": page,
            "per_page": limit,
            "total_pages": (total_count + limit - 1) // limit,
            "has_more": page * limit < total_count
        }

    except Exception as e:
        logger.error("❌ 获取 Printify 订单列表失败", error=str(e))
        import traceback
        logger.error("   异常堆栈", stack=traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"获取 Printify 订单列表失败: {str(e)}"
        )


@router.get("/orders/{order_id}", response_model=dict)
async def get_printify_order_details(
    order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    获取 Printify 订单详情
    """
    tenant, user = auth
    
    logger.info(
        "🔍 开始获取 Printify 订单详情",
        order_id=order_id,
        tenant_id=tenant.id,
        user_id=user.id
    )

    try:
        # 查询订单
        query = select(PrintifyOrder).where(
            PrintifyOrder.id == order_id,
            PrintifyOrder.tenant_id == tenant.id
        ).options(
            selectinload(PrintifyOrder.external_system),
            selectinload(PrintifyOrder.scm_order)
        )

        result = await db.execute(query)
        order = result.scalar_one_or_none()

        if not order:
            logger.error("❌ Printify 订单不存在", order_id=order_id)
            raise HTTPException(status_code=404, detail="Printify 订单不存在")

        logger.info("✅ Printify 订单详情获取成功", order_id=order_id)

        # 构建响应数据
        order_data = {
            "id": order.id,
            "external_order_id": order.external_order_id,
            "scm_order_id": order.scm_order_id,
            "status": order.status,
            "total_price": order.total_price,
            "currency": order.currency,
            "customer_email": order.customer_email,
            "customer_name": order.customer_name,
            "shipping_address": order.shipping_address,
            "billing_address": order.billing_address,
            "tracking_number": order.tracking_number,
            "tracking_url": order.tracking_url,
            "carrier": order.carrier,
            "created_at": order.created_at.isoformat() if order.created_at else None,
            "updated_at": order.updated_at.isoformat() if order.updated_at else None,
            "shipped_at": order.shipped_at.isoformat() if order.shipped_at else None,
            "delivered_at": order.delivered_at.isoformat() if order.delivered_at else None,
            "external_system": {
                "id": order.external_system.id,
                "name": order.external_system.name,
                "system_type": order.external_system.system_type
            } if order.external_system else None,
            "scm_order": {
                "id": order.scm_order.id,
                "scm_order_number": order.scm_order.scm_order_number,
                "status": order.scm_order.status
            } if order.scm_order else None,
            "printify_data": order.printify_data,
            "external_data": order.external_data
        }

        return {
            "success": True,
            "order": order_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("❌ 获取 Printify 订单详情失败", error=str(e))
        import traceback
        logger.error("   异常堆栈", stack=traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"获取 Printify 订单详情失败: {str(e)}"
        )


@router.post("/orders/sync-logistics", response_model=dict)
async def sync_printify_logistics(
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> Any:
    """
    同步 Printify 订单物流信息到 SCM 订单
    """
    tenant, user = auth
    
    logger.info(
        "🔍 开始同步 Printify 订单物流信息",
        tenant_id=tenant.id,
        user_id=user.id
    )

    try:
        # 获取所有待同步的 Printify 订单
        query = select(PrintifyOrder).where(
            PrintifyOrder.tenant_id == tenant.id,
            PrintifyOrder.scm_order_id.isnot(None),
            PrintifyOrder.status.in_(['shipped', 'delivered'])
        ).options(
            selectinload(PrintifyOrder.scm_order)
        )

        result = await db.execute(query)
        orders = result.scalars().all()

        logger.info(f"✅ 找到 {len(orders)} 个需要同步物流信息的订单")

        synced_count = 0
        errors = []

        for order in orders:
            try:
                # 检查是否需要更新物流信息
                needs_update = False
                
                # 检查跟踪号
                if order.tracking_number and order.scm_order.tracking_number != order.tracking_number:
                    order.scm_order.tracking_number = order.tracking_number
                    needs_update = True

                # 检查跟踪链接
                if order.tracking_url and order.scm_order.tracking_url != order.tracking_url:
                    order.scm_order.tracking_url = order.tracking_url
                    needs_update = True

                # 检查承运商
                if order.carrier and order.scm_order.carrier != order.carrier:
                    order.scm_order.carrier = order.carrier
                    needs_update = True

                # 检查发货时间
                if order.shipped_at and not order.scm_order.shipped_at:
                    order.scm_order.shipped_at = order.shipped_at
                    needs_update = True

                # 检查送达时间
                if order.delivered_at and not order.scm_order.delivered_at:
                    order.scm_order.delivered_at = order.delivered_at
                    needs_update = True

                # 更新订单状态
                if order.status == 'shipped' and order.scm_order.fulfillment_status != 'shipped':
                    order.scm_order.fulfillment_status = 'shipped'
                    needs_update = True
                elif order.status == 'delivered' and order.scm_order.fulfillment_status != 'delivered':
                    order.scm_order.fulfillment_status = 'delivered'
                    needs_update = True

                if needs_update:
                    # 更新 SCM 订单
                    order.scm_order.updated_at = datetime.now()
                    db.add(order.scm_order)
                    
                    # 更新 Printify 订单的同步时间
                    order.updated_at = datetime.now()
                    db.add(order)
                    
                    synced_count += 1
                    logger.info(f"✅ 同步物流信息成功: Printify订单 {order.id} -> SCM订单 {order.scm_order.id}")

            except Exception as e:
                error_msg = f"同步订单 {order.id} 失败: {str(e)}"
                logger.error(f"❌ {error_msg}")
                errors.append(error_msg)

        # 提交所有更改
        await db.commit()

        logger.info(f"✅ 物流信息同步完成: 成功 {synced_count} 个，错误 {len(errors)} 个")

        return {
            "success": True,
            "message": f"物流信息同步完成",
            "synced_count": synced_count,
            "total_orders": len(orders),
            "errors": errors,
            "error_count": len(errors)
        }

    except Exception as e:
        logger.error("❌ 同步 Printify 订单物流信息失败", error=str(e))
        import traceback
        logger.error("   异常堆栈", stack=traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"同步 Printify 订单物流信息失败: {str(e)}"
        )

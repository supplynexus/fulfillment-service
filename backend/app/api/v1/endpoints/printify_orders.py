"""
Printify订单管理API端点
"""

from fastapi import APIRouter, Depends, HTTPException, status, Body
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
                "shop_id": "24981565",  # 硬编码的测试商店ID
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
            or "24981565",  # 使用解密后的shop_id，或fallback到external_system_id，最后fallback到测试ID
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
                        config["shop_id"] = str(shops[0].get("id", "24981565"))
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
            "shop_id": "24981565",  # 默认测试ID，实际使用时需要配置真实的商店ID
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


class PrintifyOrderSaveRequest(BaseModel):
    """保存Printify订单到数据库的请求"""
    
    external_order_id: str = Field(..., description="Printify订单ID")
    external_system_id: str = Field(..., description="外部系统ID (hashid)")
    status: str = Field(..., description="订单状态")
    total_price: float = Field(..., description="总价格")
    currency: str = Field(default="USD", description="货币")
    customer_email: str = Field(..., description="客户邮箱")
    customer_name: str = Field(..., description="客户姓名")
    shipping_address: Dict[str, Any] = Field(..., description="收货地址")
    billing_address: Optional[Dict[str, Any]] = Field(None, description="账单地址")
    printify_data: Dict[str, Any] = Field(..., description="Printify原始数据")
    external_data: Dict[str, Any] = Field(..., description="外部数据")
    scm_order_id: Optional[int] = Field(None, description="关联的SCM订单ID")


class PrintifyOrderSaveResponse(BaseModel):
    """保存Printify订单响应"""
    
    success: bool
    order_id: Optional[int] = None
    message: Optional[str] = None


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
                "tracking_company": order.carrier,  # 添加前端期望的字段名
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


@router.post("/save", response_model=PrintifyOrderSaveResponse)
async def save_printify_order_to_database(
    request: PrintifyOrderSaveRequest,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth),
) -> PrintifyOrderSaveResponse:
    """
    保存从 Printify API 获取的订单到数据库
    """
    tenant, user = auth

    logger.info(
        "🔍 开始保存 Printify 订单到数据库",
        external_order_id=request.external_order_id,
        tenant_id=tenant.id,
        user_id=user.id,
    )

    try:
        # 解码外部系统 ID (hashid)
        from app.core.hashids_utils import decode_id
        
        try:
            external_system_id = decode_id(request.external_system_id)
            logger.info(f"✅ 外部系统 ID 解码成功: {request.external_system_id} -> {external_system_id}")
        except Exception as e:
            logger.error(f"❌ 外部系统 ID 解码失败: {request.external_system_id}, 错误: {str(e)}")
            return PrintifyOrderSaveResponse(
                success=False,
                message=f"无效的外部系统 ID: {str(e)}"
            )

        # 检查外部系统是否存在
        external_system = await db.get(ExternalSystem, external_system_id)
        if not external_system or external_system.tenant_id != tenant.id:
            logger.error(f"❌ 外部系统不存在或无权限: {external_system_id}")
            return PrintifyOrderSaveResponse(
                success=False,
                message="外部系统不存在或无权限"
            )

        # 检查订单是否已存在 - 优先使用 external_system_id，如果找不到则尝试不使用 external_system_id
        from sqlalchemy import select, and_
        
        # 首先尝试使用三个条件查找（包括 external_system_id）
        existing_order_result = await db.execute(
            select(PrintifyOrder).where(
                and_(
                    PrintifyOrder.external_order_id == request.external_order_id,
                    PrintifyOrder.tenant_id == tenant.id,
                    PrintifyOrder.external_system_id == external_system_id
                )
            )
        )
        existing_order = existing_order_result.scalar_one_or_none()
        
        # 如果找不到，尝试不使用 external_system_id 查找（用于从 SCM 订单创建的订单）
        if not existing_order:
            logger.info(f"🔍 使用 external_system_id 未找到订单，尝试不使用 external_system_id 查找: external_order_id={request.external_order_id}")
            existing_order_result = await db.execute(
                select(PrintifyOrder).where(
                    and_(
                        PrintifyOrder.external_order_id == request.external_order_id,
                        PrintifyOrder.tenant_id == tenant.id
                    )
                )
            )
            existing_order = existing_order_result.scalar_one_or_none()
        
        if existing_order:
            # 更新现有订单（保留已有的 scm_order_id 和物流信息）
            logger.info(f"🔄 更新现有 Printify 订单: {request.external_order_id}")
            existing_order.external_system_id = external_system_id
            # 保留已有的 scm_order_id，如果请求中没有提供则保持原值
            if request.scm_order_id is not None:
                existing_order.scm_order_id = request.scm_order_id
            existing_order.status = request.status
            existing_order.total_price = request.total_price
            existing_order.currency = request.currency
            existing_order.customer_email = request.customer_email
            existing_order.customer_name = request.customer_name
            existing_order.shipping_address = request.shipping_address
            existing_order.billing_address = request.billing_address
            existing_order.printify_data = request.printify_data
            existing_order.external_data = request.external_data
            # 注意：不更新物流信息字段（tracking_number, tracking_url, carrier, shipped_at, delivered_at）
            # 这些字段应该通过 update-tracking 端点更新
            
            printify_order = existing_order
        else:
            # 创建新的 Printify 订单记录
            logger.info(f"➕ 创建新的 Printify 订单: {request.external_order_id}")
            printify_order = PrintifyOrder(
                tenant_id=tenant.id,
                external_system_id=external_system_id,
                external_order_id=request.external_order_id,
                scm_order_id=request.scm_order_id,
                status=request.status,
                total_price=request.total_price,
                currency=request.currency,
                customer_email=request.customer_email,
                customer_name=request.customer_name,
                shipping_address=request.shipping_address,
                billing_address=request.billing_address,
                printify_data=request.printify_data,
                external_data=request.external_data,
                tracking_number=request.external_data.get('tracking_number'),
                tracking_url=request.external_data.get('tracking_url'),
                carrier=request.external_data.get('carrier'),
            )

            # 如果有发货信息，设置发货时间
            if request.external_data.get('shipments') and len(request.external_data['shipments']) > 0:
                shipment = request.external_data['shipments'][0]
                if shipment.get('shipped_at'):
                    from datetime import datetime
                    try:
                        printify_order.shipped_at = datetime.fromisoformat(shipment['shipped_at'].replace('Z', '+00:00'))
                    except:
                        pass
                if shipment.get('delivered_at'):
                    try:
                        printify_order.delivered_at = datetime.fromisoformat(shipment['delivered_at'].replace('Z', '+00:00'))
                    except:
                        pass

            db.add(printify_order)

        await db.commit()
        await db.refresh(printify_order)

        logger.info(
            "✅ Printify 订单保存到数据库成功",
            order_id=printify_order.id,
            external_order_id=request.external_order_id,
            tenant_id=tenant.id,
        )

        return PrintifyOrderSaveResponse(
            success=True,
            order_id=printify_order.id,
            message="订单保存成功"
        )

    except Exception as e:
        logger.error("❌ 保存 Printify 订单到数据库失败", error=str(e))
        import traceback
        logger.error("   异常堆栈", stack=traceback.format_exc())
        return PrintifyOrderSaveResponse(
            success=False,
            message=f"保存订单失败: {str(e)}"
        )


@router.post("/update-scm-status", response_model=dict)
async def update_scm_status(
    request: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    更新SCM订单状态 - 将Printify订单的物流信息同步到关联的SCM订单
    """
    tenant, user = auth
    
    try:
        order_ids = request.get('order_ids', [])
        if not order_ids:
            raise HTTPException(status_code=400, detail="请提供要更新的订单ID列表")
        
        logger.info(f"🔄 开始更新SCM订单状态: order_ids={order_ids}, tenant_id={tenant.id}")
        
        # 查询选中的Printify订单
        from app.models.printify_order import PrintifyOrder
        from app.models.scm_order import SCMOrder
        from sqlalchemy import select, and_
        from datetime import datetime
        
        printify_orders = await db.execute(
            select(PrintifyOrder).where(
                and_(
                    PrintifyOrder.id.in_(order_ids),
                    PrintifyOrder.tenant_id == tenant.id,
                    PrintifyOrder.scm_order_id.isnot(None)
                )
            )
        )
        orders = printify_orders.scalars().all()
        
        if not orders:
            raise HTTPException(status_code=404, detail="未找到有效的Printify订单")
        
        updated_count = 0
        
        for order in orders:
            if not order.scm_order_id:
                continue
                
            # 查询关联的SCM订单
            scm_order_result = await db.execute(
                select(SCMOrder).where(
                    and_(
                        SCMOrder.id == order.scm_order_id,
                        SCMOrder.tenant_id == tenant.id
                    )
                )
            )
            scm_order = scm_order_result.scalar_one_or_none()
            
            if not scm_order:
                logger.warning(f"⚠️ 未找到关联的SCM订单: printify_order_id={order.id}, scm_order_id={order.scm_order_id}")
                continue
            
            # 更新SCM订单的物流信息
            updated = False
            
            # 更新跟踪号
            if order.tracking_number and scm_order.tracking_number != order.tracking_number:
                scm_order.tracking_number = order.tracking_number
                updated = True
                logger.info(f"✅ 更新跟踪号: {order.tracking_number}")
            
            # 更新跟踪URL
            if order.tracking_url and scm_order.tracking_url != order.tracking_url:
                scm_order.tracking_url = order.tracking_url
                updated = True
                logger.info(f"✅ 更新跟踪URL: {order.tracking_url}")
            
            # 更新承运商
            if order.carrier and scm_order.carrier != order.carrier:
                scm_order.carrier = order.carrier
                updated = True
                logger.info(f"✅ 更新承运商: {order.carrier}")
            
            # 更新发货时间
            if order.shipped_at and not scm_order.shipped_at:
                scm_order.shipped_at = order.shipped_at
                updated = True
                logger.info(f"✅ 更新发货时间: {order.shipped_at}")
            
            # 更新送达时间
            if order.delivered_at and not scm_order.delivered_at:
                scm_order.delivered_at = order.delivered_at
                updated = True
                logger.info(f"✅ 更新送达时间: {order.delivered_at}")
            
            # 更新履行状态
            if order.status == 'shipped' and scm_order.fulfillment_status != 'shipped':
                scm_order.fulfillment_status = 'shipped'
                updated = True
                logger.info(f"✅ 更新履行状态为已发货")
            elif order.status == 'delivered' and scm_order.fulfillment_status != 'delivered':
                scm_order.fulfillment_status = 'delivered'
                updated = True
                logger.info(f"✅ 更新履行状态为已送达")
            
            if updated:
                scm_order.updated_at = datetime.now()
                db.add(scm_order)
                updated_count += 1
                logger.info(f"✅ SCM订单更新成功: scm_order_id={scm_order.id}, printify_order_id={order.id}")
        
        await db.commit()
        
        logger.info(f"✅ SCM订单状态更新完成: 共更新了 {updated_count} 个订单")
        
        return {
            "success": True,
            "message": f"成功更新了 {updated_count} 个SCM订单的物流信息",
            "updated_count": updated_count
        }
        
    except Exception as e:
        logger.error(f"❌ 更新SCM订单状态失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"更新SCM订单状态失败: {str(e)}")


@router.post("/update-tracking", response_model=dict)
async def update_printify_order_tracking(
    request: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> Any:
    """
    更新Printify订单的物流信息到本地数据库
    """
    tenant, user = auth
    
    try:
        external_order_id = request.get('external_order_id')
        external_system_id_hashid = request.get('external_system_id')
        tracking_number = request.get('tracking_number')
        tracking_url = request.get('tracking_url')
        carrier = request.get('carrier')
        shipped_at = request.get('shipped_at')
        delivered_at = request.get('delivered_at')
        status = request.get('status')
        
        if not external_order_id or not external_system_id_hashid:
            raise HTTPException(status_code=400, detail="缺少必要参数")
        
        logger.info(f"🔄 开始更新Printify订单物流信息: external_order_id={external_order_id}, tenant_id={tenant.id}")
        
        # 解码外部系统ID
        from app.core.hashids_utils import decode_id
        try:
            external_system_id = decode_id(external_system_id_hashid)
            logger.info(f"✅ 外部系统ID解码成功: {external_system_id_hashid} -> {external_system_id}")
        except Exception as e:
            logger.error(f"❌ 外部系统ID解码失败: {external_system_id_hashid}, 错误: {str(e)}")
            raise HTTPException(status_code=400, detail=f"无效的外部系统ID: {str(e)}")
        
        # 查找Printify订单 - 优先使用 external_system_id，如果找不到则尝试不使用 external_system_id
        from sqlalchemy import select, and_
        
        # 首先尝试使用三个条件查找（包括 external_system_id）
        printify_order_result = await db.execute(
            select(PrintifyOrder).where(
                and_(
                    PrintifyOrder.external_order_id == external_order_id,
                    PrintifyOrder.tenant_id == tenant.id,
                    PrintifyOrder.external_system_id == external_system_id
                )
            )
        )
        printify_order = printify_order_result.scalar_one_or_none()
        
        # 如果找不到，尝试不使用 external_system_id 查找（用于从 SCM 订单创建的订单）
        if not printify_order:
            logger.info(f"🔍 使用 external_system_id 未找到订单，尝试不使用 external_system_id 查找: external_order_id={external_order_id}")
            printify_order_result = await db.execute(
                select(PrintifyOrder).where(
                    and_(
                        PrintifyOrder.external_order_id == external_order_id,
                        PrintifyOrder.tenant_id == tenant.id
                    )
                )
            )
            printify_order = printify_order_result.scalar_one_or_none()
        
        if not printify_order:
            logger.warning(f"⚠️ 未找到Printify订单: external_order_id={external_order_id}, external_system_id={external_system_id}, tenant_id={tenant.id}")
            # 记录所有匹配的订单以便调试
            all_orders_result = await db.execute(
                select(PrintifyOrder).where(
                    PrintifyOrder.tenant_id == tenant.id
                )
            )
            all_orders = all_orders_result.scalars().all()
            matching_orders = [o for o in all_orders if o.external_order_id == external_order_id]
            logger.warning(f"🔍 调试信息: 租户下共有 {len(all_orders)} 个订单，其中 external_order_id={external_order_id} 的订单有 {len(matching_orders)} 个")
            if matching_orders:
                for o in matching_orders:
                    logger.warning(f"   找到订单: id={o.id}, external_order_id={o.external_order_id}, external_system_id={o.external_system_id}")
            return {
                "success": False,
                "message": "未找到对应的Printify订单，请先保存订单到本地数据库"
            }
        
        # 更新物流信息
        updated = False
        
        # 记录接收到的参数
        logger.info(f"🔍 接收到的物流信息参数", {
            "tracking_number": tracking_number,
            "tracking_url": tracking_url,
            "carrier": carrier,
            "shipped_at": shipped_at,
            "delivered_at": delivered_at,
            "status": status
        })
        
        # 更新跟踪号（包括 None 值）
        if printify_order.tracking_number != tracking_number:
            printify_order.tracking_number = tracking_number
            updated = True
            logger.info(f"✅ 更新跟踪号: {tracking_number}")
        
        # 更新跟踪URL（包括 None 值）
        if printify_order.tracking_url != tracking_url:
            printify_order.tracking_url = tracking_url
            updated = True
            logger.info(f"✅ 更新跟踪URL: {tracking_url}")
        
        # 更新承运商（包括 None 值）
        if printify_order.carrier != carrier:
            printify_order.carrier = carrier
            updated = True
            logger.info(f"✅ 更新承运商: {carrier}")
        
        # 更新发货时间
        if shipped_at is not None and not printify_order.shipped_at:
            try:
                printify_order.shipped_at = datetime.fromisoformat(shipped_at.replace('Z', '+00:00'))
                updated = True
                logger.info(f"✅ 更新发货时间: {shipped_at}")
            except:
                pass
        
        # 更新送达时间
        if delivered_at is not None and not printify_order.delivered_at:
            try:
                printify_order.delivered_at = datetime.fromisoformat(delivered_at.replace('Z', '+00:00'))
                updated = True
                logger.info(f"✅ 更新送达时间: {delivered_at}")
            except:
                pass
        
        # 更新状态
        if status is not None and printify_order.status != status:
            printify_order.status = status
            updated = True
            logger.info(f"✅ 更新状态: {status}")
        
        if updated:
            printify_order.updated_at = datetime.now()
            db.add(printify_order)
            await db.commit()
            logger.info(f"✅ Printify订单物流信息更新成功: external_order_id={external_order_id}")
            return {
                "success": True,
                "message": "物流信息更新成功"
            }
        else:
            logger.info(f"ℹ️ 无需更新: external_order_id={external_order_id}")
            return {
                "success": True,
                "message": "物流信息无需更新"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 更新Printify订单物流信息失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"更新物流信息失败: {str(e)}")


@router.post("/{printify_order_id}/create-scm-and-bind", response_model=dict)
async def create_scm_from_printify_and_bind(
    printify_order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> dict:
    """
    从 Printify 同步订单创建 SCM 订单并绑定（用于「未关联」的 Printify 订单）。
    """
    from app.core.logging import RequestLogger
    from app.models.scm_order import SCMOrder
    from app.services.order_number_service import OrderNumberService
    from app.core.hashids_utils import encode_id
    from sqlalchemy import and_

    logger = RequestLogger("printify_orders.create_scm_and_bind")
    tenant, user = auth

    printify_result = await db.execute(
        select(PrintifyOrder).where(
            and_(
                PrintifyOrder.id == printify_order_id,
                PrintifyOrder.tenant_id == tenant.id
            )
        )
    )
    printify_order = printify_result.scalar_one_or_none()
    if not printify_order:
        raise HTTPException(status_code=404, detail="Printify order not found")
    if printify_order.scm_order_id:
        raise HTTPException(
            status_code=400,
            detail="Printify order is already bound to an SCM order"
        )

    # Build line_items from Printify order (external_data or printify_data)
    raw = printify_order.external_data or printify_order.printify_data or {}
    raw_items = raw.get("line_items") or []
    line_items = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        meta = item.get("metadata") or {}
        line_items.append({
            "core_product_id": None,
            "core_variant_id": None,
            "quantity": int(item.get("quantity") or 1),
            "metadata": {
                "title": meta.get("title"),
                "sku": meta.get("sku"),
                "variant_label": meta.get("variant_label"),
                "source_line_item_id": item.get("id"),
            },
        })
    if not line_items:
        line_items = [{"core_product_id": None, "core_variant_id": None, "quantity": 1, "metadata": {}}]

    scm_order_number = await OrderNumberService.generate_scm_order_number(db, tenant.id)
    routing_metadata = {
        "target_system_type": "PRINTIFY",
        "target_system_id": None,
        "created_from_printify_order_id": printify_order_id,
        "created_from_printify_external_id": printify_order.external_order_id,
        "created_at": datetime.utcnow().isoformat(),
        "created_by": user.email,
    }
    shipping_address = printify_order.shipping_address if isinstance(printify_order.shipping_address, dict) else {}
    if not shipping_address:
        shipping_address = {"country": "US"}

    scm_order = SCMOrder(
        tenant_id=tenant.id,
        source_order_id=None,
        scm_order_number=scm_order_number,
        status="created",
        routing_strategy="manual",
        line_items=line_items,
        currency=printify_order.currency or "USD",
        customer_email=printify_order.customer_email or "",
        customer_name=printify_order.customer_name,
        customer_phone=None,
        shipping_address=shipping_address,
        billing_address=printify_order.billing_address if isinstance(printify_order.billing_address, dict) else None,
        routing_metadata=routing_metadata,
    )
    db.add(scm_order)
    await db.flush()

    # Bind
    printify_order.scm_order_id = scm_order.id
    scm_order.printify_order_id = printify_order.external_order_id
    scm_order.printify_shop_id = str(printify_order.external_system_id)
    if not scm_order.routing_metadata:
        scm_order.routing_metadata = {}
    scm_order.routing_metadata["printify_order_id"] = printify_order.external_order_id
    scm_order.routing_metadata["printify_bind_at"] = datetime.utcnow().isoformat()
    scm_order.routing_metadata["printify_bind_by"] = user.email

    await db.commit()
    await db.refresh(scm_order)

    logger.info(
        "create_scm_and_bind success",
        scm_order_id=scm_order.id,
        printify_order_id=printify_order_id,
    )
    return {
        "success": True,
        "message": "SCM order created and bound to Printify order",
        "scm_order_id": scm_order.id,
        "scm_order_hashid": encode_id(scm_order.id),
        "scm_order_number": scm_order.scm_order_number,
        "printify_order_id": printify_order_id,
        "printify_external_order_id": printify_order.external_order_id,
    }


@router.post("/{printify_order_id}/bind-scm-order", response_model=dict)
async def bind_scm_order_to_printify(
    printify_order_id: int,
    request_data: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> dict:
    """
    将 SCM 订单绑定到 Printify 订单
    """
    from app.core.hashids_utils import decode_id
    from app.core.logging import RequestLogger
    from app.models.scm_order import SCMOrder
    from app.models.printify_order import PrintifyOrder
    from sqlalchemy import select, and_
    from fastapi import HTTPException
    from datetime import datetime

    logger = RequestLogger("printify_orders.bind_scm_order")
    tenant, user = auth

    try:
        # 获取 SCM 订单 hashid
        scm_order_hashid = request_data.get('scm_order_hashid')
        if not scm_order_hashid:
            raise HTTPException(status_code=400, detail="SCM order hashid is required")

        # 解码 SCM 订单 hashid
        scm_order_id = decode_id(scm_order_hashid)
        logger.info(f"✅ SCM 订单 Hashid 解码成功: {scm_order_hashid} -> {scm_order_id}")
    except Exception as e:
        logger.error(f"❌ SCM 订单 Hashid 解码失败: {scm_order_hashid}, 错误: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid SCM order ID")

    try:
        # 查询 Printify 订单
        printify_result = await db.execute(
            select(PrintifyOrder).where(
                and_(
                    PrintifyOrder.id == printify_order_id,
                    PrintifyOrder.tenant_id == tenant.id
                )
            )
        )
        printify_order = printify_result.scalar_one_or_none()

        if not printify_order:
            logger.error(f"❌ Printify 订单不存在: printify_order_id={printify_order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Printify order not found")

        # 查询 SCM 订单
        scm_result = await db.execute(
            select(SCMOrder).where(
                and_(
                    SCMOrder.id == scm_order_id,
                    SCMOrder.tenant_id == tenant.id
                )
            )
        )
        scm_order = scm_result.scalar_one_or_none()

        if not scm_order:
            logger.error(f"❌ SCM 订单不存在: scm_order_id={scm_order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="SCM order not found")

        # 检查 Printify 订单是否已经绑定到其他 SCM 订单
        if printify_order.scm_order_id and printify_order.scm_order_id != scm_order_id:
            logger.warning(f"⚠️ Printify 订单已绑定到其他 SCM 订单: printify_order_id={printify_order_id}, existing_scm_order_id={printify_order.scm_order_id}")
            raise HTTPException(status_code=400, detail="Printify order is already bound to another SCM order")

        # 检查 SCM 订单是否已经绑定到其他 Printify 订单
        existing_printify_result = await db.execute(
            select(PrintifyOrder).where(
                and_(
                    PrintifyOrder.scm_order_id == scm_order_id,
                    PrintifyOrder.tenant_id == tenant.id,
                    PrintifyOrder.id != printify_order_id
                )
            )
        )
        existing_printify_order = existing_printify_result.scalar_one_or_none()

        if existing_printify_order:
            logger.warning(f"⚠️ SCM 订单已绑定到其他 Printify 订单: scm_order_id={scm_order_id}, existing_printify_order_id={existing_printify_order.id}")
            raise HTTPException(status_code=400, detail="SCM order is already bound to another Printify order")

        # 执行绑定
        printify_order.scm_order_id = scm_order_id
        scm_order.printify_order_id = printify_order.external_order_id
        scm_order.printify_shop_id = str(printify_order.external_system_id)

        # 更新路由元数据
        if not scm_order.routing_metadata:
            scm_order.routing_metadata = {}
        scm_order.routing_metadata['printify_order_id'] = printify_order.external_order_id
        scm_order.routing_metadata['printify_bind_at'] = datetime.utcnow().isoformat()
        scm_order.routing_metadata['printify_bind_by'] = user.email

        await db.commit()

        logger.info(f"✅ SCM 订单绑定成功: scm_order_id={scm_order_id}, printify_order_id={printify_order_id}")

        return {
            "success": True,
            "message": "SCM order bound to Printify order successfully",
            "scm_order_id": scm_order_id,
            "printify_order_id": printify_order_id,
            "scm_order_number": scm_order.scm_order_number,
            "printify_external_order_id": printify_order.external_order_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 绑定 SCM 订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to bind SCM order: {str(e)}")


@router.post("/{printify_order_id}/unbind-scm-order", response_model=dict)
async def unbind_scm_order_from_printify(
    printify_order_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> dict:
    """
    解绑 Printify 订单与 SCM 订单的关联
    """
    from app.core.logging import RequestLogger
    from app.models.scm_order import SCMOrder
    from app.models.printify_order import PrintifyOrder
    from sqlalchemy import select, and_
    from fastapi import HTTPException
    from datetime import datetime

    logger = RequestLogger("printify_orders.unbind_scm_order")
    tenant, user = auth

    try:
        # 查询 Printify 订单
        printify_result = await db.execute(
            select(PrintifyOrder).where(
                and_(
                    PrintifyOrder.id == printify_order_id,
                    PrintifyOrder.tenant_id == tenant.id
                )
            )
        )
        printify_order = printify_result.scalar_one_or_none()

        if not printify_order:
            logger.error(f"❌ Printify 订单不存在: printify_order_id={printify_order_id}, tenant_id={tenant.id}")
            raise HTTPException(status_code=404, detail="Printify order not found")

        if not printify_order.scm_order_id:
            logger.warning(f"⚠️ Printify 订单没有绑定任何 SCM 订单: printify_order_id={printify_order_id}")
            raise HTTPException(status_code=404, detail="No SCM order bound to this Printify order")

        # 查询绑定的 SCM 订单
        scm_result = await db.execute(
            select(SCMOrder).where(
                and_(
                    SCMOrder.id == printify_order.scm_order_id,
                    SCMOrder.tenant_id == tenant.id
                )
            )
        )
        scm_order = scm_result.scalar_one_or_none()

        if not scm_order:
            logger.warning(f"⚠️ 绑定的 SCM 订单不存在: scm_order_id={printify_order.scm_order_id}")
            # 即使 SCM 订单不存在，也要清理 Printify 订单的绑定
            printify_order.scm_order_id = None
            await db.commit()
            return {
                "success": True,
                "message": "SCM order unbound from Printify order successfully (SCM order was missing)",
                "printify_order_id": printify_order_id,
                "printify_external_order_id": printify_order.external_order_id
            }

        # 执行解绑
        printify_order.scm_order_id = None
        scm_order.printify_order_id = None
        scm_order.printify_shop_id = None

        # 更新路由元数据
        if scm_order.routing_metadata:
            scm_order.routing_metadata.pop('printify_order_id', None)
            scm_order.routing_metadata['printify_unbind_at'] = datetime.utcnow().isoformat()
            scm_order.routing_metadata['printify_unbind_by'] = user.email

        await db.commit()

        logger.info(f"✅ SCM 订单解绑成功: scm_order_id={scm_order.id}, printify_order_id={printify_order_id}")

        return {
            "success": True,
            "message": "SCM order unbound from Printify order successfully",
            "scm_order_id": scm_order.id,
            "printify_order_id": printify_order_id,
            "scm_order_number": scm_order.scm_order_number,
            "printify_external_order_id": printify_order.external_order_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 解绑 SCM 订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to unbind SCM order: {str(e)}")


@router.post("/orders/batch-delete", response_model=dict)
async def batch_delete_printify_orders(
    request: dict = Body(...),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> dict:
    """
    批量删除 Printify 本地订单
    """
    tenant, user = auth
    
    try:
        order_ids = request.get('order_ids', [])
        if not order_ids or not isinstance(order_ids, list):
            raise HTTPException(status_code=400, detail="请提供要删除的订单ID列表")
        
        logger.info(f"🗑️ 开始批量删除 Printify 订单: order_ids={order_ids}, tenant_id={tenant.id}, user_id={user.id}")
        
        # 查询要删除的订单
        from sqlalchemy import select, and_
        
        orders_result = await db.execute(
            select(PrintifyOrder).where(
                and_(
                    PrintifyOrder.id.in_(order_ids),
                    PrintifyOrder.tenant_id == tenant.id
                )
            )
        )
        orders = orders_result.scalars().all()
        
        if not orders:
            logger.warning(f"⚠️ 未找到要删除的订单: order_ids={order_ids}")
            return {
                "success": False,
                "message": "未找到要删除的订单",
                "deleted_count": 0
            }
        
        # 记录要删除的订单信息
        deleted_order_ids = [order.id for order in orders]
        deleted_external_order_ids = [order.external_order_id for order in orders]
        
        logger.info(f"🔍 找到 {len(orders)} 个订单待删除: {deleted_order_ids}")
        
        # 检查是否有订单关联了 SCM 订单
        orders_with_scm = [order for order in orders if order.scm_order_id]
        if orders_with_scm:
            logger.warning(f"⚠️ 有 {len(orders_with_scm)} 个订单关联了 SCM 订单，将同时解绑")
            scm_order_ids = [order.scm_order_id for order in orders_with_scm]
            
            # 查询关联的 SCM 订单并解绑
            from app.models.scm_order import SCMOrder
            scm_result = await db.execute(
                select(SCMOrder).where(
                    and_(
                        SCMOrder.id.in_(scm_order_ids),
                        SCMOrder.tenant_id == tenant.id
                    )
                )
            )
            scm_orders = scm_result.scalars().all()
            
            for scm_order in scm_orders:
                scm_order.printify_order_id = None
                scm_order.printify_shop_id = None
                if scm_order.routing_metadata:
                    scm_order.routing_metadata.pop('printify_order_id', None)
                    scm_order.routing_metadata['printify_unbind_at'] = datetime.utcnow().isoformat()
                    scm_order.routing_metadata['printify_unbind_by'] = user.email
                logger.info(f"✅ 已解绑 SCM 订单: scm_order_id={scm_order.id}")
        
        # 删除 Printify 订单
        for order in orders:
            await db.delete(order)
        
        await db.commit()
        
        logger.info(f"✅ 批量删除 Printify 订单成功: 删除了 {len(orders)} 个订单")
        
        return {
            "success": True,
            "message": f"成功删除 {len(orders)} 个订单",
            "deleted_count": len(orders),
            "deleted_order_ids": deleted_order_ids,
            "deleted_external_order_ids": deleted_external_order_ids
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ 批量删除 Printify 订单失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"批量删除订单失败: {str(e)}")

"""
商品映射检查 API
检查核心商品与外部系统（如 Printify）的映射关系
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.models.product import Product, ProductVariant, ProductMapping, ExternalProduct
from app.core.logging import RequestLogger
from typing import List, Dict, Any
from pydantic import BaseModel
from typing import Optional

router = APIRouter()


class MappingStatus(BaseModel):
    """映射状态"""
    core_variant_id: int
    core_variant_sku: str
    core_variant_name: str
    is_mapped: bool
    external_product_id: Optional[int] = None
    external_variant_id: Optional[int] = None
    external_sku: Optional[str] = None
    external_name: Optional[str] = None
    mapping_id: Optional[int] = None


class ProductMappingCheckResponse(BaseModel):
    """商品映射检查响应"""
    scm_order_id: int
    total_items: int
    mapped_items: int
    unmapped_items: int
    mapping_status: List[MappingStatus]
    can_fulfill: bool


@router.get("/scm-orders/{scm_order_hashid}/mapping-check", response_model=ProductMappingCheckResponse)
async def check_scm_order_mapping(
    scm_order_hashid: str,
    external_system: str = "printify",
    db: AsyncSession = Depends(get_async_db),
    auth: tuple = Depends(verify_tenant_auth)
) -> ProductMappingCheckResponse:
    """
    检查 SCM 订单的商品映射状态
    """
    from app.core.hashids_utils import decode_id
    from app.models.scm_order import SCMOrder
    
    logger = RequestLogger("product_mapping_check.check_scm_order_mapping")
    tenant, user = auth

    try:
        # 解码 hashid
        scm_order_id = decode_id(scm_order_hashid)
        logger.info(f"✅ Hashid 解码成功: {scm_order_hashid} -> {scm_order_id}")
    except Exception as e:
        logger.error(f"❌ Hashid 解码失败: {scm_order_hashid}, 错误: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid SCM order ID")

    # 查询 SCM 订单
    result = await db.execute(
        select(SCMOrder).where(
            SCMOrder.id == scm_order_id, 
            SCMOrder.tenant_id == tenant.id
        )
    )
    scm_order = result.scalar_one_or_none()

    if not scm_order:
        logger.error(f"❌ SCM 订单不存在: scm_order_id={scm_order_id}, tenant_id={tenant.id}")
        raise HTTPException(status_code=404, detail="SCM order not found")

    # 获取订单中的商品变体
    line_items = scm_order.line_items or []
    core_variant_ids = [item.get("core_variant_id") for item in line_items if item.get("core_variant_id")]
    
    if not core_variant_ids:
        logger.warning(f"⚠️ SCM 订单没有商品: scm_order_id={scm_order_id}")
        return ProductMappingCheckResponse(
            scm_order_id=scm_order_id,
            total_items=0,
            mapped_items=0,
            unmapped_items=0,
            mapping_status=[],
            can_fulfill=False
        )

    logger.info(f"🔍 检查商品映射: scm_order_id={scm_order_id}, variant_count={len(core_variant_ids)}")

    # 查询外部系统
    from app.models.external_system import ExternalSystem, ExternalSystemType
    external_system_result = await db.execute(
        select(ExternalSystem).where(
            and_(
                ExternalSystem.tenant_id == tenant.id,
                ExternalSystem.system_type == ExternalSystemType.PRINTIFY
            )
        )
    )
    external_system_obj = external_system_result.scalar_one_or_none()
    
    if not external_system_obj:
        logger.error(f"❌ 未找到 Printify 外部系统: tenant_id={tenant.id}")
        raise HTTPException(status_code=404, detail="Printify external system not found")

    # 查询商品变体信息
    variants_result = await db.execute(
        select(ProductVariant).where(
            and_(
                ProductVariant.id.in_(core_variant_ids),
                ProductVariant.tenant_id == tenant.id
            )
        )
    )
    variants = variants_result.scalars().all()
    variant_dict = {v.id: v for v in variants}

    # 查询映射关系
    mappings_result = await db.execute(
        select(ProductMapping).where(
            and_(
                ProductMapping.core_variant_id.in_(core_variant_ids),
                ProductMapping.tenant_id == tenant.id,
                ProductMapping.external_system_id == external_system_obj.id
            )
        )
    )
    mappings = mappings_result.scalars().all()
    mapping_dict = {m.core_variant_id: m for m in mappings}

    # 构建映射状态
    mapping_status = []
    mapped_items = 0
    unmapped_items = 0

    for item in line_items:
        core_variant_id = item.get("core_variant_id")
        if not core_variant_id:
            continue
            
        variant = variant_dict.get(core_variant_id)
        if not variant:
            logger.warning(f"⚠️ 商品变体不存在: core_variant_id={core_variant_id}")
            continue

        mapping = mapping_dict.get(core_variant_id)
        is_mapped = mapping is not None

        if is_mapped:
            mapped_items += 1
            # 查询外部商品信息
            external_product_result = await db.execute(
                select(ExternalProduct).where(
                    and_(
                        ExternalProduct.external_product_id == mapping.external_product_id,
                        ExternalProduct.tenant_id == tenant.id
                    )
                )
            )
            external_product = external_product_result.scalar_one_or_none()
            
            mapping_status.append(MappingStatus(
                       core_variant_id=core_variant_id,
                       core_variant_sku=variant.sku,
                       core_variant_name=variant.sku,  # 使用 SKU 作为名称
                       is_mapped=True,
                       external_sku=external_product.sku if external_product else "",
                       external_name=external_product.name if external_product else "",
                       mapping_id=mapping.id
                   ))
        else:
            unmapped_items += 1
            mapping_status.append(MappingStatus(
                core_variant_id=core_variant_id,
                core_variant_sku=variant.sku,
                core_variant_name=variant.sku,  # 使用 SKU 作为名称
                is_mapped=False
            ))

    can_fulfill = unmapped_items == 0

    logger.info(f"✅ 映射检查完成: scm_order_id={scm_order_id}, mapped={mapped_items}, unmapped={unmapped_items}, can_fulfill={can_fulfill}")

    return ProductMappingCheckResponse(
        scm_order_id=scm_order_id,
        total_items=len(core_variant_ids),
        mapped_items=mapped_items,
        unmapped_items=unmapped_items,
        mapping_status=mapping_status,
        can_fulfill=can_fulfill
    )

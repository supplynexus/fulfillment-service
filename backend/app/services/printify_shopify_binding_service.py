"""
Printify–Shopify 商品自动绑定：按 Printify raw_data.external.id 与核心商品 Shopify 映射匹配，
为「有 Shopify、无 Printify」的核心商品创建商品级映射。供 API、Celery 自动化、脚本复用。
"""

from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.external_system import ExternalSystem, ExternalSystemType
from app.models.product import Product, ProductMapping
from app.models.printify_product import PrintifyProduct


def extract_shopify_product_id_from_gid(external_product_id: Optional[str]) -> Optional[str]:
    """从 product_mappings 的 external_product_id (gid://shopify/Product/xxx) 提取数字 id"""
    if not external_product_id or not isinstance(external_product_id, str):
        return None
    s = external_product_id.strip()
    if "Product/" in s:
        s = s.split("Product/")[-1].split("?")[0].strip()
    elif s.isdigit():
        pass
    else:
        return None
    return s if s.isdigit() else None


async def auto_bind_printify_by_shopify(
    db: AsyncSession,
    tenant_id: int,
    dry_run: bool = False,
) -> dict:
    """
    按 Printify raw_data.external.id 与 Shopify 映射，为「有 Shopify、无 Printify」的核心商品创建商品级映射。
    不依赖 is_deleted 字段，可在脚本/Celery 等环境复用。

    Returns:
        dict: dry_run, candidates, created_count, skipped_already_mapped, error(optional)
    """
    # 1) 外部系统
    shopify_sys = (
        await db.execute(
            select(ExternalSystem).where(
                ExternalSystem.tenant_id == tenant_id,
                ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
            )
        )
    ).scalar_one_or_none()
    printify_sys = (
        await db.execute(
            select(ExternalSystem).where(
                ExternalSystem.tenant_id == tenant_id,
                ExternalSystem.system_type == ExternalSystemType.PRINTIFY,
            )
        )
    ).scalar_one_or_none()
    if not shopify_sys or not printify_sys:
        return {
            "dry_run": dry_run,
            "candidates": [],
            "created_count": 0,
            "skipped_already_mapped": 0,
            "error": "未找到租户的 Shopify 或 Printify 外部系统",
        }
    shopify_es_id = shopify_sys.id
    printify_es_id = printify_sys.id

    # 2) 有 Printify 映射的 core_product_id
    has_printify_subq = (
        select(ProductMapping.core_product_id).where(
            ProductMapping.tenant_id == tenant_id,
            ProductMapping.external_system_id == printify_es_id,
        ).distinct()
    )
    core_with_shopify = (
        select(ProductMapping.core_product_id, ProductMapping.external_product_id).where(
            ProductMapping.tenant_id == tenant_id,
            ProductMapping.external_system_id == shopify_es_id,
            ProductMapping.core_product_id.not_in(has_printify_subq),
        )
    )
    res = await db.execute(core_with_shopify)
    rows = res.all()
    core_to_shopify_id: dict[int, str] = {}
    for r in rows:
        if r.core_product_id not in core_to_shopify_id:
            sid = extract_shopify_product_id_from_gid(r.external_product_id)
            if sid:
                core_to_shopify_id[r.core_product_id] = sid

    if not core_to_shopify_id:
        return {"dry_run": dry_run, "candidates": [], "created_count": 0, "skipped_already_mapped": 0}

    # 3) Printify 商品
    pp_res = await db.execute(
        select(PrintifyProduct).where(
            PrintifyProduct.tenant_id == tenant_id,
            PrintifyProduct.external_system_id == printify_es_id,
        )
    )
    printify_products = pp_res.scalars().all()
    shopify_id_to_printify: dict[str, list] = {}
    for pp in printify_products:
        if not getattr(pp, "raw_data", None) or not isinstance(pp.raw_data, dict):
            continue
        ext = pp.raw_data.get("external")
        if not ext or not isinstance(ext, dict):
            continue
        sh_id = ext.get("id")
        if not sh_id:
            continue
        sh_id = str(sh_id).strip()
        shopify_id_to_printify.setdefault(sh_id, []).append(pp)

    # 4) 候选
    core_ids = list(core_to_shopify_id.keys())
    products_res = await db.execute(
        select(Product).where(Product.id.in_(core_ids), Product.tenant_id == tenant_id)
    )
    products_by_id = {p.id: p for p in products_res.scalars().all()}
    candidates: list[dict] = []
    for cid, shopify_id in core_to_shopify_id.items():
        pps = shopify_id_to_printify.get(shopify_id)
        if not pps:
            continue
        pp = pps[0]
        p_core = products_by_id.get(cid)
        core_title = (p_core.title if p_core else "") or ""
        candidates.append({
            "core_product_id": cid,
            "core_title": core_title,
            "printify_product_id": pp.printify_product_id,
            "printify_title": pp.title or "",
            "shopify_product_id": shopify_id,
        })

    if dry_run:
        return {
            "dry_run": True,
            "candidates": candidates,
            "created_count": 0,
            "skipped_already_mapped": 0,
        }

    # 5) 执行
    created = 0
    skipped = 0
    for c in candidates:
        core_product_id = c["core_product_id"]
        printify_product_id = c["printify_product_id"]
        existing = (
            await db.execute(
                select(ProductMapping).where(
                    ProductMapping.tenant_id == tenant_id,
                    ProductMapping.core_product_id == core_product_id,
                    ProductMapping.external_system_id == printify_es_id,
                )
            )
        ).scalar_one_or_none()
        if existing:
            skipped += 1
            continue
        mapping = ProductMapping(
            tenant_id=tenant_id,
            core_product_id=core_product_id,
            core_variant_id=None,
            external_system_id=printify_es_id,
            external_product_id=printify_product_id,
            external_variant_id=None,
            mapping_type="auto",
            sync_direction="bidirectional",
            sync_status="pending",
            sync_config={"auto_bind_by_printify_external_id": True},
            field_mappings={"title": "title", "sku": "sku", "price": "price"},
        )
        db.add(mapping)
        created += 1
    await db.commit()
    return {
        "dry_run": False,
        "candidates": candidates,
        "created_count": created,
        "skipped_already_mapped": skipped,
    }

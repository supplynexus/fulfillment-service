"""
Printify Product Service
管理 Printify 商品的本地数据库操作
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, and_
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any
from datetime import datetime

from app.models.printify_product import PrintifyProduct, PrintifyVariant
from app.models.external_system import ExternalSystem
from app.models.product import ExternalProduct
from app.core.logging import get_logger

logger = get_logger(__name__)


def _is_published_from_api_data(product_data: Dict[str, Any]) -> bool:
    """
    Printify 是否已发布：按实际 API 响应判断，仅看 sales_channel_properties。
    已用店铺 24981565 验证：6978c01e1868fbefd300e159 已发布（scp 为非空 dict），
    698254feac45c6e86a0b90b0 / 69825421562ab484c806a82c 未发布（scp 为空）。
    单商品/列表 API 可能返回 dict（如 {"collections": [...], "free_shipping": false}）或 list。
    - 非空（dict 有 key 或 list 有元素）= 已发布；空/None = 未发布。
    """
    scp = product_data.get("sales_channel_properties")
    if scp is None:
        return False
    if isinstance(scp, list):
        return len(scp) > 0
    if isinstance(scp, dict):
        return bool(scp)
    return False


class PrintifyProductService:
    """Printify 商品服务类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_product(self, tenant_id: int, external_system_id: int, product_data: Dict[str, Any]) -> PrintifyProduct:
        """创建 Printify 商品"""
        try:
            logger.info(" 开始创建 Printify 商品", 
                       tenant_id=tenant_id, 
                       external_system_id=external_system_id,
                       printify_product_id=product_data.get('id'))
            
            # 创建商品记录
            printify_product = PrintifyProduct(
                tenant_id=tenant_id,
                external_system_id=external_system_id,
                printify_product_id=product_data['id'],
                printify_shop_id=str(product_data.get('shop_id', '')),
                title=product_data['title'],
                description=product_data.get('description'),
                tags=product_data.get('tags', []),
                visible=_is_published_from_api_data(product_data),
                is_locked=product_data.get('is_locked', False),
                is_published=_is_published_from_api_data(product_data),
                external=product_data.get('external'),
                user_id=product_data.get('user_id'),
                print_provider_id=product_data.get('print_provider_id'),
                options=product_data.get('options', []),
                variants=product_data.get('variants', []),
                images=product_data.get('images', []),
                print_areas=product_data.get('print_areas', []),
                raw_data=product_data,
                sync_status='synced',
                last_synced_at=datetime.now()
            )
            
            self.db.add(printify_product)
            await self.db.flush()  # 获取 ID
            
            logger.info(" Printify 商品记录创建成功", 
                       product_id=printify_product.id,
                       printify_product_id=printify_product.printify_product_id)
            
            # 创建变体记录（如果失败，不影响商品创建）
            if product_data.get('variants'):
                try:
                    # 过滤变体并更新商品记录
                    valid_variants = self._filter_valid_variants(product_data['variants'])
                    printify_product.variants = valid_variants
                    
                    await self._create_variants(printify_product.id, product_data['variants'], tenant_id)
                    logger.info(" Printify 变体创建成功", 
                               product_id=printify_product.id,
                               variant_count=len(valid_variants))
                except Exception as variant_error:
                    logger.warning(" 变体创建失败，但商品已创建", 
                                  error=str(variant_error),
                                  product_id=printify_product.id)
                    # 不重新抛出异常，让商品创建成功
            
            await self._upsert_external_product(tenant_id, external_system_id, product_data)
            await self.db.commit()
            
            logger.info(" Printify 商品创建完成", 
                       product_id=printify_product.id,
                       printify_product_id=printify_product.printify_product_id)
            
            return printify_product
            
        except Exception as e:
            logger.error(" 创建 Printify 商品失败", 
                        error=str(e), 
                        tenant_id=tenant_id,
                        printify_product_id=product_data.get('id'))
            import traceback
            logger.error("   异常堆栈", stack=traceback.format_exc())
            await self.db.rollback()
            raise
    
    async def _create_variants(self, printify_product_id: int, variants_data: List[Dict[str, Any]], tenant_id: int) -> None:
        """创建商品变体"""
        try:
            # 过滤有效的变体
            valid_variants = self._filter_valid_variants(variants_data)
            
            logger.info(" 变体过滤结果", 
                       product_id=printify_product_id,
                       total_variants=len(variants_data),
                       valid_variants=len(valid_variants))
            
            for variant_data in valid_variants:
                printify_variant = PrintifyVariant(
                    tenant_id=tenant_id,
                    printify_product_id=printify_product_id,
                    printify_variant_id=variant_data['id'],
                    sku=variant_data.get('sku'),
                    title=variant_data.get('title'),
                    cost=variant_data.get('cost'),
                    price=variant_data.get('price'),
                    grams=variant_data.get('grams'),
                    is_enabled=variant_data.get('is_enabled', True),
                    is_default=variant_data.get('is_default', False),
                    is_available=variant_data.get('is_available', True),
                    options=variant_data.get('options', []),
                    raw_data=variant_data
                )
                self.db.add(printify_variant)
            
            logger.info(" Printify 变体创建成功", 
                       product_id=printify_product_id,
                       variant_count=len(valid_variants))
                       
        except Exception as e:
            logger.error(" 创建 Printify 变体失败", 
                        error=str(e), 
                        product_id=printify_product_id)
            raise
    
    def _filter_valid_variants(self, variants_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤有效的变体，只保留真正需要的变体"""
        valid_variants = []
        variant_keys = set()  # 用于去重
        
        for variant in variants_data:
            # 基本有效性检查
            if not variant.get('id'):
                continue
                
            # 检查是否启用
            if not variant.get('is_enabled', True):
                continue
                
            # 检查是否有价格（免费商品可能价格为0，但应该保留）
            if variant.get('price') is None:
                continue
                
            # 检查是否有标题或SKU
            if not variant.get('title') and not variant.get('sku'):
                continue
                
            # 检查变体选项是否有效（避免重复的变体组合）
            options = variant.get('options', [])
            if options and isinstance(options, list):
                # Printify 的选项格式是整数数组，如 [2766, 19]
                # 检查是否有有效的选项值（非空数组）
                if len(options) == 0:
                    continue
                    
                # 检查是否是重复的变体组合（基于选项值）
                # 对于整数数组，直接使用排序后的元组作为键
                variant_key = tuple(sorted(options))
                
                if variant_key in variant_keys:
                    continue
                    
                variant_keys.add(variant_key)
            else:
                # 没有选项的变体，使用 ID 作为唯一标识
                variant_key = variant.get('id')
                if variant_key in variant_keys:
                    continue
                variant_keys.add(variant_key)
            
            valid_variants.append(variant)
        
        return valid_variants
    
    async def _upsert_external_product(
        self, tenant_id: int, external_system_id: int, product_data: Dict[str, Any]
    ) -> None:
        """
        同步写入 external_products，使「外部商品映射」列表能显示已同步的 Printify 商品。
        Printify 未发布（visible=False）的商品不写入或从 external_products 移除，避免映射时出现多个同名未发布项。
        """
        try:
            # Printify: 已发布状态与 _is_published_from_api_data 一致（visible/is_visible/sales_channel_properties）
            is_published = _is_published_from_api_data(product_data)
            ext_product_id = str(product_data["id"])

            stmt = select(ExternalProduct).where(
                and_(
                    ExternalProduct.tenant_id == tenant_id,
                    ExternalProduct.external_system_id == external_system_id,
                    ExternalProduct.external_product_id == ext_product_id,
                    ExternalProduct.external_variant_id.is_(None),
                )
            )
            result = await self.db.execute(stmt)
            existing = result.scalar_one_or_none()

            if not is_published:
                # 未发布：不展示在映射列表。若曾写入过则删除，避免列表中同时出现多个同名（1 个 published + 2 个 unpublished）
                if existing:
                    await self.db.delete(existing)
                    logger.info(
                        " 从 external_products 移除未发布 Printify 商品（映射列表不再展示）",
                        external_product_id=ext_product_id,
                    )
                return
            # 已发布：正常 upsert
            variants = product_data.get("variants") or []
            first_price = float(variants[0]["price"]) if variants and variants[0].get("price") is not None else None
            now = datetime.now()
            if existing:
                existing.title = product_data.get("title") or existing.title
                existing.description = product_data.get("description")
                existing.status = "enabled"
                existing.is_active = True
                existing.is_available = True
                existing.price = first_price
                existing.variants = variants
                existing.images = product_data.get("images")
                existing.product_type = None
                existing.vendor = None
                existing.tags = product_data.get("tags")
                existing.external_data = product_data
                existing.last_synced_at = now
                existing.sync_status = "synced"
                existing.sync_error = None
                existing.updated_at = now
            else:
                ext = ExternalProduct(
                    tenant_id=tenant_id,
                    external_system_id=external_system_id,
                    external_product_id=ext_product_id,
                    external_variant_id=None,
                    title=product_data.get("title"),
                    description=product_data.get("description"),
                    status="enabled",
                    is_active=True,
                    is_available=True,
                    price=first_price,
                    variants=variants,
                    images=product_data.get("images"),
                    tags=product_data.get("tags"),
                    external_data=product_data,
                    last_synced_at=now,
                    sync_status="synced",
                )
                self.db.add(ext)
        except Exception as e:
            logger.warning(" 写入 external_products 失败（不影响 printify_products 同步）", error=str(e))

    async def get_product_by_printify_id(self, tenant_id: int, external_system_id: int, printify_product_id: str) -> Optional[PrintifyProduct]:
        """根据 Printify 商品 ID 获取商品"""
        try:
            logger.info(" 开始获取 Printify 商品", 
                       tenant_id=tenant_id,
                       external_system_id=external_system_id,
                       printify_product_id=printify_product_id)
            
            stmt = select(PrintifyProduct).where(
                and_(
                    PrintifyProduct.tenant_id == tenant_id,
                    PrintifyProduct.external_system_id == external_system_id,
                    PrintifyProduct.printify_product_id == printify_product_id
                )
            )
            
            result = await self.db.execute(stmt)
            product = result.scalar_one_or_none()
            
            if product:
                logger.info(" Printify 商品获取成功", 
                           product_id=product.id,
                           title=product.title)
            else:
                logger.info(" Printify 商品不存在", 
                           printify_product_id=printify_product_id)
            
            return product
            
        except Exception as e:
            logger.error(" 获取 Printify 商品失败", 
                        error=str(e),
                        tenant_id=tenant_id,
                        printify_product_id=printify_product_id)
            raise
    
    async def get_products_by_tenant(
        self,
        tenant_id: int,
        external_system_id: Optional[int] = None,
        limit: int = 100,
        offset: int = 0,
        published_only: Optional[bool] = None,
        printify_shop_id: Optional[str] = None,
    ) -> List[PrintifyProduct]:
        """获取租户的 Printify 商品列表。published_only: True=仅已发布, False=仅未发布, None=全部。printify_shop_id 有值时只返回该店铺商品（避免多店铺混显）。"""
        try:
            shop_id_normalized = str(printify_shop_id).strip() if printify_shop_id else None
            logger.info(" 开始获取 Printify 商品列表",
                       tenant_id=tenant_id,
                       external_system_id=external_system_id,
                       limit=limit,
                       offset=offset,
                       published_only=published_only,
                       printify_shop_id=shop_id_normalized)
            
            stmt = select(PrintifyProduct).where(PrintifyProduct.tenant_id == tenant_id)
            
            if external_system_id:
                stmt = stmt.where(PrintifyProduct.external_system_id == external_system_id)
            if published_only is not None:
                stmt = stmt.where(PrintifyProduct.is_published == published_only)
            if shop_id_normalized:
                stmt = stmt.where(PrintifyProduct.printify_shop_id == shop_id_normalized)
            
            stmt = stmt.offset(offset).limit(limit).order_by(PrintifyProduct.created_at.desc())
            
            result = await self.db.execute(stmt)
            products = result.scalars().all()
            
            logger.info(" Printify 商品列表获取成功", 
                       count=len(products),
                       tenant_id=tenant_id)
            
            return products
            
        except Exception as e:
            logger.error(" 获取 Printify 商品列表失败", 
                        error=str(e),
                        tenant_id=tenant_id)
            raise
    
    async def update_product(self, product_id: int, product_data: Dict[str, Any]) -> Optional[PrintifyProduct]:
        """更新 Printify 商品"""
        try:
            logger.info(" 开始更新 Printify 商品", 
                       product_id=product_id)
            
            # 获取现有商品
            stmt = select(PrintifyProduct).where(PrintifyProduct.id == product_id)
            result = await self.db.execute(stmt)
            product = result.scalar_one_or_none()
            
            if not product:
                logger.warning(" Printify 商品不存在", product_id=product_id)
                return None
            
            # 更新商品信息
            update_data = {
                'title': product_data.get('title', product.title),
                'description': product_data.get('description', product.description),
                'tags': product_data.get('tags', product.tags),
                'visible': _is_published_from_api_data(product_data),
                'is_locked': product_data.get('is_locked', product.is_locked),
                'is_published': _is_published_from_api_data(product_data),
                'external': product_data.get('external', product.external),
                'user_id': product_data.get('user_id', product.user_id),
                'print_provider_id': product_data.get('print_provider_id', product.print_provider_id),
                'options': product_data.get('options', product.options),
                'images': product_data.get('images', product.images),
                'print_areas': product_data.get('print_areas', product.print_areas),
                'raw_data': product_data,
                'sync_status': 'synced',
                'last_synced_at': datetime.now(),
                'updated_at': datetime.now()
            }
            
            # 处理变体数据
            if product_data.get('variants'):
                valid_variants = self._filter_valid_variants(product_data['variants'])
                update_data['variants'] = valid_variants
            else:
                update_data['variants'] = product.variants
            
            stmt = update(PrintifyProduct).where(PrintifyProduct.id == product_id).values(**update_data)
            await self.db.execute(stmt)
            
            # 更新变体
            if product_data.get('variants'):
                await self._update_variants(product_id, product_data['variants'], product.tenant_id)
            
            await self._upsert_external_product(
                product.tenant_id, product.external_system_id, product_data
            )
            await self.db.commit()
            
            logger.info(" Printify 商品更新成功", 
                       product_id=product_id,
                       title=update_data['title'])
            
            # 返回更新后的商品
            return await self.get_product_by_id(product_id)
            
        except Exception as e:
            logger.error(" 更新 Printify 商品失败", 
                        error=str(e),
                        product_id=product_id)
            await self.db.rollback()
            raise
    
    async def _update_variants(self, printify_product_id: int, variants_data: List[Dict[str, Any]], tenant_id: int) -> None:
        """更新商品变体"""
        try:
            # 过滤有效的变体
            valid_variants = self._filter_valid_variants(variants_data)
            
            # 删除现有变体
            stmt = delete(PrintifyVariant).where(PrintifyVariant.printify_product_id == printify_product_id)
            await self.db.execute(stmt)
            
            # 创建新变体
            await self._create_variants(printify_product_id, valid_variants, tenant_id)
            
            logger.info(" Printify 变体更新成功", 
                       product_id=printify_product_id,
                       total_variants=len(variants_data),
                       valid_variants=len(valid_variants))
                       
        except Exception as e:
            logger.error(" 更新 Printify 变体失败", 
                        error=str(e), 
                        product_id=printify_product_id)
            raise
    
    async def get_product_by_id(self, product_id: int) -> Optional[PrintifyProduct]:
        """根据 ID 获取商品"""
        try:
            stmt = select(PrintifyProduct).where(PrintifyProduct.id == product_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(" 获取 Printify 商品失败", 
                        error=str(e),
                        product_id=product_id)
            raise
    
    async def delete_product(self, product_id: int) -> bool:
        """删除 Printify 商品"""
        try:
            logger.info(" 开始删除 Printify 商品", product_id=product_id)
            
            # 删除变体
            stmt = delete(PrintifyVariant).where(PrintifyVariant.printify_product_id == product_id)
            await self.db.execute(stmt)
            
            # 删除商品
            stmt = delete(PrintifyProduct).where(PrintifyProduct.id == product_id)
            result = await self.db.execute(stmt)
            
            await self.db.commit()
            
            if result.rowcount > 0:
                logger.info(" Printify 商品删除成功", product_id=product_id)
                return True
            else:
                logger.warning(" Printify 商品不存在", product_id=product_id)
                return False
                
        except Exception as e:
            logger.error(" 删除 Printify 商品失败", 
                        error=str(e),
                        product_id=product_id)
            await self.db.rollback()
            raise
    
    async def sync_products_from_api(self, tenant_id: int, external_system_id: int, api_products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """从 API 同步商品到本地数据库"""
        try:
            logger.info("开始同步 Printify 商品", 
                       tenant_id=tenant_id,
                       external_system_id=external_system_id,
                       api_product_count=len(api_products))
            
            synced_count = 0
            updated_count = 0
            created_count = 0
            error_count = 0
            
            for product_data in api_products:
                try:
                    # 检查商品是否已存在
                    existing_product = await self.get_product_by_printify_id(
                        tenant_id, external_system_id, product_data['id']
                    )
                    
                    if existing_product:
                        # 更新现有商品
                        await self.update_product(existing_product.id, product_data)
                        updated_count += 1
                    else:
                        # 创建新商品
                        await self.create_product(tenant_id, external_system_id, product_data)
                        created_count += 1
                    
                    synced_count += 1
                    
                except Exception as e:
                    logger.error("同步单个商品失败", 
                                error=str(e),
                                printify_product_id=product_data.get('id'))
                    error_count += 1
            
            result = {
                'total': len(api_products),
                'synced': synced_count,
                'created': created_count,
                'updated': updated_count,
                'errors': error_count
            }
            
            logger.info("Printify 商品同步完成", **result)
            return result
            
        except Exception as e:
            logger.error("同步 Printify 商品失败", 
                        error=str(e),
                        tenant_id=tenant_id)
            raise

    async def clear_products_by_external_system(
        self, tenant_id: int, external_system_id: int
    ) -> Dict[str, Any]:
        """
        清空该外部系统下所有 Printify 本地数据（便于先删后重新同步）。
        删除：printify_variants、printify_products、该 external_system 的 external_products。
        """
        try:
            # 1. 删除该租户+外部系统下所有 Printify 商品的变体
            stmt = select(PrintifyProduct.id).where(
                and_(
                    PrintifyProduct.tenant_id == tenant_id,
                    PrintifyProduct.external_system_id == external_system_id,
                )
            )
            result = await self.db.execute(stmt)
            product_ids = [row[0] for row in result.all()]
            if product_ids:
                await self.db.execute(
                    delete(PrintifyVariant).where(
                        PrintifyVariant.printify_product_id.in_(product_ids)
                    )
                )
            # 2. 删除 Printify 商品
            stmt = delete(PrintifyProduct).where(
                and_(
                    PrintifyProduct.tenant_id == tenant_id,
                    PrintifyProduct.external_system_id == external_system_id,
                )
            )
            pp_result = await self.db.execute(stmt)
            deleted_products = pp_result.rowcount
            # 3. 删除该外部系统对应的 external_products（同步时会重新写入）
            stmt = delete(ExternalProduct).where(
                and_(
                    ExternalProduct.tenant_id == tenant_id,
                    ExternalProduct.external_system_id == external_system_id,
                )
            )
            ep_result = await self.db.execute(stmt)
            deleted_external = ep_result.rowcount
            await self.db.commit()
            logger.info(
                "清空 Printify 数据完成",
                tenant_id=tenant_id,
                external_system_id=external_system_id,
                deleted_products=deleted_products,
                deleted_external_products=deleted_external,
            )
            return {
                "deleted_printify_products": deleted_products,
                "deleted_external_products": deleted_external,
            }
        except Exception as e:
            await self.db.rollback()
            logger.error(
                "清空 Printify 数据失败",
                error=str(e),
                tenant_id=tenant_id,
                external_system_id=external_system_id,
            )
            raise

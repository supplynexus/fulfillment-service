"""
Shopify 商品同步服务
用于从 Shopify 获取商品并同步到本地数据库
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.product import Product
from app.models.external_system import ExternalSystem, ExternalSystemType
from app.schemas.product import ProductCreate
from app.core.security import decrypt_data
from app.services.shopify.client import ShopifyGraphQLClient

logger = logging.getLogger(__name__)


class ShopifyProductService:
    """Shopify 商品同步服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_shopify_credentials(self, tenant_id: int) -> Optional[Dict[str, str]]:
        """从数据库获取 Shopify 凭据"""
        try:
            # 查找 Shopify 外部系统
            result = await self.db.execute(
                select(ExternalSystem).where(
                    ExternalSystem.tenant_id == tenant_id,
                    ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                    ExternalSystem.is_active == True
                )
            )
            external_system = result.scalar_one_or_none()
            
            if not external_system:
                logger.warning(f"未找到活跃的 Shopify 外部系统 (tenant_id: {tenant_id})")
                return None
            
            # 处理凭据 - 支持加密和未加密两种格式
            credentials = {}
            for key, value in external_system.credentials.items():
                try:
                    # 尝试解密（如果是加密的）
                    credentials[key] = decrypt_data(value)
                except Exception:
                    # 如果解密失败，假设是未加密的
                    credentials[key] = value
            
            return credentials
            
        except Exception as e:
            logger.error(f"获取 Shopify 凭据失败: {e}")
            return None
    
    def _convert_shopify_product_to_schema(self, product_data: Dict[str, Any]) -> ProductCreate:
        """将 Shopify 商品数据转换为 ProductCreate schema"""
        
        # 提取基本信息
        shopify_product_id = str(product_data.get('id', ''))
        title = product_data.get('title', '')
        description = product_data.get('description', '')
        
        # 提取标签
        tags = []
        for tag in product_data.get('tags', []):
            tags.append(tag)
        
        # 提取图片
        images = []
        for image in product_data.get('images', {}).get('edges', []):
            node = image.get('node', {})
            images.append({
                'id': node.get('id'),
                'url': node.get('url'),
                'alt_text': node.get('altText')
            })
        
        # 提取变体
        variants = []
        for variant in product_data.get('variants', {}).get('edges', []):
            node = variant.get('node', {})
            variants.append({
                'id': node.get('id'),
                'title': node.get('title'),
                'sku': node.get('sku'),
                'price': node.get('price'),
                'compare_at_price': node.get('compareAtPrice'),
                'inventory_quantity': node.get('inventoryQuantity'),
                'weight': node.get('weight'),
                'weight_unit': node.get('weightUnit')
            })
        
        # 提取价格信息
        price = None
        compare_at_price = None
        if variants:
            # 使用第一个变体的价格作为主价格
            first_variant = variants[0]
            price = float(first_variant.get('price', 0)) if first_variant.get('price') else None
            compare_at_price = float(first_variant.get('compare_at_price', 0)) if first_variant.get('compare_at_price') else None
        
        # 提取状态信息
        is_active = product_data.get('status', 'ACTIVE') == 'ACTIVE'
        is_available = product_data.get('availableForSale', True)
        
        # 提取时间信息
        created_at = product_data.get('createdAt')
        if created_at:
            created_date = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        else:
            created_date = datetime.utcnow()
        
        return ProductCreate(
            external_product_id=shopify_product_id,
            title=title,
            description=description,
            tags=tags,
            images=images,
            variants=variants,
            price=price,
            compare_at_price=compare_at_price,
            is_active=is_active,
            is_available=is_available,
            external_data=product_data  # 保存原始数据
        )
    
    async def _get_smart_sync_timestamp(self, tenant_id: int, buffer_minutes: int = 5) -> datetime:
        """
        获取智能同步时间戳，防止漏单
        
        策略：
        1. 优先使用外部系统的 last_product_sync_at
        2. 如果没有，使用数据库中该租户最新商品的 updated_at
        3. 如果都没有，使用当前时间减去 buffer_minutes
        4. 为了防漏单，将时间戳往前推 buffer_minutes 分钟
        """
        try:
            # 1. 获取外部系统的最后商品同步时间
            result = await self.db.execute(
                select(ExternalSystem.last_product_sync_at)
                .where(
                    ExternalSystem.tenant_id == tenant_id,
                    ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                    ExternalSystem.is_active == True
                )
            )
            external_sync_time = result.scalar_one_or_none()
            
            if external_sync_time:
                # 往前推 buffer_minutes 分钟，防止漏单
                sync_time = external_sync_time - timedelta(minutes=buffer_minutes)
                logger.info(f"使用外部系统商品同步时间: {external_sync_time} -> {sync_time}")
                return sync_time
            
            # 2. 获取数据库中该租户最新商品的更新时间
            result = await self.db.execute(
                select(Product.updated_at)
                .where(Product.tenant_id == tenant_id)
                .order_by(Product.updated_at.desc())
                .limit(1)
            )
            latest_product_time = result.scalar_one_or_none()
            
            if latest_product_time:
                # 往前推 buffer_minutes 分钟，防止漏单
                sync_time = latest_product_time - timedelta(minutes=buffer_minutes)
                logger.info(f"使用最新商品时间: {latest_product_time} -> {sync_time}")
                return sync_time
            
            # 3. 默认使用当前时间减去 buffer_minutes
            sync_time = datetime.utcnow() - timedelta(minutes=buffer_minutes)
            logger.info(f"使用默认时间: {sync_time}")
            return sync_time
            
        except Exception as e:
            logger.error(f"获取智能同步时间戳失败: {e}")
            # 出错时使用保守的时间
            return datetime.utcnow() - timedelta(hours=1)
    
    async def sync_products(
        self,
        tenant_id: int,
        query_filter: Optional[str] = None,
        max_products: Optional[int] = None,
        sync_recent_only: bool = True
    ) -> Dict[str, Any]:
        """同步 Shopify 商品到本地数据库"""
        
        try:
            # 获取 Shopify 凭据
            credentials = await self.get_shopify_credentials(tenant_id)
            if not credentials:
                return {
                    'success': False,
                    'error': '无法获取 Shopify 凭据',
                    'products_fetched': 0,
                    'products_saved': 0,
                    'products_updated': 0,
                    'errors': []
                }
            
            access_token = credentials.get('access_token')
            store_url = credentials.get('store_url', '')
            
            # 从 store_url 中提取 shop_name
            if store_url.startswith('https://'):
                shop_name = store_url.replace('https://', '').replace('.myshopify.com', '')
            else:
                shop_name = store_url.replace('.myshopify.com', '')
            
            if not access_token or not shop_name:
                return {
                    'success': False,
                    'error': '缺少必要的 Shopify 配置',
                    'products_fetched': 0,
                    'products_saved': 0,
                    'products_updated': 0,
                    'errors': []
                }
            
            # 创建 Shopify 客户端
            client = ShopifyGraphQLClient(shop_name, access_token)
            
            # 设置查询过滤条件
            if sync_recent_only:
                # 使用智能时间戳，防止漏单
                since_time = await self._get_smart_sync_timestamp(tenant_id, buffer_minutes=5)
                # 使用带时区的精确时间格式
                time_filter = f"updated_at:>={since_time.isoformat()}"
                if query_filter:
                    query_filter = f"{query_filter} AND {time_filter}"
                else:
                    query_filter = time_filter
                
                logger.info(f"智能同步时间戳: {since_time.isoformat()}")
            
            logger.info(f"开始同步 Shopify 商品 (tenant_id: {tenant_id}, filter: {query_filter})")
            
            products_fetched = 0
            products_saved = 0
            products_updated = 0
            errors = []
            
            # 获取商品
            async for product_data in client.get_all_products(
                query_filter=query_filter,
                max_products=max_products
            ):
                products_fetched += 1
                
                try:
                    # 转换为 schema
                    product_create = self._convert_shopify_product_to_schema(product_data)
                    
                    # 检查商品是否已存在
                    existing_product = await self.db.execute(
                        select(Product).where(
                            Product.external_product_id == product_create.external_product_id,
                            Product.tenant_id == tenant_id
                        )
                    )
                    existing_product = existing_product.scalar_one_or_none()
                    
                    # 新 Product 模型只包含以下字段，排除不存在的字段
                    # (tags, variants 现在是关系; price, compare_at_price 不存在)
                    excluded_fields = {'external_data', 'tags', 'variants', 'price', 'compare_at_price'}
                    
                    if existing_product:
                        # 更新现有商品
                        for field, value in product_create.dict(exclude_unset=True, exclude=excluded_fields).items():
                            if hasattr(existing_product, field):
                                setattr(existing_product, field, value)
                        existing_product.updated_at = datetime.utcnow()
                        products_updated += 1
                        logger.debug(f"更新商品: {product_create.external_product_id}")
                    else:
                        # 创建新商品 - 只传递 Product 模型支持的字段
                        product_data_dict = product_create.dict(exclude=excluded_fields)
                        new_product = Product(
                            tenant_id=tenant_id,
                            **product_data_dict
                        )
                        self.db.add(new_product)
                        products_saved += 1
                        logger.debug(f"创建新商品: {product_create.external_product_id}")
                    
                    # 提交事务
                    await self.db.commit()
                    
                except Exception as e:
                    await self.db.rollback()
                    error_msg = f"处理商品 {product_data.get('id')} 时出错: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)
            
            # 更新外部系统的最后商品同步时间
            await self._update_product_sync_timestamp(tenant_id)
            
            result = {
                'success': True,
                'products_fetched': products_fetched,
                'products_saved': products_saved,
                'products_updated': products_updated,
                'errors': errors
            }
            
            logger.info(f"商品同步完成: {result}")
            return result
            
        except Exception as e:
            logger.error(f"商品同步失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'products_fetched': 0,
                'products_saved': 0,
                'products_updated': 0,
                'errors': [str(e)]
            }
    
    async def _update_product_sync_timestamp(self, tenant_id: int):
        """更新外部系统的最后商品同步时间"""
        try:
            await self.db.execute(
                update(ExternalSystem)
                .where(
                    ExternalSystem.tenant_id == tenant_id,
                    ExternalSystem.system_type == ExternalSystemType.SHOPIFY,
                    ExternalSystem.is_active == True
                )
                .values(last_product_sync_at=datetime.now(timezone.utc))
            )
            await self.db.commit()
        except Exception as e:
            logger.error(f"更新商品同步时间戳失败: {e}")
    
    async def get_recent_products(
        self,
        tenant_id: int,
        hours: int = 24,
        limit: int = 100
    ) -> List[Product]:
        """获取最近的商品"""
        try:
            since_time = datetime.utcnow() - timedelta(hours=hours)
            
            result = await self.db.execute(
                select(Product)
                .where(
                    Product.tenant_id == tenant_id,
                    Product.updated_at >= since_time
                )
                .order_by(Product.updated_at.desc())
                .limit(limit)
            )
            
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"获取最近商品失败: {e}")
            return []
    
    async def get_products_by_status(
        self,
        tenant_id: int,
        is_active: Optional[bool] = None,
        is_available: Optional[bool] = None,
        limit: int = 100
    ) -> List[Product]:
        """按状态获取商品"""
        try:
            query = select(Product).where(Product.tenant_id == tenant_id)
            
            if is_active is not None:
                query = query.where(Product.is_active == is_active)
            
            if is_available is not None:
                query = query.where(Product.is_available == is_available)
            
            query = query.order_by(Product.updated_at.desc()).limit(limit)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"按状态获取商品失败: {e}")
            return []

"""
ProductVariantService - SKU 管理服务

实现功能：
1. SKU 的 CRUD 操作
2. 批量创建 SKU（笛卡尔积生成）
3. SKU 维度值管理
4. SKU 属性管理
5. SKU 搜索和筛选
6. SKU 状态管理
"""

from typing import List, Optional, Dict, Set, Tuple, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload
from itertools import product as cartesian_product
import logging

from app.models.product import Product, ProductVariant
from app.models.product_dimension import (
    ProductDimensionTemplate,
    ProductDimensionValue,
    ProductVariantDimension
)
from app.models.product_attribute import ProductVariantAttribute
from app.models.product_category import ProductCategoryDimension
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProductVariantService:
    """SKU 管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_variant(
        self,
        product_id: int,
        sku: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        price: Optional[float] = None,
        cost_price: Optional[float] = None,
        weight: Optional[float] = None,
        dimensions: Optional[Dict[str, Any]] = None,
        attributes: Optional[Dict[str, Any]] = None,
        is_active: bool = True
    ) -> ProductVariant:
        """
        创建单个 SKU
        
        Args:
            product_id: 产品ID
            sku: SKU编码
            name: SKU名称
            description: 描述
            price: 售价
            cost_price: 成本价
            weight: 重量
            dimensions: 维度值字典 {dimension_code: value_id}
            attributes: 属性字典 {attribute_key: attribute_value}
            is_active: 是否激活
            
        Returns:
            ProductVariant: 创建的SKU
        """
        logger.info("🔍 开始创建SKU", 
                   product_id=product_id,
                   sku=sku)
        
        # 检查SKU是否重复
        existing = await self.get_variant_by_sku(product_id, sku)
        if existing:
            raise ValueError(f"SKU '{sku}' 已存在")
        
        # 创建SKU
        variant = ProductVariant(
            product_id=product_id,
            sku=sku,
            name=name,
            description=description,
            price=price,
            cost_price=cost_price,
            weight=weight,
            is_active=is_active
        )
        
        self.db.add(variant)
        await self.db.flush()  # 获取ID
        
        # 添加维度值
        if dimensions:
            await self._add_variant_dimensions(variant.id, dimensions)
        
        # 添加属性
        if attributes:
            await self._add_variant_attributes(variant.id, attributes)
        
        await self.db.commit()
        
        logger.info("✅ SKU创建成功", 
                   variant_id=variant.id,
                   sku=sku)
        
        return variant
    
    async def get_variant_by_sku(
        self, 
        product_id: int, 
        sku: str
    ) -> Optional[ProductVariant]:
        """根据SKU编码获取SKU"""
        result = await self.db.execute(
            select(ProductVariant)
            .where(
                and_(
                    ProductVariant.product_id == product_id,
                    ProductVariant.sku == sku
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_variant_by_id(
        self, 
        variant_id: int
    ) -> Optional[ProductVariant]:
        """根据ID获取SKU"""
        result = await self.db.execute(
            select(ProductVariant)
            .where(ProductVariant.id == variant_id)
            .options(
                selectinload(ProductVariant.product),
                selectinload(ProductVariant.variant_dimensions),
                selectinload(ProductVariant.variant_attributes)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_product_variants(
        self, 
        product_id: int,
        include_inactive: bool = False
    ) -> List[ProductVariant]:
        """获取产品的所有SKU"""
        query = select(ProductVariant).where(ProductVariant.product_id == product_id)
        
        if not include_inactive:
            query = query.where(ProductVariant.is_active == True)
        
        query = query.order_by(ProductVariant.sku)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def generate_cartesian_product_variants(
        self,
        product_id: int,
        dimension_combinations: Dict[str, List[int]],
        base_sku_prefix: str = "",
        base_name_prefix: str = "",
        base_price: Optional[float] = None,
        base_cost_price: Optional[float] = None,
        base_weight: Optional[float] = None,
        additional_attributes: Optional[Dict[str, Any]] = None
    ) -> List[ProductVariant]:
        """
        使用笛卡尔积生成多个SKU
        
        Args:
            product_id: 产品ID
            dimension_combinations: 维度组合 {dimension_code: [value_id1, value_id2, ...]}
            base_sku_prefix: SKU前缀
            base_name_prefix: 名称前缀
            base_price: 基础价格
            base_cost_price: 基础成本价
            base_weight: 基础重量
            additional_attributes: 额外属性
            
        Returns:
            List[ProductVariant]: 创建的SKU列表
        """
        logger.info("🔍 开始生成笛卡尔积SKU", 
                   product_id=product_id,
                   dimension_count=len(dimension_combinations))
        
        # 获取维度模板信息
        dimension_templates = await self._get_dimension_templates_by_codes(
            list(dimension_combinations.keys())
        )
        
        # 获取维度值信息
        dimension_values = await self._get_dimension_values_by_ids(
            [vid for vids in dimension_combinations.values() for vid in vids]
        )
        
        # 生成笛卡尔积组合
        dimension_codes = list(dimension_combinations.keys())
        dimension_value_lists = [dimension_combinations[code] for code in dimension_codes]
        
        combinations = list(cartesian_product(*dimension_value_lists))
        
        logger.info("🔍 笛卡尔积组合生成", 
                   total_combinations=len(combinations))
        
        created_variants = []
        
        for i, combination in enumerate(combinations):
            # 构建SKU名称和编码
            sku_parts = []
            name_parts = []
            dimension_values_dict = {}
            
            for j, value_id in enumerate(combination):
                dimension_code = dimension_codes[j]
                value_info = dimension_values.get(value_id)
                
                if value_info:
                    sku_parts.append(value_info['value_code'])
                    name_parts.append(value_info['value_name'])
                    dimension_values_dict[dimension_code] = value_id
            
            # 生成SKU编码和名称
            sku_suffix = "-".join(sku_parts)
            name_suffix = " ".join(name_parts)
            
            sku = f"{base_sku_prefix}-{sku_suffix}" if base_sku_prefix else sku_suffix
            name = f"{base_name_prefix} {name_suffix}".strip() if base_name_prefix else name_suffix
            
            # 创建SKU
            variant = ProductVariant(
                product_id=product_id,
                sku=sku,
                name=name,
                price=base_price,
                cost_price=base_cost_price,
                weight=base_weight,
                is_active=True
            )
            
            self.db.add(variant)
            await self.db.flush()  # 获取ID
            
            # 添加维度值
            await self._add_variant_dimensions(variant.id, dimension_values_dict)
            
            # 添加额外属性
            if additional_attributes:
                await self._add_variant_attributes(variant.id, additional_attributes)
            
            created_variants.append(variant)
        
        await self.db.commit()
        
        logger.info("✅ 笛卡尔积SKU生成成功", 
                   created_count=len(created_variants))
        
        return created_variants
    
    async def preview_cartesian_product(
        self,
        dimension_combinations: Dict[str, List[int]]
    ) -> List[Dict[str, Any]]:
        """
        预览笛卡尔积组合（不创建SKU）
        
        Args:
            dimension_combinations: 维度组合
            
        Returns:
            List[Dict]: 预览结果
        """
        logger.info("🔍 开始预览笛卡尔积组合")
        
        # 获取维度值信息
        dimension_values = await self._get_dimension_values_by_ids(
            [vid for vids in dimension_combinations.values() for vid in vids]
        )
        
        # 生成笛卡尔积组合
        dimension_codes = list(dimension_combinations.keys())
        dimension_value_lists = [dimension_combinations[code] for code in dimension_codes]
        
        combinations = list(cartesian_product(*dimension_value_lists))
        
        preview_results = []
        
        for combination in combinations:
            sku_parts = []
            name_parts = []
            dimension_info = {}
            
            for j, value_id in enumerate(combination):
                dimension_code = dimension_codes[j]
                value_info = dimension_values.get(value_id)
                
                if value_info:
                    sku_parts.append(value_info['value_code'])
                    name_parts.append(value_info['value_name'])
                    dimension_info[dimension_code] = {
                        'value_id': value_id,
                        'value_code': value_info['value_code'],
                        'value_name': value_info['value_name']
                    }
            
            preview_results.append({
                'sku_suffix': "-".join(sku_parts),
                'name_suffix': " ".join(name_parts),
                'dimensions': dimension_info
            })
        
        logger.info("✅ 笛卡尔积预览完成", 
                   total_combinations=len(preview_results))
        
        return preview_results
    
    async def update_variant(
        self,
        variant_id: int,
        **update_data
    ) -> Optional[ProductVariant]:
        """更新SKU信息"""
        logger.info("🔍 开始更新SKU", variant_id=variant_id)
        
        variant = await self.get_variant_by_id(variant_id)
        if not variant:
            return None
        
        # 更新字段
        for key, value in update_data.items():
            if hasattr(variant, key):
                setattr(variant, key, value)
        
        await self.db.commit()
        
        logger.info("✅ SKU更新成功", variant_id=variant_id)
        
        return variant
    
    async def delete_variant(
        self,
        variant_id: int
    ) -> bool:
        """删除SKU"""
        logger.info("🔍 开始删除SKU", variant_id=variant_id)
        
        variant = await self.get_variant_by_id(variant_id)
        if not variant:
            return False
        
        # 删除SKU（级联删除相关数据）
        await self.db.delete(variant)
        await self.db.commit()
        
        logger.info("✅ SKU删除成功", variant_id=variant_id)
        
        return True
    
    async def search_variants(
        self,
        tenant_id: int,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "sku",
        sort_order: str = "asc",
        limit: int = 100,
        offset: int = 0
    ) -> Tuple[List[ProductVariant], int]:
        """
        搜索SKU
        
        Args:
            tenant_id: 租户ID
            filters: 筛选条件
            sort_by: 排序字段
            sort_order: 排序方向
            limit: 限制数量
            offset: 偏移量
            
        Returns:
            Tuple[List[ProductVariant], int]: SKU列表和总数
        """
        logger.info("🔍 开始搜索SKU", 
                   tenant_id=tenant_id,
                   filters=filters)
        
        # 构建基础查询
        query = select(ProductVariant).join(Product).where(Product.tenant_id == tenant_id)
        
        # 应用筛选条件
        if filters:
            if 'sku' in filters:
                query = query.where(ProductVariant.sku.ilike(f"%{filters['sku']}%"))
            
            if 'name' in filters:
                query = query.where(ProductVariant.name.ilike(f"%{filters['name']}%"))
            
            if 'is_active' in filters:
                query = query.where(ProductVariant.is_active == filters['is_active'])
            
            if 'product_id' in filters:
                query = query.where(ProductVariant.product_id == filters['product_id'])
            
            if 'price_min' in filters:
                query = query.where(ProductVariant.price >= filters['price_min'])
            
            if 'price_max' in filters:
                query = query.where(ProductVariant.price <= filters['price_max'])
        
        # 获取总数
        count_query = select(func.count(ProductVariant.id)).select_from(
            query.subquery()
        )
        count_result = await self.db.execute(count_query)
        total = count_result.scalar()
        
        # 排序
        if sort_by == "sku":
            sort_column = ProductVariant.sku
        elif sort_by == "name":
            sort_column = ProductVariant.name
        elif sort_by == "price":
            sort_column = ProductVariant.price
        elif sort_by == "created_at":
            sort_column = ProductVariant.created_at
        else:
            sort_column = ProductVariant.sku
        
        if sort_order == "desc":
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # 分页
        query = query.limit(limit).offset(offset)
        
        # 执行查询
        result = await self.db.execute(query)
        variants = result.scalars().all()
        
        logger.info("✅ SKU搜索完成", 
                   found_count=len(variants),
                   total=total)
        
        return variants, total
    
    async def _add_variant_dimensions(
        self,
        variant_id: int,
        dimensions: Dict[str, Any]
    ) -> None:
        """为SKU添加维度值"""
        for dimension_code, value_id in dimensions.items():
            # 获取维度模板ID
            template_result = await self.db.execute(
                select(ProductDimensionTemplate.id)
                .where(ProductDimensionTemplate.dimension_code == dimension_code)
            )
            template_id = template_result.scalar_one_or_none()
            
            if template_id:
                variant_dimension = ProductVariantDimension(
                    variant_id=variant_id,
                    dimension_template_id=template_id,
                    dimension_value_id=value_id
                )
                self.db.add(variant_dimension)
    
    async def _add_variant_attributes(
        self,
        variant_id: int,
        attributes: Dict[str, Any]
    ) -> None:
        """为SKU添加属性"""
        for attribute_key, attribute_value in attributes.items():
            attribute = ProductVariantAttribute(
                variant_id=variant_id,
                attribute_key=attribute_key,
                attribute_value=str(attribute_value),
                attribute_type='string'
            )
            self.db.add(attribute)
    
    async def _get_dimension_templates_by_codes(
        self,
        dimension_codes: List[str]
    ) -> Dict[str, Any]:
        """根据编码获取维度模板"""
        result = await self.db.execute(
            select(ProductDimensionTemplate)
            .where(ProductDimensionTemplate.dimension_code.in_(dimension_codes))
        )
        templates = result.scalars().all()
        
        return {template.dimension_code: template for template in templates}
    
    async def _get_dimension_values_by_ids(
        self,
        value_ids: List[int]
    ) -> Dict[int, Dict[str, Any]]:
        """根据ID获取维度值"""
        result = await self.db.execute(
            select(ProductDimensionValue)
            .where(ProductDimensionValue.id.in_(value_ids))
        )
        values = result.scalars().all()
        
        return {
            value.id: {
                'value_code': value.value_code,
                'value_name': value.value_name,
                'value_type': value.value_type
            }
            for value in values
        }
    
    async def get_variant_statistics(
        self,
        tenant_id: int
    ) -> Dict[str, Any]:
        """获取SKU统计信息"""
        logger.info("🔍 开始获取SKU统计信息", tenant_id=tenant_id)
        
        # 基础统计
        total_variants = await self.db.execute(
            select(func.count(ProductVariant.id))
            .join(Product)
            .where(Product.tenant_id == tenant_id)
        )
        
        active_variants = await self.db.execute(
            select(func.count(ProductVariant.id))
            .join(Product)
            .where(
                and_(
                    Product.tenant_id == tenant_id,
                    ProductVariant.is_active == True
                )
            )
        )
        
        # 按产品统计
        variants_by_product = await self.db.execute(
            select(
                Product.id,
                Product.name,
                func.count(ProductVariant.id).label('variant_count')
            )
            .join(ProductVariant, Product.id == ProductVariant.product_id)
            .where(Product.tenant_id == tenant_id)
            .group_by(Product.id, Product.name)
        )
        
        stats = {
            "total_variants": total_variants.scalar(),
            "active_variants": active_variants.scalar(),
            "inactive_variants": total_variants.scalar() - active_variants.scalar(),
            "variants_by_product": [
                {
                    "product_id": row.id,
                    "product_name": row.name,
                    "variant_count": row.variant_count
                }
                for row in variants_by_product
            ]
        }
        
        logger.info("✅ SKU统计信息获取成功")
        
        return stats

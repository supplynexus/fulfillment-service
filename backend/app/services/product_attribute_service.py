"""
ProductAttributeService - 产品属性管理服务

实现功能：
1. 产品属性的 CRUD 操作
2. SKU 属性的 CRUD 操作
3. 属性继承和合并逻辑
4. 属性类型管理
5. 属性验证规则
6. 属性搜索和筛选
"""

from typing import List, Optional, Dict, Set, Tuple, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload
import json
import logging

from app.models.product_attribute import (
    ProductAttribute,
    ProductVariantAttribute
)
from app.models.product import Product, ProductVariant
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProductAttributeService:
    """产品属性管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_product_attribute(
        self,
        product_id: int,
        attribute_key: str,
        attribute_value: str,
        attribute_type: str = 'string',
        display_name: Optional[str] = None,
        sort_order: int = 0
    ) -> ProductAttribute:
        """
        创建产品属性
        
        Args:
            product_id: 产品ID
            attribute_key: 属性键（如：brand, material）
            attribute_value: 属性值
            attribute_type: 属性类型（string, number, boolean, json）
            display_name: 显示名称
            sort_order: 排序
            
        Returns:
            ProductAttribute: 创建的产品属性
        """
        logger.info("🔍 开始创建产品属性", 
                   product_id=product_id,
                   attribute_key=attribute_key,
                   attribute_type=attribute_type)
        
        # 检查属性键是否重复
        existing = await self.get_product_attribute_by_key(product_id, attribute_key)
        if existing:
            raise ValueError(f"产品属性键 '{attribute_key}' 已存在")
        
        # 验证属性值类型
        validated_value = self._validate_attribute_value(attribute_value, attribute_type)
        
        # 创建产品属性
        attribute = ProductAttribute(
            product_id=product_id,
            attribute_key=attribute_key,
            attribute_value=validated_value,
            attribute_type=attribute_type,
            display_name=display_name or attribute_key,
            sort_order=sort_order
        )
        
        self.db.add(attribute)
        await self.db.commit()
        
        logger.info("✅ 产品属性创建成功", 
                   attribute_id=attribute.id,
                   attribute_key=attribute_key)
        
        return attribute
    
    async def get_product_attribute_by_key(
        self, 
        product_id: int, 
        attribute_key: str
    ) -> Optional[ProductAttribute]:
        """根据键获取产品属性"""
        result = await self.db.execute(
            select(ProductAttribute)
            .where(
                and_(
                    ProductAttribute.product_id == product_id,
                    ProductAttribute.attribute_key == attribute_key
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_product_attributes(
        self, 
        product_id: int
    ) -> List[ProductAttribute]:
        """获取产品的所有属性"""
        result = await self.db.execute(
            select(ProductAttribute)
            .where(ProductAttribute.product_id == product_id)
            .order_by(ProductAttribute.sort_order, ProductAttribute.id)
        )
        return result.scalars().all()
    
    async def create_variant_attribute(
        self,
        variant_id: int,
        attribute_key: str,
        attribute_value: str,
        attribute_type: str = 'string',
        display_name: Optional[str] = None,
        migrated_from_dimension: bool = False,
        sort_order: int = 0
    ) -> ProductVariantAttribute:
        """
        创建SKU属性
        
        Args:
            variant_id: SKU ID
            attribute_key: 属性键
            attribute_value: 属性值
            attribute_type: 属性类型
            display_name: 显示名称
            migrated_from_dimension: 是否从维度迁移而来
            sort_order: 排序
            
        Returns:
            ProductVariantAttribute: 创建的SKU属性
        """
        logger.info("🔍 开始创建SKU属性", 
                   variant_id=variant_id,
                   attribute_key=attribute_key,
                   attribute_type=attribute_type)
        
        # 检查属性键是否重复
        existing = await self.get_variant_attribute_by_key(variant_id, attribute_key)
        if existing:
            raise ValueError(f"SKU属性键 '{attribute_key}' 已存在")
        
        # 验证属性值类型
        validated_value = self._validate_attribute_value(attribute_value, attribute_type)
        
        # 创建SKU属性
        attribute = ProductVariantAttribute(
            variant_id=variant_id,
            attribute_key=attribute_key,
            attribute_value=validated_value,
            attribute_type=attribute_type,
            display_name=display_name or attribute_key,
            migrated_from_dimension=migrated_from_dimension,
            sort_order=sort_order
        )
        
        self.db.add(attribute)
        await self.db.commit()
        
        logger.info("✅ SKU属性创建成功", 
                   attribute_id=attribute.id,
                   attribute_key=attribute_key)
        
        return attribute
    
    async def get_variant_attribute_by_key(
        self, 
        variant_id: int, 
        attribute_key: str
    ) -> Optional[ProductVariantAttribute]:
        """根据键获取SKU属性"""
        result = await self.db.execute(
            select(ProductVariantAttribute)
            .where(
                and_(
                    ProductVariantAttribute.variant_id == variant_id,
                    ProductVariantAttribute.attribute_key == attribute_key
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_variant_attributes(
        self, 
        variant_id: int
    ) -> List[ProductVariantAttribute]:
        """获取SKU的所有属性"""
        result = await self.db.execute(
            select(ProductVariantAttribute)
            .where(ProductVariantAttribute.variant_id == variant_id)
            .order_by(ProductVariantAttribute.sort_order, ProductVariantAttribute.id)
        )
        return result.scalars().all()
    
    async def get_merged_attributes_for_variant(
        self, 
        variant_id: int
    ) -> Dict[str, Any]:
        """
        获取SKU的合并属性（产品属性 + SKU属性）
        
        合并优先级：SKU属性 > 产品属性
        
        Returns:
            Dict[str, Any]: 合并后的属性字典
        """
        logger.info("🔍 开始获取SKU合并属性", variant_id=variant_id)
        
        # 获取SKU信息
        variant_result = await self.db.execute(
            select(ProductVariant)
            .where(ProductVariant.id == variant_id)
            .options(selectinload(ProductVariant.product))
        )
        variant = variant_result.scalar_one_or_none()
        
        if not variant:
            return {}
        
        # 获取产品属性
        product_attributes = await self.get_product_attributes(variant.product_id)
        
        # 获取SKU属性
        variant_attributes = await self.get_variant_attributes(variant_id)
        
        # 合并属性（SKU属性优先）
        merged_attributes = {}
        
        # 先添加产品属性
        for attr in product_attributes:
            merged_attributes[attr.attribute_key] = {
                "value": attr.attribute_value,
                "type": attr.attribute_type,
                "display_name": attr.display_name,
                "source": "product"
            }
        
        # 再添加SKU属性（覆盖产品属性）
        for attr in variant_attributes:
            merged_attributes[attr.attribute_key] = {
                "value": attr.attribute_value,
                "type": attr.attribute_type,
                "display_name": attr.display_name,
                "source": "variant",
                "migrated_from_dimension": attr.migrated_from_dimension
            }
        
        logger.info("✅ SKU合并属性获取成功", 
                   variant_id=variant_id,
                   total_attributes=len(merged_attributes))
        
        return merged_attributes
    
    async def update_product_attribute(
        self,
        product_id: int,
        attribute_key: str,
        attribute_value: str,
        attribute_type: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> Optional[ProductAttribute]:
        """更新产品属性"""
        logger.info("🔍 开始更新产品属性", 
                   product_id=product_id,
                   attribute_key=attribute_key)
        
        attribute = await self.get_product_attribute_by_key(product_id, attribute_key)
        if not attribute:
            return None
        
        # 验证属性值类型
        validated_value = self._validate_attribute_value(attribute_value, attribute_type or attribute.attribute_type)
        
        # 更新属性
        attribute.attribute_value = validated_value
        if attribute_type:
            attribute.attribute_type = attribute_type
        if display_name:
            attribute.display_name = display_name
        
        await self.db.commit()
        
        logger.info("✅ 产品属性更新成功", attribute_id=attribute.id)
        
        return attribute
    
    async def update_variant_attribute(
        self,
        variant_id: int,
        attribute_key: str,
        attribute_value: str,
        attribute_type: Optional[str] = None,
        display_name: Optional[str] = None
    ) -> Optional[ProductVariantAttribute]:
        """更新SKU属性"""
        logger.info("🔍 开始更新SKU属性", 
                   variant_id=variant_id,
                   attribute_key=attribute_key)
        
        attribute = await self.get_variant_attribute_by_key(variant_id, attribute_key)
        if not attribute:
            return None
        
        # 验证属性值类型
        validated_value = self._validate_attribute_value(attribute_value, attribute_type or attribute.attribute_type)
        
        # 更新属性
        attribute.attribute_value = validated_value
        if attribute_type:
            attribute.attribute_type = attribute_type
        if display_name:
            attribute.display_name = display_name
        
        await self.db.commit()
        
        logger.info("✅ SKU属性更新成功", attribute_id=attribute.id)
        
        return attribute
    
    async def delete_product_attribute(
        self,
        product_id: int,
        attribute_key: str
    ) -> bool:
        """删除产品属性"""
        logger.info("🔍 开始删除产品属性", 
                   product_id=product_id,
                   attribute_key=attribute_key)
        
        attribute = await self.get_product_attribute_by_key(product_id, attribute_key)
        if not attribute:
            return False
        
        await self.db.delete(attribute)
        await self.db.commit()
        
        logger.info("✅ 产品属性删除成功")
        
        return True
    
    async def delete_variant_attribute(
        self,
        variant_id: int,
        attribute_key: str
    ) -> bool:
        """删除SKU属性"""
        logger.info("🔍 开始删除SKU属性", 
                   variant_id=variant_id,
                   attribute_key=attribute_key)
        
        attribute = await self.get_variant_attribute_by_key(variant_id, attribute_key)
        if not attribute:
            return False
        
        await self.db.delete(attribute)
        await self.db.commit()
        
        logger.info("✅ SKU属性删除成功")
        
        return True
    
    async def search_products_by_attribute(
        self,
        tenant_id: int,
        attribute_key: str,
        attribute_value: Optional[str] = None,
        attribute_type: Optional[str] = None,
        exact_match: bool = True
    ) -> List[Product]:
        """
        根据属性搜索产品
        
        Args:
            tenant_id: 租户ID
            attribute_key: 属性键
            attribute_value: 属性值（可选）
            attribute_type: 属性类型（可选）
            exact_match: 是否精确匹配
            
        Returns:
            List[Product]: 匹配的产品列表
        """
        logger.info("🔍 开始根据属性搜索产品", 
                   tenant_id=tenant_id,
                   attribute_key=attribute_key,
                   exact_match=exact_match)
        
        # 构建查询条件
        conditions = [
            Product.tenant_id == tenant_id,
            ProductAttribute.attribute_key == attribute_key
        ]
        
        if attribute_value:
            if exact_match:
                conditions.append(ProductAttribute.attribute_value == attribute_value)
            else:
                conditions.append(ProductAttribute.attribute_value.ilike(f"%{attribute_value}%"))
        
        if attribute_type:
            conditions.append(ProductAttribute.attribute_type == attribute_type)
        
        # 执行查询
        result = await self.db.execute(
            select(Product)
            .join(ProductAttribute, Product.id == ProductAttribute.product_id)
            .where(and_(*conditions))
            .distinct()
        )
        
        products = result.scalars().all()
        
        logger.info("✅ 产品属性搜索完成", 
                   found_count=len(products))
        
        return products
    
    async def search_variants_by_attribute(
        self,
        tenant_id: int,
        attribute_key: str,
        attribute_value: Optional[str] = None,
        attribute_type: Optional[str] = None,
        exact_match: bool = True
    ) -> List[ProductVariant]:
        """
        根据属性搜索SKU
        
        Args:
            tenant_id: 租户ID
            attribute_key: 属性键
            attribute_value: 属性值（可选）
            attribute_type: 属性类型（可选）
            exact_match: 是否精确匹配
            
        Returns:
            List[ProductVariant]: 匹配的SKU列表
        """
        logger.info("🔍 开始根据属性搜索SKU", 
                   tenant_id=tenant_id,
                   attribute_key=attribute_key,
                   exact_match=exact_match)
        
        # 构建查询条件
        conditions = [
            Product.tenant_id == tenant_id,
            ProductVariantAttribute.attribute_key == attribute_key
        ]
        
        if attribute_value:
            if exact_match:
                conditions.append(ProductVariantAttribute.attribute_value == attribute_value)
            else:
                conditions.append(ProductVariantAttribute.attribute_value.ilike(f"%{attribute_value}%"))
        
        if attribute_type:
            conditions.append(ProductVariantAttribute.attribute_type == attribute_type)
        
        # 执行查询
        result = await self.db.execute(
            select(ProductVariant)
            .join(Product, ProductVariant.product_id == Product.id)
            .join(ProductVariantAttribute, ProductVariant.id == ProductVariantAttribute.variant_id)
            .where(and_(*conditions))
            .distinct()
        )
        
        variants = result.scalars().all()
        
        logger.info("✅ SKU属性搜索完成", 
                   found_count=len(variants))
        
        return variants
    
    def _validate_attribute_value(
        self, 
        value: str, 
        attribute_type: str
    ) -> str:
        """
        验证属性值类型
        
        Args:
            value: 属性值
            attribute_type: 属性类型
            
        Returns:
            str: 验证后的属性值
            
        Raises:
            ValueError: 如果属性值类型不匹配
        """
        if attribute_type == 'string':
            return str(value)
        elif attribute_type == 'number':
            try:
                float(value)
                return str(value)
            except ValueError:
                raise ValueError(f"属性值 '{value}' 不是有效的数字")
        elif attribute_type == 'boolean':
            if value.lower() in ('true', 'false', '1', '0', 'yes', 'no'):
                return str(value.lower() in ('true', '1', 'yes'))
            else:
                raise ValueError(f"属性值 '{value}' 不是有效的布尔值")
        elif attribute_type == 'json':
            try:
                json.loads(value)
                return value
            except json.JSONDecodeError:
                raise ValueError(f"属性值 '{value}' 不是有效的JSON")
        else:
            return str(value)
    
    async def get_attribute_statistics(
        self, 
        tenant_id: int
    ) -> Dict[str, Any]:
        """
        获取属性统计信息
        
        Returns:
            Dict[str, Any]: 属性统计信息
        """
        logger.info("🔍 开始获取属性统计信息", tenant_id=tenant_id)
        
        # 产品属性统计
        product_attr_stats = await self.db.execute(
            select(
                ProductAttribute.attribute_key,
                ProductAttribute.attribute_type,
                func.count(ProductAttribute.id).label('count')
            )
            .join(Product, ProductAttribute.product_id == Product.id)
            .where(Product.tenant_id == tenant_id)
            .group_by(ProductAttribute.attribute_key, ProductAttribute.attribute_type)
        )
        
        # SKU属性统计
        variant_attr_stats = await self.db.execute(
            select(
                ProductVariantAttribute.attribute_key,
                ProductVariantAttribute.attribute_type,
                func.count(ProductVariantAttribute.id).label('count')
            )
            .join(ProductVariant, ProductVariantAttribute.variant_id == ProductVariant.id)
            .join(Product, ProductVariant.product_id == Product.id)
            .where(Product.tenant_id == tenant_id)
            .group_by(ProductVariantAttribute.attribute_key, ProductVariantAttribute.attribute_type)
        )
        
        stats = {
            "product_attributes": [
                {
                    "attribute_key": row.attribute_key,
                    "attribute_type": row.attribute_type,
                    "count": row.count
                }
                for row in product_attr_stats
            ],
            "variant_attributes": [
                {
                    "attribute_key": row.attribute_key,
                    "attribute_type": row.attribute_type,
                    "count": row.count
                }
                for row in variant_attr_stats
            ]
        }
        
        logger.info("✅ 属性统计信息获取成功")
        
        return stats

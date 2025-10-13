"""
ProductDimensionService - 产品维度管理服务

实现功能：
1. 维度模板的 CRUD 操作
2. 维度值的 CRUD 操作
3. 分类维度关联管理
4. 维度继承逻辑
5. SKU 维度值管理
6. 维度验证规则
"""

from typing import List, Optional, Dict, Set, Tuple, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import selectinload
import logging

from app.models.product_dimension import (
    ProductDimensionTemplate,
    ProductDimensionValue,
    ProductVariantDimension
)
from app.models.product_category import ProductCategoryDimension
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProductDimensionService:
    """产品维度管理服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_dimension_template(
        self,
        tenant_id: int,
        dimension_code: str,
        dimension_name: str,
        dimension_type: str = 'select',
        description: Optional[str] = None,
        sort_order: int = 0
    ) -> ProductDimensionTemplate:
        """
        创建维度模板
        
        Args:
            tenant_id: 租户ID
            dimension_code: 维度编码（如：color, size）
            dimension_name: 维度名称（如：颜色, 尺码）
            dimension_type: 维度类型（select, text, number, boolean）
            description: 描述
            sort_order: 排序
            
        Returns:
            ProductDimensionTemplate: 创建的维度模板
        """
        logger.info("🔍 开始创建维度模板", 
                   tenant_id=tenant_id,
                   dimension_code=dimension_code,
                   dimension_type=dimension_type)
        
        # 检查维度编码是否重复
        existing = await self.get_dimension_template_by_code(tenant_id, dimension_code)
        if existing:
            raise ValueError(f"维度编码 '{dimension_code}' 已存在")
        
        # 创建维度模板
        template = ProductDimensionTemplate(
            tenant_id=tenant_id,
            dimension_code=dimension_code,
            dimension_name=dimension_name,
            dimension_type=dimension_type,
            description=description,
            sort_order=sort_order
        )
        
        self.db.add(template)
        await self.db.commit()
        
        logger.info("✅ 维度模板创建成功", 
                   template_id=template.id,
                   dimension_code=dimension_code)
        
        return template
    
    async def get_dimension_template_by_code(
        self, 
        tenant_id: int, 
        dimension_code: str
    ) -> Optional[ProductDimensionTemplate]:
        """根据编码获取维度模板"""
        result = await self.db.execute(
            select(ProductDimensionTemplate)
            .where(
                and_(
                    ProductDimensionTemplate.tenant_id == tenant_id,
                    ProductDimensionTemplate.dimension_code == dimension_code
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_dimension_template_by_id(
        self, 
        template_id: int, 
        tenant_id: int
    ) -> Optional[ProductDimensionTemplate]:
        """根据ID获取维度模板"""
        result = await self.db.execute(
            select(ProductDimensionTemplate)
            .where(
                and_(
                    ProductDimensionTemplate.id == template_id,
                    ProductDimensionTemplate.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_dimension_templates(
        self, 
        tenant_id: int, 
        include_inactive: bool = False
    ) -> List[ProductDimensionTemplate]:
        """获取租户的所有维度模板"""
        query = select(ProductDimensionTemplate).where(
            ProductDimensionTemplate.tenant_id == tenant_id
        )
        
        if not include_inactive:
            query = query.where(ProductDimensionTemplate.is_active == True)
        
        query = query.order_by(ProductDimensionTemplate.sort_order, ProductDimensionTemplate.id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def create_dimension_value(
        self,
        category_dimension_id: int,
        dimension_template_id: int,
        value_code: str,
        value_name: str,
        value_type: str = 'normal',
        is_default: bool = False,
        sort_order: int = 0,
        created_by: Optional[int] = None
    ) -> ProductDimensionValue:
        """
        创建维度值
        
        Args:
            category_dimension_id: 分类维度关联ID
            dimension_template_id: 维度模板ID
            value_code: 值编码（如：red, S, M）
            value_name: 值名称（如：红色, 小号, 中号）
            value_type: 值类型（normal, default, not_applicable）
            is_default: 是否为默认值
            sort_order: 排序
            created_by: 创建人
            
        Returns:
            ProductDimensionValue: 创建的维度值
        """
        logger.info("🔍 开始创建维度值", 
                   category_dimension_id=category_dimension_id,
                   value_code=value_code,
                   value_type=value_type)
        
        # 检查值编码是否重复
        existing = await self.get_dimension_value_by_code(
            category_dimension_id, value_code
        )
        if existing:
            raise ValueError(f"维度值编码 '{value_code}' 已存在")
        
        # 创建维度值
        dimension_value = ProductDimensionValue(
            category_dimension_id=category_dimension_id,
            dimension_template_id=dimension_template_id,
            value_code=value_code,
            value_name=value_name,
            value_type=value_type,
            is_default=is_default,
            sort_order=sort_order,
            created_by=created_by
        )
        
        self.db.add(dimension_value)
        await self.db.commit()
        
        logger.info("✅ 维度值创建成功", 
                   value_id=dimension_value.id,
                   value_code=value_code)
        
        return dimension_value
    
    async def get_dimension_value_by_code(
        self, 
        category_dimension_id: int, 
        value_code: str
    ) -> Optional[ProductDimensionValue]:
        """根据编码获取维度值"""
        result = await self.db.execute(
            select(ProductDimensionValue)
            .where(
                and_(
                    ProductDimensionValue.category_dimension_id == category_dimension_id,
                    ProductDimensionValue.value_code == value_code
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_dimension_values_by_template(
        self, 
        dimension_template_id: int,
        category_dimension_id: Optional[int] = None
    ) -> List[ProductDimensionValue]:
        """获取维度模板的所有值"""
        query = select(ProductDimensionValue).where(
            ProductDimensionValue.dimension_template_id == dimension_template_id
        )
        
        if category_dimension_id:
            query = query.where(
                ProductDimensionValue.category_dimension_id == category_dimension_id
            )
        
        query = query.order_by(ProductDimensionValue.sort_order, ProductDimensionValue.id)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_effective_dimensions_for_category(
        self, 
        category_id: int, 
        tenant_id: int
    ) -> List[Dict[str, Any]]:
        """
        获取分类的有效维度（包括继承的维度）
        
        Returns:
            List[Dict]: 包含维度信息和继承来源的字典列表
        """
        logger.info("🔍 开始获取分类有效维度", category_id=category_id)
        
        # 获取分类的所有维度关联
        result = await self.db.execute(
            select(ProductCategoryDimension)
            .where(ProductCategoryDimension.category_id == category_id)
            .options(
                selectinload(ProductCategoryDimension.dimension_template),
                selectinload(ProductCategoryDimension.dimension_values)
            )
        )
        category_dimensions = result.scalars().all()
        
        effective_dimensions = []
        for cat_dim in category_dimensions:
            dimension_info = {
                "category_dimension_id": cat_dim.id,
                "dimension_template": cat_dim.dimension_template,
                "source_type": cat_dim.source_type,
                "source_category_id": cat_dim.source_category_id,
                "is_required": cat_dim.is_required,
                "is_overridable": cat_dim.is_overridable,
                "dimension_values": cat_dim.dimension_values,
                "sort_order": cat_dim.sort_order
            }
            effective_dimensions.append(dimension_info)
        
        logger.info("✅ 分类有效维度获取成功", 
                   category_id=category_id,
                   dimension_count=len(effective_dimensions))
        
        return effective_dimensions
    
    async def inherit_dimension_from_parent(
        self,
        child_category_id: int,
        parent_category_id: int,
        dimension_template_id: int,
        is_required: bool = True,
        is_overridable: bool = True
    ) -> ProductCategoryDimension:
        """
        从父分类继承维度
        
        Args:
            child_category_id: 子分类ID
            parent_category_id: 父分类ID
            dimension_template_id: 维度模板ID
            is_required: 是否必填
            is_overridable: 是否可覆盖
            
        Returns:
            ProductCategoryDimension: 创建的维度关联
        """
        logger.info("🔍 开始继承维度", 
                   child_category_id=child_category_id,
                   parent_category_id=parent_category_id,
                   dimension_template_id=dimension_template_id)
        
        # 检查是否已存在
        existing = await self.db.execute(
            select(ProductCategoryDimension)
            .where(
                and_(
                    ProductCategoryDimension.category_id == child_category_id,
                    ProductCategoryDimension.dimension_template_id == dimension_template_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("维度已存在，无法重复继承")
        
        # 创建继承关系
        category_dimension = ProductCategoryDimension(
            category_id=child_category_id,
            dimension_template_id=dimension_template_id,
            source_type='inherited',
            source_category_id=parent_category_id,
            is_required=is_required,
            is_overridable=is_overridable
        )
        
        self.db.add(category_dimension)
        await self.db.flush()  # 获取ID
        
        # 继承维度值
        parent_values_result = await self.db.execute(
            select(ProductDimensionValue)
            .where(
                and_(
                    ProductDimensionValue.dimension_template_id == dimension_template_id,
                    ProductCategoryDimension.category_id == parent_category_id
                )
                .join(ProductCategoryDimension, 
                      ProductDimensionValue.category_dimension_id == ProductCategoryDimension.id)
            )
        )
        parent_values = parent_values_result.scalars().all()
        
        for parent_value in parent_values:
            inherited_value = ProductDimensionValue(
                category_dimension_id=category_dimension.id,
                dimension_template_id=dimension_template_id,
                value_code=parent_value.value_code,
                value_name=parent_value.value_name,
                value_type=parent_value.value_type,
                is_default=parent_value.is_default,
                sort_order=parent_value.sort_order,
                created_by=parent_value.created_by
            )
            self.db.add(inherited_value)
        
        await self.db.commit()
        
        logger.info("✅ 维度继承成功", 
                   category_dimension_id=category_dimension.id)
        
        return category_dimension
    
    async def override_dimension(
        self,
        category_id: int,
        dimension_template_id: int,
        is_required: bool = None,
        is_overridable: bool = None
    ) -> ProductCategoryDimension:
        """
        覆盖继承的维度设置
        
        Args:
            category_id: 分类ID
            dimension_template_id: 维度模板ID
            is_required: 新的必填设置
            is_overridable: 新的可覆盖设置
            
        Returns:
            ProductCategoryDimension: 更新后的维度关联
        """
        logger.info("🔍 开始覆盖维度设置", 
                   category_id=category_id,
                   dimension_template_id=dimension_template_id)
        
        # 查找现有的维度关联
        result = await self.db.execute(
            select(ProductCategoryDimension)
            .where(
                and_(
                    ProductCategoryDimension.category_id == category_id,
                    ProductCategoryDimension.dimension_template_id == dimension_template_id
                )
            )
        )
        category_dimension = result.scalar_one_or_none()
        
        if not category_dimension:
            raise ValueError("维度关联不存在")
        
        if category_dimension.source_type != 'inherited':
            raise ValueError("只能覆盖继承的维度")
        
        # 更新设置
        if is_required is not None:
            category_dimension.is_required = is_required
        if is_overridable is not None:
            category_dimension.is_overridable = is_overridable
        
        category_dimension.source_type = 'overridden'
        
        await self.db.commit()
        
        logger.info("✅ 维度设置覆盖成功")
        
        return category_dimension
    
    async def remove_inherited_dimension(
        self,
        category_id: int,
        dimension_template_id: int
    ) -> bool:
        """
        移除继承的维度
        
        Args:
            category_id: 分类ID
            dimension_template_id: 维度模板ID
            
        Returns:
            bool: 是否成功移除
        """
        logger.info("🔍 开始移除继承维度", 
                   category_id=category_id,
                   dimension_template_id=dimension_template_id)
        
        result = await self.db.execute(
            select(ProductCategoryDimension)
            .where(
                and_(
                    ProductCategoryDimension.category_id == category_id,
                    ProductCategoryDimension.dimension_template_id == dimension_template_id,
                    ProductCategoryDimension.source_type == 'inherited'
                )
            )
        )
        category_dimension = result.scalar_one_or_none()
        
        if category_dimension:
            await self.db.delete(category_dimension)
            await self.db.commit()
            logger.info("✅ 继承维度移除成功")
            return True
        else:
            logger.warning("⚠️ 继承维度不存在")
            return False
    
    async def create_variant_dimension(
        self,
        variant_id: int,
        dimension_template_id: int,
        dimension_value_id: int
    ) -> ProductVariantDimension:
        """
        为SKU创建维度值
        
        Args:
            variant_id: SKU ID
            dimension_template_id: 维度模板ID
            dimension_value_id: 维度值ID
            
        Returns:
            ProductVariantDimension: 创建的SKU维度值
        """
        logger.info("🔍 开始创建SKU维度值", 
                   variant_id=variant_id,
                   dimension_template_id=dimension_template_id)
        
        # 检查是否已存在
        existing = await self.db.execute(
            select(ProductVariantDimension)
            .where(
                and_(
                    ProductVariantDimension.variant_id == variant_id,
                    ProductVariantDimension.dimension_template_id == dimension_template_id
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("SKU维度值已存在")
        
        # 创建SKU维度值
        variant_dimension = ProductVariantDimension(
            variant_id=variant_id,
            dimension_template_id=dimension_template_id,
            dimension_value_id=dimension_value_id
        )
        
        self.db.add(variant_dimension)
        await self.db.commit()
        
        logger.info("✅ SKU维度值创建成功", 
                   variant_dimension_id=variant_dimension.id)
        
        return variant_dimension
    
    async def get_variant_dimensions(
        self, 
        variant_id: int
    ) -> List[ProductVariantDimension]:
        """获取SKU的所有维度值"""
        result = await self.db.execute(
            select(ProductVariantDimension)
            .where(ProductVariantDimension.variant_id == variant_id)
            .options(
                selectinload(ProductVariantDimension.dimension_template),
                selectinload(ProductVariantDimension.dimension_value)
            )
        )
        return result.scalars().all()
    
    async def update_dimension_template(
        self,
        template_id: int,
        tenant_id: int,
        **update_data
    ) -> Optional[ProductDimensionTemplate]:
        """更新维度模板"""
        logger.info("🔍 开始更新维度模板", template_id=template_id)
        
        template = await self.get_dimension_template_by_id(template_id, tenant_id)
        if not template:
            return None
        
        # 更新字段
        for key, value in update_data.items():
            if hasattr(template, key):
                setattr(template, key, value)
        
        await self.db.commit()
        
        logger.info("✅ 维度模板更新成功", template_id=template_id)
        
        return template
    
    async def delete_dimension_template(
        self,
        template_id: int,
        tenant_id: int,
        force: bool = False
    ) -> bool:
        """删除维度模板"""
        logger.info("🔍 开始删除维度模板", 
                   template_id=template_id,
                   force=force)
        
        template = await self.get_dimension_template_by_id(template_id, tenant_id)
        if not template:
            return False
        
        # 检查是否被使用
        if not force:
            # 检查是否有分类在使用此维度
            category_usage = await self.db.execute(
                select(ProductCategoryDimension)
                .where(ProductCategoryDimension.dimension_template_id == template_id)
            )
            if category_usage.scalar_one_or_none():
                raise ValueError("维度模板正在被分类使用，无法删除。使用 force=True 强制删除。")
        
        # 删除模板（级联删除相关数据）
        await self.db.delete(template)
        await self.db.commit()
        
        logger.info("✅ 维度模板删除成功", template_id=template_id)
        
        return True

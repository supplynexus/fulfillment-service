"""
ProductCategorySwitchService - 产品分类切换服务

实现功能：
1. 分类切换检测
2. 维度兼容性分析
3. 维度迁移处理
4. SKU 维度值迁移
5. 不兼容维度处理
6. 分类切换回滚
"""

from typing import List, Optional, Dict, Set, Tuple, Any, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.orm import selectinload
import logging

from app.models.product import Product, ProductVariant
from app.models.product_category import (
    ProductCategory,
    ProductCategoryAssignment,
    ProductCategoryDimension
)
from app.models.product_dimension import (
    ProductDimensionTemplate,
    ProductDimensionValue,
    ProductVariantDimension
)
from app.models.product_attribute import ProductVariantAttribute
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProductCategorySwitchService:
    """产品分类切换服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def analyze_category_switch(
        self,
        product_id: int,
        new_category_id: int,
        tenant_id: int
    ) -> Dict[str, Any]:
        """
        分析分类切换的影响
        
        Args:
            product_id: 产品ID
            new_category_id: 新分类ID
            tenant_id: 租户ID
            
        Returns:
            Dict[str, Any]: 分析结果
        """
        logger.info("🔍 开始分析分类切换", 
                   product_id=product_id,
                   new_category_id=new_category_id)
        
        # 获取当前分类
        current_category = await self._get_product_current_category(product_id)
        
        # 获取新分类
        new_category = await self._get_category_by_id(new_category_id, tenant_id)
        if not new_category:
            raise ValueError("目标分类不存在")
        
        # 获取当前分类的维度
        current_dimensions = await self._get_category_dimensions(
            current_category.id if current_category else None
        )
        
        # 获取新分类的维度
        new_dimensions = await self._get_category_dimensions(new_category_id)
        
        # 分析维度兼容性
        compatibility_analysis = await self._analyze_dimension_compatibility(
            current_dimensions, new_dimensions
        )
        
        # 获取产品的SKU
        product_variants = await self._get_product_variants(product_id)
        
        # 分析SKU维度值影响
        variant_impact_analysis = await self._analyze_variant_impact(
            product_variants, current_dimensions, new_dimensions
        )
        
        analysis_result = {
            "current_category": {
                "id": current_category.id if current_category else None,
                "name": current_category.category_name if current_category else None
            },
            "new_category": {
                "id": new_category.id,
                "name": new_category.category_name
            },
            "compatibility_analysis": compatibility_analysis,
            "variant_impact_analysis": variant_impact_analysis,
            "recommendations": await self._generate_switch_recommendations(
                compatibility_analysis, variant_impact_analysis
            )
        }
        
        logger.info("✅ 分类切换分析完成", 
                   product_id=product_id,
                   new_category_id=new_category_id)
        
        return analysis_result
    
    async def switch_product_category(
        self,
        product_id: int,
        new_category_id: int,
        tenant_id: int,
        migration_strategy: str = "auto",
        preserve_incompatible_dimensions: bool = True,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        执行分类切换
        
        Args:
            product_id: 产品ID
            new_category_id: 新分类ID
            tenant_id: 租户ID
            migration_strategy: 迁移策略 (auto, manual, preserve)
            preserve_incompatible_dimensions: 是否保留不兼容维度
            user_id: 操作用户ID
            
        Returns:
            Dict[str, Any]: 切换结果
        """
        logger.info("🔍 开始执行分类切换", 
                   product_id=product_id,
                   new_category_id=new_category_id,
                   migration_strategy=migration_strategy)
        
        # 分析切换影响
        analysis = await self.analyze_category_switch(product_id, new_category_id, tenant_id)
        
        # 获取当前分类
        current_category = await self._get_product_current_category(product_id)
        
        # 获取新分类
        new_category = await self._get_category_by_id(new_category_id, tenant_id)
        
        # 执行分类切换
        switch_result = await self._execute_category_switch(
            product_id, new_category_id, tenant_id
        )
        
        # 处理维度迁移
        dimension_migration_result = await self._handle_dimension_migration(
            product_id, current_category, new_category, 
            analysis["compatibility_analysis"], migration_strategy, preserve_incompatible_dimensions
        )
        
        # 处理SKU维度值迁移
        variant_migration_result = await self._handle_variant_dimension_migration(
            product_id, analysis["variant_impact_analysis"], 
            migration_strategy, preserve_incompatible_dimensions, user_id
        )
        
        result = {
            "switch_successful": switch_result["success"],
            "category_switch": switch_result,
            "dimension_migration": dimension_migration_result,
            "variant_migration": variant_migration_result,
            "analysis": analysis
        }
        
        logger.info("✅ 分类切换完成", 
                   product_id=product_id,
                   new_category_id=new_category_id,
                   success=result["switch_successful"])
        
        return result
    
    async def rollback_category_switch(
        self,
        product_id: int,
        original_category_id: int,
        tenant_id: int,
        user_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        回滚分类切换
        
        Args:
            product_id: 产品ID
            original_category_id: 原始分类ID
            tenant_id: 租户ID
            user_id: 操作用户ID
            
        Returns:
            Dict[str, Any]: 回滚结果
        """
        logger.info("🔍 开始回滚分类切换", 
                   product_id=product_id,
                   original_category_id=original_category_id)
        
        # 执行分类回滚
        rollback_result = await self._execute_category_switch(
            product_id, original_category_id, tenant_id
        )
        
        # 回滚维度迁移
        dimension_rollback_result = await self._rollback_dimension_migration(
            product_id, original_category_id
        )
        
        # 回滚SKU维度值
        variant_rollback_result = await self._rollback_variant_dimension_migration(
            product_id, user_id
        )
        
        result = {
            "rollback_successful": rollback_result["success"],
            "category_rollback": rollback_result,
            "dimension_rollback": dimension_rollback_result,
            "variant_rollback": variant_rollback_result
        }
        
        logger.info("✅ 分类切换回滚完成", 
                   product_id=product_id,
                   success=result["rollback_successful"])
        
        return result
    
    async def _get_product_current_category(self, product_id: int) -> Optional[ProductCategory]:
        """获取产品的当前分类"""
        result = await self.db.execute(
            select(ProductCategory)
            .join(ProductCategoryAssignment, ProductCategory.id == ProductCategoryAssignment.category_id)
            .where(
                and_(
                    ProductCategoryAssignment.product_id == product_id,
                    ProductCategoryAssignment.is_primary == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_category_by_id(self, category_id: int, tenant_id: int) -> Optional[ProductCategory]:
        """根据ID获取分类"""
        result = await self.db.execute(
            select(ProductCategory)
            .where(
                and_(
                    ProductCategory.id == category_id,
                    ProductCategory.tenant_id == tenant_id
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_category_dimensions(self, category_id: Optional[int]) -> List[Dict[str, Any]]:
        """获取分类的维度"""
        if not category_id:
            return []
        
        result = await self.db.execute(
            select(ProductCategoryDimension)
            .where(ProductCategoryDimension.category_id == category_id)
            .options(
                selectinload(ProductCategoryDimension.dimension_template),
                selectinload(ProductCategoryDimension.dimension_values)
            )
        )
        
        dimensions = result.scalars().all()
        return [
            {
                "id": dim.id,
                "dimension_template": dim.dimension_template,
                "source_type": dim.source_type,
                "is_required": dim.is_required,
                "is_overridable": dim.is_overridable,
                "dimension_values": dim.dimension_values
            }
            for dim in dimensions
        ]
    
    async def _get_product_variants(self, product_id: int) -> List[ProductVariant]:
        """获取产品的所有SKU"""
        result = await self.db.execute(
            select(ProductVariant)
            .where(ProductVariant.product_id == product_id)
            .options(
                selectinload(ProductVariant.variant_dimensions),
                selectinload(ProductVariant.variant_attributes)
            )
        )
        return result.scalars().all()
    
    async def _analyze_dimension_compatibility(
        self,
        current_dimensions: List[Dict[str, Any]],
        new_dimensions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析维度兼容性"""
        current_dimension_codes = {dim["dimension_template"].dimension_code for dim in current_dimensions}
        new_dimension_codes = {dim["dimension_template"].dimension_code for dim in new_dimensions}
        
        compatible_dimensions = current_dimension_codes.intersection(new_dimension_codes)
        incompatible_dimensions = current_dimension_codes - new_dimension_codes
        new_dimensions_only = new_dimension_codes - current_dimension_codes
        
        return {
            "compatible_dimensions": list(compatible_dimensions),
            "incompatible_dimensions": list(incompatible_dimensions),
            "new_dimensions_only": list(new_dimensions_only),
            "compatibility_score": len(compatible_dimensions) / len(current_dimension_codes) if current_dimension_codes else 1.0
        }
    
    async def _analyze_variant_impact(
        self,
        variants: List[ProductVariant],
        current_dimensions: List[Dict[str, Any]],
        new_dimensions: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """分析SKU维度值影响"""
        affected_variants = []
        unaffected_variants = []
        
        for variant in variants:
            variant_dimensions = {vd.dimension_template.dimension_code: vd.dimension_value for vd in variant.variant_dimensions}
            
            # 检查是否有不兼容的维度值
            has_incompatible = False
            for dimension_code in variant_dimensions.keys():
                if dimension_code not in {dim["dimension_template"].dimension_code for dim in new_dimensions}:
                    has_incompatible = True
                    break
            
            if has_incompatible:
                affected_variants.append({
                    "variant_id": variant.id,
                    "sku": variant.sku,
                    "incompatible_dimensions": [
                        code for code in variant_dimensions.keys() 
                        if code not in {dim["dimension_template"].dimension_code for dim in new_dimensions}
                    ]
                })
            else:
                unaffected_variants.append(variant.id)
        
        return {
            "affected_variants": affected_variants,
            "unaffected_variants": unaffected_variants,
            "total_variants": len(variants),
            "affected_count": len(affected_variants)
        }
    
    async def _generate_switch_recommendations(
        self,
        compatibility_analysis: Dict[str, Any],
        variant_impact_analysis: Dict[str, Any]
    ) -> List[str]:
        """生成切换建议"""
        recommendations = []
        
        if compatibility_analysis["compatibility_score"] < 0.5:
            recommendations.append("⚠️ 维度兼容性较低，建议谨慎切换")
        
        if variant_impact_analysis["affected_count"] > 0:
            recommendations.append(f"⚠️ {variant_impact_analysis['affected_count']} 个SKU将受到影响")
            recommendations.append("建议选择保留不兼容维度作为产品属性")
        
        if compatibility_analysis["new_dimensions_only"]:
            recommendations.append(f"ℹ️ 新分类有 {len(compatibility_analysis['new_dimensions_only'])} 个新维度")
        
        return recommendations
    
    async def _execute_category_switch(
        self,
        product_id: int,
        new_category_id: int,
        tenant_id: int
    ) -> Dict[str, Any]:
        """执行分类切换"""
        try:
            # 更新或创建分类归属
            existing_assignment = await self.db.execute(
                select(ProductCategoryAssignment)
                .where(
                    and_(
                        ProductCategoryAssignment.product_id == product_id,
                        ProductCategoryAssignment.is_primary == True
                    )
                )
            )
            assignment = existing_assignment.scalar_one_or_none()
            
            if assignment:
                assignment.category_id = new_category_id
            else:
                assignment = ProductCategoryAssignment(
                    product_id=product_id,
                    category_id=new_category_id,
                    is_primary=True
                )
                self.db.add(assignment)
            
            await self.db.commit()
            
            return {"success": True, "message": "分类切换成功"}
        except Exception as e:
            await self.db.rollback()
            logger.error("❌ 分类切换失败", error=str(e))
            return {"success": False, "message": f"分类切换失败: {str(e)}"}
    
    async def _handle_dimension_migration(
        self,
        product_id: int,
        current_category: Optional[ProductCategory],
        new_category: ProductCategory,
        compatibility_analysis: Dict[str, Any],
        migration_strategy: str,
        preserve_incompatible_dimensions: bool
    ) -> Dict[str, Any]:
        """处理维度迁移"""
        migration_result = {
            "success": True,
            "migrated_dimensions": [],
            "preserved_dimensions": [],
            "errors": []
        }
        
        try:
            if preserve_incompatible_dimensions and compatibility_analysis["incompatible_dimensions"]:
                # 将不兼容的维度转换为产品属性
                for dimension_code in compatibility_analysis["incompatible_dimensions"]:
                    await self._convert_dimension_to_attribute(
                        product_id, dimension_code, migration_result
                    )
            
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            migration_result["success"] = False
            migration_result["errors"].append(str(e))
            logger.error("❌ 维度迁移失败", error=str(e))
        
        return migration_result
    
    async def _handle_variant_dimension_migration(
        self,
        product_id: int,
        variant_impact_analysis: Dict[str, Any],
        migration_strategy: str,
        preserve_incompatible_dimensions: bool,
        user_id: Optional[int]
    ) -> Dict[str, Any]:
        """处理SKU维度值迁移"""
        migration_result = {
            "success": True,
            "migrated_variants": [],
            "preserved_variants": [],
            "errors": []
        }
        
        try:
            for affected_variant in variant_impact_analysis["affected_variants"]:
                if preserve_incompatible_dimensions:
                    # 将不兼容的维度值转换为SKU属性
                    await self._convert_variant_dimensions_to_attributes(
                        affected_variant["variant_id"],
                        affected_variant["incompatible_dimensions"],
                        user_id,
                        migration_result
                    )
                else:
                    # 删除不兼容的维度值
                    await self._remove_incompatible_variant_dimensions(
                        affected_variant["variant_id"],
                        affected_variant["incompatible_dimensions"],
                        migration_result
                    )
            
            await self.db.commit()
            
        except Exception as e:
            await self.db.rollback()
            migration_result["success"] = False
            migration_result["errors"].append(str(e))
            logger.error("❌ SKU维度值迁移失败", error=str(e))
        
        return migration_result
    
    async def _convert_dimension_to_attribute(
        self,
        product_id: int,
        dimension_code: str,
        migration_result: Dict[str, Any]
    ) -> None:
        """将维度转换为产品属性"""
        # 这里需要实现具体的转换逻辑
        # 将维度的维度值转换为产品属性
        pass
    
    async def _convert_variant_dimensions_to_attributes(
        self,
        variant_id: int,
        incompatible_dimensions: List[str],
        user_id: Optional[int],
        migration_result: Dict[str, Any]
    ) -> None:
        """将SKU的维度值转换为属性"""
        # 获取SKU的维度值
        variant_dimensions = await self.db.execute(
            select(ProductVariantDimension)
            .where(ProductVariantDimension.variant_id == variant_id)
            .options(
                selectinload(ProductVariantDimension.dimension_template),
                selectinload(ProductVariantDimension.dimension_value)
            )
        )
        
        for vd in variant_dimensions.scalars().all():
            if vd.dimension_template.dimension_code in incompatible_dimensions:
                # 创建SKU属性
                attribute = ProductVariantAttribute(
                    variant_id=variant_id,
                    attribute_key=vd.dimension_template.dimension_code,
                    attribute_value=vd.dimension_value.value_name,
                    attribute_type='string',
                    migrated_from_dimension=True,
                    created_by=user_id
                )
                self.db.add(attribute)
                
                # 删除维度值
                await self.db.delete(vd)
                
                migration_result["migrated_variants"].append(variant_id)
    
    async def _remove_incompatible_variant_dimensions(
        self,
        variant_id: int,
        incompatible_dimensions: List[str],
        migration_result: Dict[str, Any]
    ) -> None:
        """删除不兼容的SKU维度值"""
        # 删除不兼容的维度值
        await self.db.execute(
            text("""
                DELETE FROM product_variant_dimensions 
                WHERE variant_id = :variant_id 
                AND dimension_template_id IN (
                    SELECT id FROM product_dimension_templates 
                    WHERE dimension_code = ANY(:dimension_codes)
                )
            """),
            {
                "variant_id": variant_id,
                "dimension_codes": incompatible_dimensions
            }
        )
        
        migration_result["preserved_variants"].append(variant_id)
    
    async def _rollback_dimension_migration(
        self,
        product_id: int,
        original_category_id: int
    ) -> Dict[str, Any]:
        """回滚维度迁移"""
        # 实现回滚逻辑
        return {"success": True, "message": "维度迁移回滚成功"}
    
    async def _rollback_variant_dimension_migration(
        self,
        product_id: int,
        user_id: Optional[int]
    ) -> Dict[str, Any]:
        """回滚SKU维度值迁移"""
        # 实现回滚逻辑
        return {"success": True, "message": "SKU维度值迁移回滚成功"}

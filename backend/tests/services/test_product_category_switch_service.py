"""
ProductCategorySwitchService 单元测试

测试产品分类切换的核心功能：
1. 分类切换兼容性分析
2. 维度冲突检测
3. 维度迁移处理
4. 分类切换执行
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.product_category_switch_service import ProductCategorySwitchService
from app.models.product import Product, ProductVariant
from app.models.product_category import (
    ProductCategory,
    ProductCategoryDimension,
    ProductCategoryAssignment
)
from app.models.product_dimension import (
    ProductDimensionTemplate,
    ProductDimensionValue,
    ProductVariantDimension
)
from app.models.product_attribute import ProductAttribute, ProductVariantAttribute


class TestProductCategorySwitchService:
    """ProductCategorySwitchService 测试类"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return ProductCategorySwitchService(mock_db)
    
    @pytest.fixture
    def sample_product(self):
        """示例产品数据"""
        product = Product()
        product.id = 1
        product.tenant_id = 1
        product.name = "基础 T 恤"
        product.handle = "basic-tshirt"
        product.description = "经典基础款 T 恤"
        product.is_active = True
        return product
    
    @pytest.fixture
    def sample_variant(self):
        """示例 SKU 数据"""
        variant = ProductVariant()
        variant.id = 1
        variant.product_id = 1
        variant.sku = "BASIC-TSHIRT-RED-S"
        variant.name = "基础 T 恤 红色 小号"
        variant.price = 29.99
        variant.is_active = True
        return variant
    
    @pytest.fixture
    def source_category(self):
        """源分类（服装）"""
        category = ProductCategory()
        category.id = 1
        category.tenant_id = 1
        category.category_code = "clothing"
        category.category_name = "服装"
        category.is_active = True
        return category
    
    @pytest.fixture
    def target_category(self):
        """目标分类（电子产品）"""
        category = ProductCategory()
        category.id = 2
        category.tenant_id = 1
        category.category_code = "electronics"
        category.category_name = "电子产品"
        category.is_active = True
        return category
    
    @pytest.fixture
    def clothing_dimensions(self):
        """服装分类的维度"""
        color_dimension = ProductCategoryDimension()
        color_dimension.id = 1
        color_dimension.category_id = 1
        color_dimension.dimension_template_id = 1
        color_dimension.source_type = "own"
        color_dimension.is_required = True
        color_dimension.is_overridable = True
        
        size_dimension = ProductCategoryDimension()
        size_dimension.id = 2
        size_dimension.category_id = 1
        size_dimension.dimension_template_id = 2
        size_dimension.source_type = "own"
        size_dimension.is_required = True
        size_dimension.is_overridable = True
        
        return [color_dimension, size_dimension]
    
    @pytest.fixture
    def electronics_dimensions(self):
        """电子产品分类的维度"""
        brand_dimension = ProductCategoryDimension()
        brand_dimension.id = 3
        brand_dimension.category_id = 2
        brand_dimension.dimension_template_id = 3
        brand_dimension.source_type = "own"
        brand_dimension.is_required = True
        brand_dimension.is_overridable = True
        
        model_dimension = ProductCategoryDimension()
        model_dimension.id = 4
        model_dimension.category_id = 2
        model_dimension.dimension_template_id = 4
        model_dimension.source_type = "own"
        model_dimension.is_required = True
        model_dimension.is_overridable = True
        
        return [brand_dimension, model_dimension]
    
    @pytest.fixture
    def dimension_templates(self):
        """维度模板"""
        color_template = ProductDimensionTemplate()
        color_template.id = 1
        color_template.dimension_code = "color"
        color_template.dimension_name = "颜色"
        color_template.dimension_type = "select"
        
        size_template = ProductDimensionTemplate()
        size_template.id = 2
        size_template.dimension_code = "size"
        size_template.dimension_name = "尺码"
        size_template.dimension_type = "select"
        
        brand_template = ProductDimensionTemplate()
        brand_template.id = 3
        brand_template.dimension_code = "brand"
        brand_template.dimension_name = "品牌"
        brand_template.dimension_type = "select"
        
        model_template = ProductDimensionTemplate()
        model_template.id = 4
        model_template.dimension_code = "model"
        model_template.dimension_name = "型号"
        model_template.dimension_type = "text"
        
        return [color_template, size_template, brand_template, model_template]

    @pytest.mark.asyncio
    async def test_analyze_category_switch_compatibility_success(self, service, mock_db, 
                                                               sample_product, source_category, 
                                                               target_category, clothing_dimensions, 
                                                               electronics_dimensions):
        """测试成功分析分类切换兼容性"""
        # 准备测试数据
        product_id = 1
        target_category_id = 2
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_product
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            source_category,  # 当前分类
            target_category   # 目标分类
        ]
        
        # 模拟分类维度查询
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = clothing_dimensions + electronics_dimensions
        mock_db.execute.return_value = mock_result
        
        # 执行测试
        result = await service.analyze_category_switch_compatibility(
            product_id=product_id,
            target_category_id=target_category_id
        )
        
        # 验证结果
        assert result is not None
        assert "compatible_dimensions" in result
        assert "incompatible_dimensions" in result
        assert "conflicts" in result
        assert "recommendations" in result

    @pytest.mark.asyncio
    async def test_analyze_category_switch_compatibility_product_not_found(self, service, mock_db):
        """测试分析不存在的产品的分类切换兼容性"""
        # 准备测试数据
        product_id = 999
        target_category_id = 2
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="产品不存在"):
            await service.analyze_category_switch_compatibility(
                product_id=product_id,
                target_category_id=target_category_id
            )

    @pytest.mark.asyncio
    async def test_analyze_category_switch_compatibility_target_category_not_found(self, service, mock_db, sample_product):
        """测试分析切换到不存在分类的兼容性"""
        # 准备测试数据
        product_id = 1
        target_category_id = 999
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            sample_product,  # 产品存在
            None            # 目标分类不存在
        ]
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="目标分类不存在"):
            await service.analyze_category_switch_compatibility(
                product_id=product_id,
                target_category_id=target_category_id
            )

    @pytest.mark.asyncio
    async def test_detect_dimension_conflicts(self, service, clothing_dimensions, electronics_dimensions):
        """测试检测维度冲突"""
        # 准备测试数据
        source_dimensions = clothing_dimensions
        target_dimensions = electronics_dimensions
        
        # 执行测试
        result = service.detect_dimension_conflicts(
            source_dimensions=source_dimensions,
            target_dimensions=target_dimensions
        )
        
        # 验证结果
        assert result is not None
        assert "conflicts" in result
        assert "compatible_dimensions" in result
        assert "incompatible_dimensions" in result

    @pytest.mark.asyncio
    async def test_detect_dimension_conflicts_no_conflicts(self, service):
        """测试检测无冲突的维度"""
        # 准备测试数据
        source_dimensions = []
        target_dimensions = []
        
        # 执行测试
        result = service.detect_dimension_conflicts(
            source_dimensions=source_dimensions,
            target_dimensions=target_dimensions
        )
        
        # 验证结果
        assert result is not None
        assert len(result["conflicts"]) == 0
        assert len(result["compatible_dimensions"]) == 0
        assert len(result["incompatible_dimensions"]) == 0

    @pytest.mark.asyncio
    async def test_migrate_incompatible_dimensions_to_attributes(self, service, mock_db, sample_product, sample_variant):
        """测试将不兼容的维度迁移为属性"""
        # 准备测试数据
        product_id = 1
        incompatible_dimensions = [
            {
                "dimension_template_id": 1,
                "dimension_name": "颜色",
                "dimension_code": "color",
                "current_values": ["red", "blue"]
            }
        ]
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_product
        mock_db.execute.return_value.scalar.return_value = 1  # 新属性 ID
        mock_db.commit.return_value = None
        
        # 执行测试
        result = await service.migrate_incompatible_dimensions_to_attributes(
            product_id=product_id,
            incompatible_dimensions=incompatible_dimensions
        )
        
        # 验证结果
        assert result is not None
        assert "migrated_attributes" in result
        assert "migrated_variant_attributes" in result
        
        # 验证数据库调用
        mock_db.add.assert_called()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_migrate_incompatible_dimensions_to_attributes_product_not_found(self, service, mock_db):
        """测试为不存在的产品迁移不兼容维度"""
        # 准备测试数据
        product_id = 999
        incompatible_dimensions = []
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="产品不存在"):
            await service.migrate_incompatible_dimensions_to_attributes(
                product_id=product_id,
                incompatible_dimensions=incompatible_dimensions
            )

    @pytest.mark.asyncio
    async def test_execute_category_switch_success(self, service, mock_db, sample_product, target_category):
        """测试成功执行分类切换"""
        # 准备测试数据
        product_id = 1
        target_category_id = 2
        switch_options = {
            "migrate_incompatible_dimensions": True,
            "remove_incompatible_dimensions": False,
            "keep_compatible_dimensions": True
        }
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_product
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            sample_product,  # 产品查询
            target_category   # 目标分类查询
        ]
        mock_db.execute.return_value.scalar.return_value = 1  # 新分类分配 ID
        mock_db.commit.return_value = None
        
        # 执行测试
        result = await service.execute_category_switch(
            product_id=product_id,
            target_category_id=target_category_id,
            switch_options=switch_options
        )
        
        # 验证结果
        assert result is not None
        assert "success" in result
        assert "new_category_assignment" in result
        assert "migrated_dimensions" in result
        assert "removed_dimensions" in result
        
        # 验证数据库调用
        mock_db.add.assert_called()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_category_switch_product_not_found(self, service, mock_db):
        """测试为不存在的产品执行分类切换"""
        # 准备测试数据
        product_id = 999
        target_category_id = 2
        switch_options = {}
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="产品不存在"):
            await service.execute_category_switch(
                product_id=product_id,
                target_category_id=target_category_id,
                switch_options=switch_options
            )

    @pytest.mark.asyncio
    async def test_execute_category_switch_target_category_not_found(self, service, mock_db, sample_product):
        """测试切换到不存在分类的分类切换"""
        # 准备测试数据
        product_id = 1
        target_category_id = 999
        switch_options = {}
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            sample_product,  # 产品存在
            None            # 目标分类不存在
        ]
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="目标分类不存在"):
            await service.execute_category_switch(
                product_id=product_id,
                target_category_id=target_category_id,
                switch_options=switch_options
            )

    @pytest.mark.asyncio
    async def test_validate_switch_options(self, service):
        """测试验证切换选项"""
        # 准备测试数据
        valid_options = {
            "migrate_incompatible_dimensions": True,
            "remove_incompatible_dimensions": False,
            "keep_compatible_dimensions": True
        }
        
        # 执行测试
        result = service.validate_switch_options(valid_options)
        
        # 验证结果
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_switch_options_invalid(self, service):
        """测试验证无效的切换选项"""
        # 准备测试数据
        invalid_options = {
            "migrate_incompatible_dimensions": "invalid_boolean",
            "remove_incompatible_dimensions": None,
            "keep_compatible_dimensions": True
        }
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="无效的切换选项"):
            service.validate_switch_options(invalid_options)

    @pytest.mark.asyncio
    async def test_get_product_current_category(self, service, mock_db, sample_product, source_category):
        """测试获取产品当前分类"""
        # 准备测试数据
        product_id = 1
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_product
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            sample_product,  # 产品查询
            source_category   # 当前分类查询
        ]
        
        # 执行测试
        result = await service.get_product_current_category(product_id=product_id)
        
        # 验证结果
        assert result is not None
        assert result.id == source_category.id
        assert result.category_name == source_category.category_name

    @pytest.mark.asyncio
    async def test_get_product_current_category_not_found(self, service, mock_db):
        """测试获取不存在产品的当前分类"""
        # 准备测试数据
        product_id = 999
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="产品不存在"):
            await service.get_product_current_category(product_id=product_id)

    @pytest.mark.asyncio
    async def test_get_product_current_category_no_assignment(self, service, mock_db, sample_product):
        """测试获取未分配分类的产品的当前分类"""
        # 准备测试数据
        product_id = 1
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [
            sample_product,  # 产品存在
            None            # 没有分类分配
        ]
        
        # 执行测试
        result = await service.get_product_current_category(product_id=product_id)
        
        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    async def test_cleanup_old_category_assignment(self, service, mock_db):
        """测试清理旧分类分配"""
        # 准备测试数据
        product_id = 1
        old_category_id = 1
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = ProductCategoryAssignment(id=1)
        mock_db.commit.return_value = None
        
        # 执行测试
        result = await service.cleanup_old_category_assignment(
            product_id=product_id,
            old_category_id=old_category_id
        )
        
        # 验证结果
        assert result is True
        
        # 验证数据库调用
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_cleanup_old_category_assignment_not_found(self, service, mock_db):
        """测试清理不存在的旧分类分配"""
        # 准备测试数据
        product_id = 1
        old_category_id = 999
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试
        result = await service.cleanup_old_category_assignment(
            product_id=product_id,
            old_category_id=old_category_id
        )
        
        # 验证结果
        assert result is False


class TestProductCategorySwitchServiceIntegration:
    """ProductCategorySwitchService 集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_category_switch_workflow(self):
        """测试完整的分类切换工作流"""
        # 这个测试需要真实的数据库连接
        # 在实际测试环境中运行
        pass

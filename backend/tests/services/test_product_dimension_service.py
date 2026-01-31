"""
ProductDimensionService 单元测试

测试维度管理的核心功能：
1. 维度模板 CRUD 操作
2. 维度继承管理
3. 维度值管理
4. 维度覆盖和移除
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.product_dimension_service import ProductDimensionService
from app.models.product_dimension import (
    ProductDimensionTemplate,
    ProductDimensionValue,
    ProductVariantDimension
)
from app.models.product_category import (
    ProductCategory,
    ProductCategoryDimension
)


class TestProductDimensionService:
    """ProductDimensionService 测试类"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return ProductDimensionService(mock_db)
    
    @pytest.fixture
    def sample_dimension_template(self):
        """示例维度模板数据"""
        template = ProductDimensionTemplate()
        template.id = 1
        template.tenant_id = 1
        template.dimension_code = "color"
        template.dimension_name = "颜色"
        template.dimension_type = "select"
        template.description = "产品颜色维度"
        template.sort_order = 1
        template.is_active = True
        return template
    
    @pytest.fixture
    def sample_dimension_value(self):
        """示例维度值数据"""
        value = ProductDimensionValue()
        value.id = 1
        value.category_dimension_id = 1
        value.dimension_template_id = 1
        value.value_code = "red"
        value.value_name = "红色"
        value.value_type = "normal"
        value.is_default = False
        value.review_status = "approved"
        value.sort_order = 1
        value.is_active = True
        return value
    
    @pytest.fixture
    def sample_category(self):
        """示例分类数据"""
        category = ProductCategory()
        category.id = 1
        category.tenant_id = 1
        category.category_code = "electronics"
        category.category_name = "电子产品"
        category.is_active = True
        return category

    @pytest.mark.asyncio
    async def test_create_dimension_template_success(self, service, mock_db, sample_dimension_template):
        """测试成功创建维度模板"""
        # 准备测试数据
        tenant_id = 1
        dimension_code = "color"
        dimension_name = "颜色"
        dimension_type = "select"
        description = "产品颜色维度"
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None  # 模板不存在
        mock_db.execute.return_value.scalar.return_value = sample_dimension_template.id
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # 执行测试
        result = await service.create_dimension_template(
            tenant_id=tenant_id,
            dimension_code=dimension_code,
            dimension_name=dimension_name,
            dimension_type=dimension_type,
            description=description
        )
        
        # 验证结果
        assert result is not None
        assert result.dimension_code == dimension_code
        assert result.dimension_name == dimension_name
        assert result.dimension_type == dimension_type
        assert result.description == description
        assert result.tenant_id == tenant_id
        
        # 验证数据库调用
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_dimension_template_duplicate_code(self, service, mock_db):
        """测试创建重复编码的维度模板"""
        # 准备测试数据
        tenant_id = 1
        dimension_code = "color"
        dimension_name = "颜色"
        
        # 模拟数据库查询结果 - 模板已存在
        mock_db.execute.return_value.scalar_one_or_none.return_value = ProductDimensionTemplate()
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="维度编码已存在"):
            await service.create_dimension_template(
                tenant_id=tenant_id,
                dimension_code=dimension_code,
                dimension_name=dimension_name
            )

    @pytest.mark.asyncio
    async def test_get_effective_dimensions(self, service, mock_db, sample_category):
        """测试获取分类的有效维度"""
        # 准备测试数据
        category_id = 1
        dimensions = [
            ProductCategoryDimension(
                id=1,
                category_id=1,
                dimension_template_id=1,
                source_type="own",
                is_required=True,
                is_overridable=True,
                is_active=True
            ),
            ProductCategoryDimension(
                id=2,
                category_id=1,
                dimension_template_id=2,
                source_type="inherited",
                source_category_id=2,
                is_required=False,
                is_overridable=True,
                is_active=True
            )
        ]
        
        # 模拟数据库查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = dimensions
        mock_db.execute.return_value = mock_result
        
        # 执行测试
        result = await service.get_effective_dimensions(category_id=category_id)
        
        # 验证结果
        assert result is not None
        assert len(result) == 2
        assert result[0].source_type == "own"
        assert result[1].source_type == "inherited"

    @pytest.mark.asyncio
    async def test_get_available_parent_dimensions(self, service, mock_db, sample_category):
        """测试获取可继承的父分类维度"""
        # 准备测试数据
        category_id = 1
        parent_dimensions = [
            ProductCategoryDimension(
                id=1,
                category_id=2,
                dimension_template_id=1,
                source_type="own",
                is_required=True,
                is_overridable=True,
                is_active=True
            )
        ]
        
        # 模拟数据库查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = parent_dimensions
        mock_db.execute.return_value = mock_result
        
        # 执行测试
        result = await service.get_available_parent_dimensions(category_id=category_id)
        
        # 验证结果
        assert result is not None
        assert len(result) == 1
        assert result[0].source_type == "own"

    @pytest.mark.asyncio
    async def test_inherit_dimension_success(self, service, mock_db, sample_category):
        """测试成功继承维度"""
        # 准备测试数据
        category_id = 1
        dimension_template_id = 1
        source_category_id = 2
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None  # 维度不存在
        mock_db.execute.return_value.scalar.return_value = 1  # 新维度ID
        mock_db.commit.return_value = None
        
        # 执行测试
        result = await service.inherit_dimension(
            category_id=category_id,
            dimension_template_id=dimension_template_id,
            source_category_id=source_category_id
        )
        
        # 验证结果
        assert result is not None
        assert result.category_id == category_id
        assert result.dimension_template_id == dimension_template_id
        assert result.source_category_id == source_category_id
        assert result.source_type == "inherited"
        
        # 验证数据库调用
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_inherit_dimension_already_exists(self, service, mock_db):
        """测试继承已存在的维度"""
        # 准备测试数据
        category_id = 1
        dimension_template_id = 1
        source_category_id = 2
        
        # 模拟数据库查询结果 - 维度已存在
        mock_db.execute.return_value.scalar_one_or_none.return_value = ProductCategoryDimension()
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="维度已存在"):
            await service.inherit_dimension(
                category_id=category_id,
                dimension_template_id=dimension_template_id,
                source_category_id=source_category_id
            )

    @pytest.mark.asyncio
    async def test_override_dimension_success(self, service, mock_db):
        """测试成功覆盖维度"""
        # 准备测试数据
        category_id = 1
        dimension_template_id = 1
        override_data = {
            "is_required": False,
            "is_overridable": False
        }
        
        # 模拟数据库查询结果
        existing_dimension = ProductCategoryDimension(
            id=1,
            category_id=category_id,
            dimension_template_id=dimension_template_id,
            source_type="inherited",
            source_category_id=2,
            is_required=True,
            is_overridable=True
        )
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_dimension
        mock_db.commit.return_value = None
        
        # 执行测试
        result = await service.override_dimension(
            category_id=category_id,
            dimension_template_id=dimension_template_id,
            **override_data
        )
        
        # 验证结果
        assert result is not None
        assert result.is_required == False
        assert result.is_overridable == False
        assert result.source_type == "overridden"
        
        # 验证数据库调用
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_override_dimension_not_found(self, service, mock_db):
        """测试覆盖不存在的维度"""
        # 准备测试数据
        category_id = 1
        dimension_template_id = 999
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="维度不存在"):
            await service.override_dimension(
                category_id=category_id,
                dimension_template_id=dimension_template_id
            )

    @pytest.mark.asyncio
    async def test_remove_inherited_dimension_success(self, service, mock_db):
        """测试成功移除继承的维度"""
        # 准备测试数据
        category_id = 1
        dimension_template_id = 1
        
        # 模拟数据库查询结果
        existing_dimension = ProductCategoryDimension(
            id=1,
            category_id=category_id,
            dimension_template_id=dimension_template_id,
            source_type="inherited",
            source_category_id=2
        )
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_dimension
        mock_db.commit.return_value = None
        
        # 执行测试
        result = await service.remove_inherited_dimension(
            category_id=category_id,
            dimension_template_id=dimension_template_id
        )
        
        # 验证结果
        assert result is True
        
        # 验证数据库调用
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_remove_inherited_dimension_not_inherited(self, service, mock_db):
        """测试移除非继承的维度"""
        # 准备测试数据
        category_id = 1
        dimension_template_id = 1
        
        # 模拟数据库查询结果
        existing_dimension = ProductCategoryDimension(
            id=1,
            category_id=category_id,
            dimension_template_id=dimension_template_id,
            source_type="own"  # 非继承维度
        )
        mock_db.execute.return_value.scalar_one_or_none.return_value = existing_dimension
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="只能移除继承的维度"):
            await service.remove_inherited_dimension(
                category_id=category_id,
                dimension_template_id=dimension_template_id
            )

    @pytest.mark.asyncio
    async def test_create_dimension_value_success(self, service, mock_db, sample_dimension_value):
        """测试成功创建维度值"""
        # 准备测试数据
        category_dimension_id = 1
        value_code = "red"
        value_name = "红色"
        value_type = "normal"
        is_default = False
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None  # 值不存在
        mock_db.execute.return_value.scalar.return_value = sample_dimension_value.id
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # 执行测试
        result = await service.create_dimension_value(
            category_dimension_id=category_dimension_id,
            value_code=value_code,
            value_name=value_name,
            value_type=value_type,
            is_default=is_default
        )
        
        # 验证结果
        assert result is not None
        assert result.value_code == value_code
        assert result.value_name == value_name
        assert result.value_type == value_type
        assert result.is_default == is_default
        
        # 验证数据库调用
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_dimension_value_duplicate_code(self, service, mock_db):
        """测试创建重复编码的维度值"""
        # 准备测试数据
        category_dimension_id = 1
        value_code = "red"
        value_name = "红色"
        
        # 模拟数据库查询结果 - 值已存在
        mock_db.execute.return_value.scalar_one_or_none.return_value = ProductDimensionValue()
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="维度值编码已存在"):
            await service.create_dimension_value(
                category_dimension_id=category_dimension_id,
                value_code=value_code,
                value_name=value_name
            )

    @pytest.mark.asyncio
    async def test_get_dimension_template_by_id(self, service, mock_db, sample_dimension_template):
        """测试根据ID获取维度模板"""
        # 准备测试数据
        template_id = 1
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_dimension_template
        
        # 执行测试
        result = await service.get_dimension_template_by_id(template_id=template_id)
        
        # 验证结果
        assert result is not None
        assert result.id == template_id
        assert result.dimension_name == "颜色"

    @pytest.mark.asyncio
    async def test_get_dimension_template_by_id_not_found(self, service, mock_db):
        """测试获取不存在的维度模板"""
        # 准备测试数据
        template_id = 999
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试
        result = await service.get_dimension_template_by_id(template_id=template_id)
        
        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    async def test_update_dimension_template(self, service, mock_db, sample_dimension_template):
        """测试更新维度模板"""
        # 准备测试数据
        template_id = 1
        update_data = {
            "dimension_name": "更新后的颜色",
            "description": "更新后的描述"
        }
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_dimension_template
        mock_db.commit.return_value = None
        
        # 执行测试
        result = await service.update_dimension_template(
            template_id=template_id,
            **update_data
        )
        
        # 验证结果
        assert result is not None
        assert result.dimension_name == "更新后的颜色"
        assert result.description == "更新后的描述"
        
        # 验证数据库调用
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_dimension_template(self, service, mock_db):
        """测试删除维度模板"""
        # 准备测试数据
        template_id = 1
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = ProductDimensionTemplate(id=1)
        mock_db.commit.return_value = None
        
        # 执行测试
        result = await service.delete_dimension_template(template_id=template_id)
        
        # 验证结果
        assert result is True
        
        # 验证数据库调用
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_dimension_template_not_found(self, service, mock_db):
        """测试删除不存在的维度模板"""
        # 准备测试数据
        template_id = 999
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试
        result = await service.delete_dimension_template(template_id=template_id)
        
        # 验证结果
        assert result is False


class TestProductDimensionServiceIntegration:
    """ProductDimensionService 集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_dimension_workflow(self):
        """测试完整的维度管理工作流"""
        # 这个测试需要真实的数据库连接
        # 在实际测试环境中运行
        pass

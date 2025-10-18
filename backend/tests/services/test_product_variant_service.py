"""
ProductVariantService 单元测试

测试 SKU 管理的核心功能：
1. SKU CRUD 操作
2. 批量创建 SKU（笛卡尔积）
3. 维度值管理
4. 属性合并逻辑
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.product_variant_service import ProductVariantService
from app.models.product import Product, ProductVariant
from app.models.product_dimension import (
    ProductDimensionTemplate,
    ProductDimensionValue,
    ProductVariantDimension
)
from app.models.product_category import ProductCategory


class TestProductVariantService:
    """ProductVariantService 测试类"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return ProductVariantService(mock_db)
    
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
        variant.cost_price = 15.00
        variant.inventory_quantity = 100
        variant.is_active = True
        return variant
    
    @pytest.fixture
    def sample_dimension_templates(self):
        """示例维度模板数据"""
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
        
        return [color_template, size_template]
    
    @pytest.fixture
    def sample_dimension_values(self):
        """示例维度值数据"""
        red_value = ProductDimensionValue()
        red_value.id = 1
        red_value.value_code = "red"
        red_value.value_name = "红色"
        red_value.value_type = "normal"
        red_value.is_default = False
        
        blue_value = ProductDimensionValue()
        blue_value.id = 2
        blue_value.value_code = "blue"
        blue_value.value_name = "蓝色"
        blue_value.value_type = "normal"
        blue_value.is_default = False
        
        s_value = ProductDimensionValue()
        s_value.id = 3
        s_value.value_code = "S"
        s_value.value_name = "小号"
        s_value.value_type = "normal"
        s_value.is_default = False
        
        m_value = ProductDimensionValue()
        m_value.id = 4
        m_value.value_code = "M"
        m_value.value_name = "中号"
        m_value.value_type = "normal"
        m_value.is_default = False
        
        return [red_value, blue_value, s_value, m_value]

    @pytest.mark.asyncio
    async def test_create_variant_success(self, service, mock_db, sample_product, sample_variant):
        """测试成功创建 SKU"""
        # 准备测试数据
        product_id = 1
        sku_data = {
            "sku": "BASIC-TSHIRT-RED-S",
            "name": "基础 T 恤 红色 小号",
            "price": 29.99,
            "cost_price": 15.00,
            "inventory_quantity": 100
        }
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_product
        mock_db.execute.return_value.scalar.return_value = sample_variant.id
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # 执行测试
        result = await service.create_variant(
            product_id=product_id,
            **sku_data
        )
        
        # 验证结果
        assert result is not None
        assert result.sku == sku_data["sku"]
        assert result.name == sku_data["name"]
        assert result.price == sku_data["price"]
        assert result.cost_price == sku_data["cost_price"]
        assert result.inventory_quantity == sku_data["inventory_quantity"]
        
        # 验证数据库调用
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_variant_product_not_found(self, service, mock_db):
        """测试为不存在的产品创建 SKU"""
        # 准备测试数据
        product_id = 999
        sku_data = {
            "sku": "BASIC-TSHIRT-RED-S",
            "name": "基础 T 恤 红色 小号"
        }
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="产品不存在"):
            await service.create_variant(
                product_id=product_id,
                **sku_data
            )

    @pytest.mark.asyncio
    async def test_create_variant_duplicate_sku(self, service, mock_db, sample_product):
        """测试创建重复 SKU 编码的 SKU"""
        # 准备测试数据
        product_id = 1
        sku_data = {
            "sku": "BASIC-TSHIRT-RED-S",
            "name": "基础 T 恤 红色 小号"
        }
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_product
        # 第二次查询返回已存在的 SKU
        mock_db.execute.return_value.scalar_one_or_none.side_effect = [sample_product, ProductVariant()]
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="SKU 编码已存在"):
            await service.create_variant(
                product_id=product_id,
                **sku_data
            )

    @pytest.mark.asyncio
    async def test_batch_create_variants_success(self, service, mock_db, sample_product):
        """测试成功批量创建 SKU"""
        # 准备测试数据
        product_id = 1
        dimension_combinations = [
            {"color": "red", "size": "S"},
            {"color": "red", "size": "M"},
            {"color": "blue", "size": "S"},
            {"color": "blue", "size": "M"}
        ]
        base_data = {
            "price": 29.99,
            "cost_price": 15.00,
            "inventory_quantity": 100
        }
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_product
        mock_db.execute.return_value.scalar.return_value = 1  # 新 SKU ID
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # 执行测试
        result = await service.batch_create_variants(
            product_id=product_id,
            dimension_combinations=dimension_combinations,
            **base_data
        )
        
        # 验证结果
        assert result is not None
        assert len(result) == 4
        
        # 验证每个 SKU 的创建
        for i, variant in enumerate(result):
            assert variant.product_id == product_id
            assert variant.price == base_data["price"]
            assert variant.cost_price == base_data["cost_price"]
            assert variant.inventory_quantity == base_data["inventory_quantity"]
        
        # 验证数据库调用
        assert mock_db.add.call_count == 4
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_cartesian_combinations(self, service):
        """测试生成笛卡尔积组合"""
        # 准备测试数据
        dimension_values = {
            "color": ["red", "blue"],
            "size": ["S", "M", "L"]
        }
        
        # 执行测试
        result = service.generate_cartesian_combinations(dimension_values)
        
        # 验证结果
        assert result is not None
        assert len(result) == 6  # 2 * 3 = 6 种组合
        
        expected_combinations = [
            {"color": "red", "size": "S"},
            {"color": "red", "size": "M"},
            {"color": "red", "size": "L"},
            {"color": "blue", "size": "S"},
            {"color": "blue", "size": "M"},
            {"color": "blue", "size": "L"}
        ]
        
        for combination in expected_combinations:
            assert combination in result

    @pytest.mark.asyncio
    async def test_generate_cartesian_combinations_empty(self, service):
        """测试生成空维度的笛卡尔积组合"""
        # 准备测试数据
        dimension_values = {}
        
        # 执行测试
        result = service.generate_cartesian_combinations(dimension_values)
        
        # 验证结果
        assert result is not None
        assert len(result) == 1  # 空维度时返回一个空组合
        assert result[0] == {}

    @pytest.mark.asyncio
    async def test_generate_cartesian_combinations_single_dimension(self, service):
        """测试生成单维度的笛卡尔积组合"""
        # 准备测试数据
        dimension_values = {
            "color": ["red", "blue"]
        }
        
        # 执行测试
        result = service.generate_cartesian_combinations(dimension_values)
        
        # 验证结果
        assert result is not None
        assert len(result) == 2
        
        expected_combinations = [
            {"color": "red"},
            {"color": "blue"}
        ]
        
        for combination in expected_combinations:
            assert combination in result

    @pytest.mark.asyncio
    async def test_create_variant_with_dimensions_success(self, service, mock_db, sample_product):
        """测试成功创建带维度值的 SKU"""
        # 准备测试数据
        product_id = 1
        sku_data = {
            "sku": "BASIC-TSHIRT-RED-S",
            "name": "基础 T 恤 红色 小号",
            "price": 29.99
        }
        dimension_values = {
            "color": "red",
            "size": "S"
        }
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_product
        mock_db.execute.return_value.scalar.return_value = 1  # 新 SKU ID
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # 执行测试
        result = await service.create_variant_with_dimensions(
            product_id=product_id,
            dimension_values=dimension_values,
            **sku_data
        )
        
        # 验证结果
        assert result is not None
        assert result.sku == sku_data["sku"]
        assert result.name == sku_data["name"]
        assert result.price == sku_data["price"]
        
        # 验证数据库调用
        mock_db.add.assert_called()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_variant_by_id(self, service, mock_db, sample_variant):
        """测试根据ID获取 SKU"""
        # 准备测试数据
        variant_id = 1
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_variant
        
        # 执行测试
        result = await service.get_variant_by_id(variant_id=variant_id)
        
        # 验证结果
        assert result is not None
        assert result.id == variant_id
        assert result.sku == "BASIC-TSHIRT-RED-S"

    @pytest.mark.asyncio
    async def test_get_variant_by_id_not_found(self, service, mock_db):
        """测试获取不存在的 SKU"""
        # 准备测试数据
        variant_id = 999
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试
        result = await service.get_variant_by_id(variant_id=variant_id)
        
        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    async def test_get_variants_by_product_id(self, service, mock_db, sample_variant):
        """测试根据产品ID获取 SKU 列表"""
        # 准备测试数据
        product_id = 1
        variants = [sample_variant]
        
        # 模拟数据库查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = variants
        mock_db.execute.return_value = mock_result
        
        # 执行测试
        result = await service.get_variants_by_product_id(product_id=product_id)
        
        # 验证结果
        assert result is not None
        assert len(result) == 1
        assert result[0].product_id == product_id

    @pytest.mark.asyncio
    async def test_update_variant_success(self, service, mock_db, sample_variant):
        """测试成功更新 SKU"""
        # 准备测试数据
        variant_id = 1
        update_data = {
            "name": "更新后的 SKU 名称",
            "price": 39.99,
            "inventory_quantity": 200
        }
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_variant
        mock_db.commit.return_value = None
        
        # 执行测试
        result = await service.update_variant(
            variant_id=variant_id,
            **update_data
        )
        
        # 验证结果
        assert result is not None
        assert result.name == update_data["name"]
        assert result.price == update_data["price"]
        assert result.inventory_quantity == update_data["inventory_quantity"]
        
        # 验证数据库调用
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_variant_not_found(self, service, mock_db):
        """测试更新不存在的 SKU"""
        # 准备测试数据
        variant_id = 999
        update_data = {"name": "更新后的 SKU 名称"}
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="SKU 不存在"):
            await service.update_variant(
                variant_id=variant_id,
                **update_data
            )

    @pytest.mark.asyncio
    async def test_delete_variant_success(self, service, mock_db):
        """测试成功删除 SKU"""
        # 准备测试数据
        variant_id = 1
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = ProductVariant(id=1)
        mock_db.commit.return_value = None
        
        # 执行测试
        result = await service.delete_variant(variant_id=variant_id)
        
        # 验证结果
        assert result is True
        
        # 验证数据库调用
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_variant_not_found(self, service, mock_db):
        """测试删除不存在的 SKU"""
        # 准备测试数据
        variant_id = 999
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试
        result = await service.delete_variant(variant_id=variant_id)
        
        # 验证结果
        assert result is False

    @pytest.mark.asyncio
    async def test_get_variant_dimensions(self, service, mock_db):
        """测试获取 SKU 的维度值"""
        # 准备测试数据
        variant_id = 1
        dimensions = [
            ProductVariantDimension(
                id=1,
                variant_id=variant_id,
                dimension_template_id=1,
                dimension_value_id=1
            ),
            ProductVariantDimension(
                id=2,
                variant_id=variant_id,
                dimension_template_id=2,
                dimension_value_id=3
            )
        ]
        
        # 模拟数据库查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = dimensions
        mock_db.execute.return_value = mock_result
        
        # 执行测试
        result = await service.get_variant_dimensions(variant_id=variant_id)
        
        # 验证结果
        assert result is not None
        assert len(result) == 2
        assert all(d.variant_id == variant_id for d in result)

    @pytest.mark.asyncio
    async def test_update_variant_dimensions(self, service, mock_db, sample_variant):
        """测试更新 SKU 的维度值"""
        # 准备测试数据
        variant_id = 1
        dimension_values = {
            "color": "blue",
            "size": "M"
        }
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_variant
        mock_db.commit.return_value = None
        
        # 执行测试
        result = await service.update_variant_dimensions(
            variant_id=variant_id,
            dimension_values=dimension_values
        )
        
        # 验证结果
        assert result is True
        
        # 验证数据库调用
        mock_db.commit.assert_called_once()


class TestProductVariantServiceIntegration:
    """ProductVariantService 集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_variant_workflow(self):
        """测试完整的 SKU 管理工作流"""
        # 这个测试需要真实的数据库连接
        # 在实际测试环境中运行
        pass

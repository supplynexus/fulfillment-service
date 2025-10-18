"""
ProductCategoryService 单元测试

测试产品分类管理的核心功能：
1. 分类 CRUD 操作
2. DAG 结构管理
3. 循环检测
4. 分类树检索
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.product_category_service import ProductCategoryService
from app.models.product_category import (
    ProductCategory,
    ProductCategoryRelation,
    ProductCategoryDimension,
    ProductCategoryAssignment
)


class TestProductCategoryService:
    """ProductCategoryService 测试类"""
    
    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock(spec=AsyncSession)
    
    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return ProductCategoryService(mock_db)
    
    @pytest.fixture
    def sample_category(self):
        """示例分类数据"""
        category = ProductCategory()
        category.id = 1
        category.tenant_id = 1
        category.category_code = "electronics"
        category.category_name = "电子产品"
        category.description = "各类电子设备"
        category.is_root = False
        category.is_active = True
        return category
    
    @pytest.fixture
    def sample_relation(self):
        """示例分类关系数据"""
        relation = ProductCategoryRelation()
        relation.id = 1
        relation.parent_category_id = 1
        relation.child_category_id = 2
        relation.relation_type = "parent_child"
        return relation

    @pytest.mark.asyncio
    async def test_create_category_success(self, service, mock_db, sample_category):
        """测试成功创建分类"""
        # 准备测试数据
        category_data = {
            "category_code": "electronics",
            "category_name": "电子产品",
            "description": "各类电子设备",
            "is_root": False
        }
        
        # 模拟数据库查询结果
        # 第一次查询：检查编码是否重复（返回None表示不重复）
        # 第二次查询：获取新分类ID
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None  # 编码不重复
        mock_result.scalar.return_value = sample_category.id  # 新分类ID
        mock_db.execute.return_value = mock_result
        mock_db.flush.return_value = None
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # 执行测试
        result = await service.create_category(
            tenant_id=1,
            **category_data
        )
        
        # 验证结果
        assert result is not None
        assert result.category_code == category_data["category_code"]
        assert result.category_name == category_data["category_name"]
        assert result.description == category_data["description"]
        assert result.is_root == category_data["is_root"]
        
        # 验证数据库调用
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_category_duplicate_code(self, service, mock_db):
        """测试创建重复编码的分类"""
        # 准备测试数据
        category_data = {
            "category_code": "electronics",
            "category_name": "电子产品"
        }
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = ProductCategory()  # 编码已存在
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="分类编码已存在"):
            await service.create_category(
                tenant_id=1,
                **category_data
            )

    @pytest.mark.asyncio
    async def test_get_category_by_id(self, service, mock_db, sample_category):
        """测试根据ID获取分类"""
        # 准备测试数据
        category_id = 1
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_category
        
        # 执行测试
        result = await service.get_category_by_id(category_id=category_id)
        
        # 验证结果
        assert result is not None
        assert result.id == category_id
        assert result.category_code == "electronics"

    @pytest.mark.asyncio
    async def test_get_category_by_id_not_found(self, service, mock_db):
        """测试获取不存在的分类"""
        # 准备测试数据
        category_id = 999
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试
        result = await service.get_category_by_id(category_id=category_id)
        
        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    async def test_get_categories_by_tenant(self, service, mock_db, sample_category):
        """测试根据租户获取分类列表"""
        # 准备测试数据
        tenant_id = 1
        categories = [sample_category]
        
        # 模拟数据库查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = categories
        mock_db.execute.return_value = mock_result
        
        # 执行测试
        result = await service.get_categories_by_tenant(tenant_id=tenant_id)
        
        # 验证结果
        assert result is not None
        assert len(result) == 1
        assert result[0].tenant_id == tenant_id

    @pytest.mark.asyncio
    async def test_update_category_success(self, service, mock_db, sample_category):
        """测试成功更新分类"""
        # 准备测试数据
        category_id = 1
        update_data = {
            "category_name": "更新后的电子产品",
            "description": "更新后的描述"
        }
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = sample_category
        mock_db.commit.return_value = None
        
        # 执行测试
        result = await service.update_category(
            category_id=category_id,
            **update_data
        )
        
        # 验证结果
        assert result is not None
        assert result.category_name == update_data["category_name"]
        assert result.description == update_data["description"]
        
        # 验证数据库调用
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_category_not_found(self, service, mock_db):
        """测试更新不存在的分类"""
        # 准备测试数据
        category_id = 999
        update_data = {"category_name": "更新后的名称"}
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="分类不存在"):
            await service.update_category(
                category_id=category_id,
                **update_data
            )

    @pytest.mark.asyncio
    async def test_delete_category_success(self, service, mock_db):
        """测试成功删除分类"""
        # 准备测试数据
        category_id = 1
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = ProductCategory(id=1)
        mock_db.commit.return_value = None
        
        # 执行测试
        result = await service.delete_category(category_id=category_id)
        
        # 验证结果
        assert result is True
        
        # 验证数据库调用
        mock_db.delete.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_category_not_found(self, service, mock_db):
        """测试删除不存在的分类"""
        # 准备测试数据
        category_id = 999
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None
        
        # 执行测试
        result = await service.delete_category(category_id=category_id)
        
        # 验证结果
        assert result is False

    @pytest.mark.asyncio
    async def test_create_category_relation_success(self, service, mock_db, sample_relation):
        """测试成功创建分类关系"""
        # 准备测试数据
        parent_category_id = 1
        child_category_id = 2
        relation_type = "parent_child"
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None  # 关系不存在
        mock_db.execute.return_value.scalar.return_value = sample_relation.id
        mock_db.commit.return_value = None
        mock_db.refresh.return_value = None
        
        # 执行测试
        result = await service.create_category_relation(
            parent_category_id=parent_category_id,
            child_category_id=child_category_id,
            relation_type=relation_type
        )
        
        # 验证结果
        assert result is not None
        assert result.parent_category_id == parent_category_id
        assert result.child_category_id == child_category_id
        assert result.relation_type == relation_type
        
        # 验证数据库调用
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_category_relation_duplicate(self, service, mock_db):
        """测试创建重复的分类关系"""
        # 准备测试数据
        parent_category_id = 1
        child_category_id = 2
        relation_type = "parent_child"
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = ProductCategoryRelation()  # 关系已存在
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="分类关系已存在"):
            await service.create_category_relation(
                parent_category_id=parent_category_id,
                child_category_id=child_category_id,
                relation_type=relation_type
            )

    @pytest.mark.asyncio
    async def test_create_category_relation_self_reference(self, service, mock_db):
        """测试创建自引用的分类关系"""
        # 准备测试数据
        parent_category_id = 1
        child_category_id = 1  # 相同ID
        relation_type = "parent_child"
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="不能创建自引用关系"):
            await service.create_category_relation(
                parent_category_id=parent_category_id,
                child_category_id=child_category_id,
                relation_type=relation_type
            )

    @pytest.mark.asyncio
    async def test_detect_cycle_success(self, service, mock_db):
        """测试成功检测循环"""
        # 准备测试数据
        parent_category_id = 1
        child_category_id = 2
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = None  # 无循环
        
        # 执行测试
        result = await service.detect_cycle(
            parent_category_id=parent_category_id,
            child_category_id=child_category_id
        )
        
        # 验证结果
        assert result is False

    @pytest.mark.asyncio
    async def test_detect_cycle_found(self, service, mock_db):
        """测试检测到循环"""
        # 准备测试数据
        parent_category_id = 1
        child_category_id = 2
        
        # 模拟数据库查询结果
        mock_db.execute.return_value.scalar_one_or_none.return_value = ProductCategoryRelation()  # 存在循环
        
        # 执行测试
        result = await service.detect_cycle(
            parent_category_id=parent_category_id,
            child_category_id=child_category_id
        )
        
        # 验证结果
        assert result is True

    @pytest.mark.asyncio
    async def test_get_category_tree(self, service, mock_db):
        """测试获取分类树"""
        # 准备测试数据
        tenant_id = 1
        
        # 模拟数据库查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # 执行测试
        result = await service.get_category_tree(tenant_id=tenant_id)
        
        # 验证结果
        assert result is not None
        assert "categories" in result
        assert "relations" in result
        assert "tree_structure" in result

    @pytest.mark.asyncio
    async def test_get_category_children(self, service, mock_db):
        """测试获取分类子节点"""
        # 准备测试数据
        category_id = 1
        
        # 模拟数据库查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # 执行测试
        result = await service.get_category_children(category_id=category_id)
        
        # 验证结果
        assert result is not None
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_category_parents(self, service, mock_db):
        """测试获取分类父节点"""
        # 准备测试数据
        category_id = 1
        
        # 模拟数据库查询结果
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        
        # 执行测试
        result = await service.get_category_parents(category_id=category_id)
        
        # 验证结果
        assert result is not None
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_validate_category_data(self, service):
        """测试验证分类数据"""
        # 准备测试数据
        valid_data = {
            "category_code": "electronics",
            "category_name": "电子产品",
            "description": "各类电子设备"
        }
        
        # 执行测试
        result = service.validate_category_data(valid_data)
        
        # 验证结果
        assert result is True

    @pytest.mark.asyncio
    async def test_validate_category_data_invalid(self, service):
        """测试验证无效的分类数据"""
        # 准备测试数据
        invalid_data = {
            "category_code": "",  # 空编码
            "category_name": "电子产品"
        }
        
        # 执行测试并验证异常
        with pytest.raises(ValueError, match="分类编码不能为空"):
            service.validate_category_data(invalid_data)


class TestProductCategoryServiceIntegration:
    """ProductCategoryService 集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_category_workflow(self):
        """测试完整的分类管理工作流"""
        # 这个测试需要真实的数据库连接
        # 在实际测试环境中运行
        pass
"""
产品分类服务单元测试

测试 ProductCategoryService 的核心业务逻辑
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.services.product_category_service import ProductCategoryService
from app.models.product_category import ProductCategory
from app.schemas.product_category import ProductCategoryCreate, ProductCategoryUpdate


class TestProductCategoryService:
    """产品分类服务单元测试"""

    @pytest.fixture
    def mock_db(self):
        """模拟数据库会话"""
        return AsyncMock(spec=AsyncSession)

    @pytest.fixture
    def service(self, mock_db):
        """创建服务实例"""
        return ProductCategoryService(mock_db)

    @pytest.mark.asyncio
    async def test_create_category_success(self, service, mock_db):
        """测试成功创建分类"""
        # 准备测试数据
        category_data = ProductCategoryCreate(
            name="电子产品",
            code="electronics",
            description="电子设备及相关产品",
            is_active=True
        )
        tenant_id = 1

        # 模拟数据库操作
        mock_category = ProductCategory(
            id=1,
            name=category_data.name,
            code=category_data.code,
            description=category_data.description,
            is_active=category_data.is_active,
            tenant_id=tenant_id
        )
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()
        mock_db.refresh.side_effect = lambda obj: setattr(obj, 'id', 1)

        # 执行测试
        result = await service.create_category(category_data, tenant_id)

        # 验证结果
        assert result.name == category_data.name
        assert result.code == category_data.code
        assert result.description == category_data.description
        assert result.is_active == category_data.is_active
        assert result.tenant_id == tenant_id

        # 验证数据库操作
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_category_duplicate_code(self, service, mock_db):
        """测试创建重复代码的分类"""
        # 准备测试数据
        category_data = ProductCategoryCreate(
            name="电子产品",
            code="electronics",
            description="电子设备及相关产品",
            is_active=True
        )
        tenant_id = 1

        # 模拟数据库完整性错误
        mock_db.add = MagicMock()
        mock_db.commit = AsyncMock(side_effect=IntegrityError("", "", ""))
        mock_db.rollback = AsyncMock()

        # 执行测试并验证异常
        with pytest.raises(ValueError, match="分类代码已存在"):
            await service.create_category(category_data, tenant_id)

        # 验证回滚操作
        mock_db.rollback.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_category_by_id_success(self, service, mock_db):
        """测试成功获取分类"""
        # 准备测试数据
        category_id = 1
        tenant_id = 1

        # 模拟数据库查询
        mock_category = ProductCategory(
            id=category_id,
            name="电子产品",
            code="electronics",
            description="电子设备及相关产品",
            is_active=True,
            tenant_id=tenant_id
        )
        mock_db.get = AsyncMock(return_value=mock_category)

        # 执行测试
        result = await service.get_category_by_id(category_id, tenant_id)

        # 验证结果
        assert result is not None
        assert result.id == category_id
        assert result.name == "电子产品"
        assert result.tenant_id == tenant_id

        # 验证数据库查询
        mock_db.get.assert_called_once_with(ProductCategory, category_id)

    @pytest.mark.asyncio
    async def test_get_category_by_id_not_found(self, service, mock_db):
        """测试获取不存在的分类"""
        # 准备测试数据
        category_id = 999
        tenant_id = 1

        # 模拟数据库查询返回None
        mock_db.get = AsyncMock(return_value=None)

        # 执行测试
        result = await service.get_category_by_id(category_id, tenant_id)

        # 验证结果
        assert result is None

    @pytest.mark.asyncio
    async def test_update_category_success(self, service, mock_db):
        """测试成功更新分类"""
        # 准备测试数据
        category_id = 1
        tenant_id = 1
        update_data = ProductCategoryUpdate(
            name="更新后的电子产品",
            description="更新后的描述"
        )

        # 模拟现有分类
        existing_category = ProductCategory(
            id=category_id,
            name="电子产品",
            code="electronics",
            description="电子设备及相关产品",
            is_active=True,
            tenant_id=tenant_id
        )

        # 模拟数据库操作
        mock_db.get = AsyncMock(return_value=existing_category)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        # 执行测试
        result = await service.update_category(category_id, update_data, tenant_id)

        # 验证结果
        assert result.name == update_data.name
        assert result.description == update_data.description
        assert result.code == "electronics"  # 未更新的字段保持不变

        # 验证数据库操作
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_category_success(self, service, mock_db):
        """测试成功删除分类"""
        # 准备测试数据
        category_id = 1
        tenant_id = 1

        # 模拟现有分类
        existing_category = ProductCategory(
            id=category_id,
            name="电子产品",
            code="electronics",
            tenant_id=tenant_id
        )

        # 模拟数据库操作
        mock_db.get = AsyncMock(return_value=existing_category)
        mock_db.delete = MagicMock()
        mock_db.commit = AsyncMock()

        # 执行测试
        result = await service.delete_category(category_id, tenant_id)

        # 验证结果
        assert result is True

        # 验证数据库操作
        mock_db.delete.assert_called_once_with(existing_category)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_category_not_found(self, service, mock_db):
        """测试删除不存在的分类"""
        # 准备测试数据
        category_id = 999
        tenant_id = 1

        # 模拟数据库查询返回None
        mock_db.get = AsyncMock(return_value=None)

        # 执行测试
        result = await service.delete_category(category_id, tenant_id)

        # 验证结果
        assert result is False

        # 验证没有执行删除操作
        mock_db.delete.assert_not_called()
        mock_db.commit.assert_not_called()

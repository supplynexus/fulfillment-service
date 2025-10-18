"""
产品分类 API 端点单元测试

测试产品分类 API 端点的请求处理逻辑
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import app
from app.models.product_category import ProductCategory
from app.schemas.product_category import ProductCategoryCreate, ProductCategoryUpdate
from app.core.jwt_utils import jwt_utils


class TestProductCategoriesAPI:
    """产品分类 API 端点单元测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def mock_tenant(self):
        """模拟租户"""
        return MagicMock(id=1, name="test-tenant")

    @pytest.fixture
    def mock_user(self):
        """模拟用户"""
        return MagicMock(id=1, email="test@example.com")

    @pytest.fixture
    def mock_category(self):
        """模拟分类"""
        return ProductCategory(
            id=1,
            name="电子产品",
            code="electronics",
            description="电子设备及相关产品",
            is_active=True,
            tenant_id=1
        )

    @pytest.fixture
    def valid_token(self):
        """生成有效JWT token"""
        return jwt_utils.generate_token(
            user_id=1,
            tenant_id=1,
            tenant_name="test-tenant"
        )

    def test_get_categories_success(self, client, valid_token):
        """测试成功获取分类列表"""
        with patch('app.api.v1.endpoints.product_categories.ProductCategoryService') as mock_service:
            # 模拟服务返回
            mock_service_instance = AsyncMock()
            mock_service_instance.get_categories.return_value = [
                ProductCategory(
                    id=1,
                    name="电子产品",
                    code="electronics",
                    description="电子设备及相关产品",
                    is_active=True,
                    tenant_id=1
                )
            ]
            mock_service.return_value = mock_service_instance

            # 执行请求
            response = client.get(
                "/api/v1/product-categories/",
                headers={"Authorization": f"Bearer {valid_token}"}
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]["name"] == "电子产品"
            assert data[0]["code"] == "electronics"

    def test_get_categories_unauthorized(self, client):
        """测试未授权访问"""
        response = client.get("/api/v1/product-categories/")
        assert response.status_code == 401

    def test_create_category_success(self, client, valid_token):
        """测试成功创建分类"""
        with patch('app.api.v1.endpoints.product_categories.ProductCategoryService') as mock_service:
            # 模拟服务返回
            mock_service_instance = AsyncMock()
            mock_category = ProductCategory(
                id=1,
                name="新分类",
                code="new-category",
                description="新分类描述",
                is_active=True,
                tenant_id=1
            )
            mock_service_instance.create_category.return_value = mock_category
            mock_service.return_value = mock_service_instance

            # 准备请求数据
            category_data = {
                "name": "新分类",
                "code": "new-category",
                "description": "新分类描述",
                "is_active": True
            }

            # 执行请求
            response = client.post(
                "/api/v1/product-categories/",
                json=category_data,
                headers={"Authorization": f"Bearer {valid_token}"}
            )

            # 验证响应
            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "新分类"
            assert data["code"] == "new-category"

    def test_create_category_validation_error(self, client, valid_token):
        """测试创建分类验证错误"""
        # 准备无效数据（缺少必填字段）
        category_data = {
            "code": "new-category",
            "description": "新分类描述"
            # 缺少 name 字段
        }

        # 执行请求
        response = client.post(
            "/api/v1/product-categories/",
            json=category_data,
            headers={"Authorization": f"Bearer {valid_token}"}
        )

        # 验证响应
        assert response.status_code == 422

    def test_create_category_duplicate_code(self, client, valid_token):
        """测试创建重复代码的分类"""
        with patch('app.api.v1.endpoints.product_categories.ProductCategoryService') as mock_service:
            # 模拟服务抛出重复代码异常
            mock_service_instance = AsyncMock()
            mock_service_instance.create_category.side_effect = ValueError("分类代码已存在")
            mock_service.return_value = mock_service_instance

            # 准备请求数据
            category_data = {
                "name": "新分类",
                "code": "electronics",  # 重复的代码
                "description": "新分类描述",
                "is_active": True
            }

            # 执行请求
            response = client.post(
                "/api/v1/product-categories/",
                json=category_data,
                headers={"Authorization": f"Bearer {valid_token}"}
            )

            # 验证响应
            assert response.status_code == 400
            data = response.json()
            assert "分类代码已存在" in data["detail"]

    def test_get_category_by_id_success(self, client, valid_token, mock_category):
        """测试成功获取单个分类"""
        with patch('app.api.v1.endpoints.product_categories.ProductCategoryService') as mock_service:
            # 模拟服务返回
            mock_service_instance = AsyncMock()
            mock_service_instance.get_category_by_id.return_value = mock_category
            mock_service.return_value = mock_service_instance

            # 执行请求
            response = client.get(
                "/api/v1/product-categories/1",
                headers={"Authorization": f"Bearer {valid_token}"}
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == 1
            assert data["name"] == "电子产品"

    def test_get_category_by_id_not_found(self, client, valid_token):
        """测试获取不存在的分类"""
        with patch('app.api.v1.endpoints.product_categories.ProductCategoryService') as mock_service:
            # 模拟服务返回None
            mock_service_instance = AsyncMock()
            mock_service_instance.get_category_by_id.return_value = None
            mock_service.return_value = mock_service_instance

            # 执行请求
            response = client.get(
                "/api/v1/product-categories/999",
                headers={"Authorization": f"Bearer {valid_token}"}
            )

            # 验证响应
            assert response.status_code == 404
            data = response.json()
            assert "Product category not found" in data["detail"]

    def test_update_category_success(self, client, valid_token, mock_category):
        """测试成功更新分类"""
        with patch('app.api.v1.endpoints.product_categories.ProductCategoryService') as mock_service:
            # 模拟服务返回
            mock_service_instance = AsyncMock()
            updated_category = ProductCategory(
                id=1,
                name="更新后的电子产品",
                code="electronics",
                description="更新后的描述",
                is_active=True,
                tenant_id=1
            )
            mock_service_instance.update_category.return_value = updated_category
            mock_service.return_value = mock_service_instance

            # 准备请求数据
            update_data = {
                "name": "更新后的电子产品",
                "description": "更新后的描述"
            }

            # 执行请求
            response = client.put(
                "/api/v1/product-categories/1",
                json=update_data,
                headers={"Authorization": f"Bearer {valid_token}"}
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["name"] == "更新后的电子产品"
            assert data["description"] == "更新后的描述"

    def test_delete_category_success(self, client, valid_token):
        """测试成功删除分类"""
        with patch('app.api.v1.endpoints.product_categories.ProductCategoryService') as mock_service:
            # 模拟服务返回
            mock_service_instance = AsyncMock()
            mock_service_instance.delete_category.return_value = True
            mock_service.return_value = mock_service_instance

            # 执行请求
            response = client.delete(
                "/api/v1/product-categories/1",
                headers={"Authorization": f"Bearer {valid_token}"}
            )

            # 验证响应
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Product category deleted successfully"

    def test_delete_category_not_found(self, client, valid_token):
        """测试删除不存在的分类"""
        with patch('app.api.v1.endpoints.product_categories.ProductCategoryService') as mock_service:
            # 模拟服务返回False
            mock_service_instance = AsyncMock()
            mock_service_instance.delete_category.return_value = False
            mock_service.return_value = mock_service_instance

            # 执行请求
            response = client.delete(
                "/api/v1/product-categories/999",
                headers={"Authorization": f"Bearer {valid_token}"}
            )

            # 验证响应
            assert response.status_code == 404
            data = response.json()
            assert "Product category not found" in data["detail"]

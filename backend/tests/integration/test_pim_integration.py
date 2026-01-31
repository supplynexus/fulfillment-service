"""
PIM 系统集成测试

测试产品信息管理系统的完整流程：
1. 产品分类管理
2. 维度模板管理
3. SKU 管理
4. 前后端数据一致性
"""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_async_db
from app.models.product_category import ProductCategory
from app.models.product_dimension import ProductDimensionTemplate
from app.models.product_variant import ProductVariant
from app.core.jwt_utils import jwt_utils


class TestPIMIntegration:
    """PIM 系统集成测试"""

    @pytest.fixture
    def client(self):
        """创建测试客户端"""
        return TestClient(app)

    @pytest.fixture
    def valid_token(self):
        """生成有效JWT token"""
        return jwt_utils.generate_token(
            user_id=1,
            tenant_id=1,
            tenant_name="test-tenant"
        )

    @pytest.fixture
    async def db_session(self):
        """获取数据库会话"""
        async for session in get_async_db():
            yield session

    def test_complete_pim_workflow(self, client, valid_token, db_session):
        """测试完整的PIM工作流程"""
        
        # 1. 创建产品分类
        category_data = {
            "name": "测试分类",
            "code": "test-category",
            "description": "测试分类描述",
            "is_active": True
        }
        
        response = client.post(
            "/api/v1/product-categories/",
            json=category_data,
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 201
        category = response.json()
        category_id = category["id"]
        
        # 2. 创建维度模板
        dimension_data = {
            "dimension_code": "color",
            "dimension_name": "颜色",
            "dimension_type": "select",
            "description": "产品颜色维度",
            "is_active": True
        }
        
        response = client.post(
            "/api/v1/dimension-templates/",
            json=dimension_data,
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 201
        dimension = response.json()
        dimension_id = dimension["id"]
        
        # 3. 为维度模板添加值
        dimension_values = [
            {"value": "红色", "display_name": "红色", "sort_order": 1},
            {"value": "蓝色", "display_name": "蓝色", "sort_order": 2},
            {"value": "绿色", "display_name": "绿色", "sort_order": 3}
        ]
        
        response = client.post(
            f"/api/v1/dimension-templates/{dimension_id}/values",
            json={"values": dimension_values},
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 201
        
        # 4. 创建产品变体（SKU）
        sku_data = {
            "sku": "TEST-SKU-001",
            "name": "测试产品 - 红色",
            "product_id": 1,  # 假设产品ID为1
            "attributes": {"color": "红色", "size": "L"},
            "price": 29.99,
            "cost": 15.00,
            "stock": 100,
            "is_active": True
        }
        
        response = client.post(
            "/api/v1/product-variants/",
            json=sku_data,
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 201
        sku = response.json()
        sku_id = sku["id"]
        
        # 5. 验证数据一致性
        # 获取分类列表
        response = client.get(
            "/api/v1/product-categories/",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        categories = response.json()
        assert len(categories) >= 1
        assert any(cat["id"] == category_id for cat in categories)
        
        # 获取维度模板列表
        response = client.get(
            "/api/v1/dimension-templates/",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        dimensions = response.json()
        assert len(dimensions) >= 1
        assert any(dim["id"] == dimension_id for dim in dimensions)
        
        # 获取SKU列表
        response = client.get(
            "/api/v1/product-variants/",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        skus = response.json()
        assert len(skus) >= 1
        assert any(sku["id"] == sku_id for sku in skus)
        
        # 6. 测试更新操作
        # 更新分类
        updated_category_data = {
            "name": "更新后的测试分类",
            "description": "更新后的描述"
        }
        
        response = client.put(
            f"/api/v1/product-categories/{category_id}",
            json=updated_category_data,
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        
        # 更新SKU
        updated_sku_data = {
            "name": "更新后的测试产品",
            "price": 39.99,
            "stock": 150
        }
        
        response = client.put(
            f"/api/v1/product-variants/{sku_id}",
            json=updated_sku_data,
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        
        # 7. 测试删除操作
        # 删除SKU
        response = client.delete(
            f"/api/v1/product-variants/{sku_id}",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        
        # 删除维度模板
        response = client.delete(
            f"/api/v1/dimension-templates/{dimension_id}",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200
        
        # 删除分类
        response = client.delete(
            f"/api/v1/product-categories/{category_id}",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 200

    def test_data_validation_and_error_handling(self, client, valid_token):
        """测试数据验证和错误处理"""
        
        # 测试创建分类时的验证错误
        invalid_category_data = {
            "code": "test-category"
            # 缺少必填字段 name
        }
        
        response = client.post(
            "/api/v1/product-categories/",
            json=invalid_category_data,
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 422
        
        # 测试创建SKU时的验证错误
        invalid_sku_data = {
            "name": "测试产品"
            # 缺少必填字段 sku
        }
        
        response = client.post(
            "/api/v1/product-variants/",
            json=invalid_sku_data,
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 422
        
        # 测试访问不存在的资源
        response = client.get(
            "/api/v1/product-categories/999",
            headers={"Authorization": f"Bearer {valid_token}"}
        )
        assert response.status_code == 404
        
        # 测试未授权访问
        response = client.get("/api/v1/product-categories/")
        assert response.status_code == 401

    def test_bulk_operations(self, client, valid_token):
        """测试批量操作"""
        
        # 批量创建SKU
        sku_batch = [
            {
                "sku": "BATCH-001",
                "name": "批量产品1",
                "product_id": 1,
                "attributes": {"color": "红色"},
                "price": 29.99,
                "cost": 15.00,
                "stock": 100,
                "is_active": True
            },
            {
                "sku": "BATCH-002",
                "name": "批量产品2",
                "product_id": 1,
                "attributes": {"color": "蓝色"},
                "price": 39.99,
                "cost": 20.00,
                "stock": 50,
                "is_active": True
            }
        ]
        
        created_skus = []
        for sku_data in sku_batch:
            response = client.post(
                "/api/v1/product-variants/",
                json=sku_data,
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            assert response.status_code == 201
            created_skus.append(response.json())
        
        # 验证批量创建的结果
        assert len(created_skus) == 2
        assert created_skus[0]["sku"] == "BATCH-001"
        assert created_skus[1]["sku"] == "BATCH-002"
        
        # 清理测试数据
        for sku in created_skus:
            response = client.delete(
                f"/api/v1/product-variants/{sku['id']}",
                headers={"Authorization": f"Bearer {valid_token}"}
            )
            assert response.status_code == 200

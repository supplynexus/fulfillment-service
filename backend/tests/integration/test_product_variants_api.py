"""
产品 SKU 管理 API 集成测试

测试 SKU 管理的完整 API 流程：
1. SKU CRUD 操作
2. 批量创建 SKU
3. 笛卡尔积生成
4. 维度值管理
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_async_db
from app.models.product import Product, ProductVariant
from app.models.product_category import ProductCategory
from app.models.product_dimension import ProductDimensionTemplate, ProductDimensionValue
from app.core.jwt_utils import jwt_utils


class TestProductVariantsAPI:
    """产品 SKU 管理 API 集成测试"""
    
    @pytest.fixture
    async def client(self):
        """创建测试客户端"""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac
    
    @pytest.fixture
    def auth_headers(self):
        """创建认证头"""
        token = jwt_utils.generate_access_token(
            user_id=1,
            tenant_id=1,
            email="test_user@example.com",
            tenant_name="test_tenant"
        )
        return {"Authorization": f"Bearer {token}"}
    
    @pytest.fixture
    async def sample_tenant(self, db: AsyncSession):
        """创建示例租户"""
        from app.models.tenant import Tenant
        tenant = Tenant(
            name="test_tenant",
            domain="test.com",
            is_active=True
        )
        db.add(tenant)
        await db.commit()
        await db.refresh(tenant)
        return tenant
    
    @pytest.fixture
    async def sample_product(self, db: AsyncSession, sample_tenant):
        """创建示例产品"""
        product = Product(
            tenant_id=sample_tenant.id,
            name="基础 T 恤",
            handle="basic-tshirt",
            description="经典基础款 T 恤",
            is_active=True
        )
        db.add(product)
        await db.commit()
        await db.refresh(product)
        return product
    
    @pytest.fixture
    async def sample_variant(self, db: AsyncSession, sample_product):
        """创建示例 SKU"""
        variant = ProductVariant(
            product_id=sample_product.id,
            sku="BASIC-TSHIRT-RED-S",
            name="基础 T 恤 红色 小号",
            price=29.99,
            cost_price=15.00,
            inventory_quantity=100,
            is_active=True
        )
        db.add(variant)
        await db.commit()
        await db.refresh(variant)
        return variant
    
    @pytest.fixture
    async def sample_category(self, db: AsyncSession, sample_tenant):
        """创建示例分类"""
        category = ProductCategory(
            tenant_id=sample_tenant.id,
            category_code="clothing",
            category_name="服装",
            description="各类服装产品",
            is_root=True
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category
    
    @pytest.fixture
    async def sample_dimension_templates(self, db: AsyncSession, sample_tenant):
        """创建示例维度模板"""
        color_template = ProductDimensionTemplate(
            tenant_id=sample_tenant.id,
            dimension_code="color",
            dimension_name="颜色",
            dimension_type="select",
            description="产品颜色维度"
        )
        size_template = ProductDimensionTemplate(
            tenant_id=sample_tenant.id,
            dimension_code="size",
            dimension_name="尺码",
            dimension_type="select",
            description="产品尺码维度"
        )
        
        db.add(color_template)
        db.add(size_template)
        await db.commit()
        await db.refresh(color_template)
        await db.refresh(size_template)
        
        return [color_template, size_template]

    @pytest.mark.asyncio
    async def test_create_variant_success(self, client: AsyncClient, auth_headers: dict, sample_product):
        """测试成功创建 SKU"""
        variant_data = {
            "sku": "BASIC-TSHIRT-BLUE-M",
            "name": "基础 T 恤 蓝色 中号",
            "price": 29.99,
            "cost_price": 15.00,
            "inventory_quantity": 100,
            "is_active": True
        }
        
        response = await client.post(
            f"/api/v1/products/{sample_product.id}/variants",
            json=variant_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == variant_data["sku"]
        assert data["name"] == variant_data["name"]
        assert data["price"] == variant_data["price"]
        assert data["cost_price"] == variant_data["cost_price"]
        assert data["inventory_quantity"] == variant_data["inventory_quantity"]

    @pytest.mark.asyncio
    async def test_create_variant_duplicate_sku(self, client: AsyncClient, auth_headers: dict, sample_product, sample_variant):
        """测试创建重复 SKU 编码的 SKU"""
        variant_data = {
            "sku": "BASIC-TSHIRT-RED-S",  # 重复 SKU
            "name": "基础 T 恤 红色 小号2",
            "price": 29.99
        }
        
        response = await client.post(
            f"/api/v1/products/{sample_product.id}/variants",
            json=variant_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "SKU 编码已存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_create_variant_product_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试为不存在的产品创建 SKU"""
        variant_data = {
            "sku": "TEST-SKU",
            "name": "测试 SKU",
            "price": 29.99
        }
        
        response = await client.post(
            "/api/v1/products/999/variants",
            json=variant_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "产品不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_variant_by_id(self, client: AsyncClient, auth_headers: dict, sample_variant):
        """测试根据ID获取 SKU"""
        response = await client.get(
            f"/api/v1/product-variants/{sample_variant.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_variant.id
        assert data["sku"] == sample_variant.sku
        assert data["name"] == sample_variant.name

    @pytest.mark.asyncio
    async def test_get_variant_by_id_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试获取不存在的 SKU"""
        response = await client.get(
            "/api/v1/product-variants/999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "SKU 不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_variants_by_product_id(self, client: AsyncClient, auth_headers: dict, sample_product, sample_variant):
        """测试根据产品ID获取 SKU 列表"""
        response = await client.get(
            f"/api/v1/products/{sample_product.id}/variants",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_update_variant_success(self, client: AsyncClient, auth_headers: dict, sample_variant):
        """测试成功更新 SKU"""
        update_data = {
            "name": "更新后的 SKU 名称",
            "price": 39.99,
            "inventory_quantity": 200
        }
        
        response = await client.put(
            f"/api/v1/product-variants/{sample_variant.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == update_data["name"]
        assert data["price"] == update_data["price"]
        assert data["inventory_quantity"] == update_data["inventory_quantity"]

    @pytest.mark.asyncio
    async def test_update_variant_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试更新不存在的 SKU"""
        update_data = {"name": "更新后的名称"}
        
        response = await client.put(
            "/api/v1/product-variants/999",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "SKU 不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_delete_variant_success(self, client: AsyncClient, auth_headers: dict, sample_variant):
        """测试成功删除 SKU"""
        response = await client.delete(
            f"/api/v1/product-variants/{sample_variant.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_delete_variant_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试删除不存在的 SKU"""
        response = await client.delete(
            "/api/v1/product-variants/999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "SKU 不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_batch_create_variants_success(self, client: AsyncClient, auth_headers: dict, sample_product, sample_category, sample_dimension_templates):
        """测试成功批量创建 SKU"""
        # 先为分类添加维度
        color_template, size_template = sample_dimension_templates
        
        # 为分类添加颜色维度
        color_dimension_data = {
            "dimension_template_id": color_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        color_dimension_response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/dimensions",
            json=color_dimension_data,
            headers=auth_headers
        )
        assert color_dimension_response.status_code == 201
        color_dimension_data_response = color_dimension_response.json()
        
        # 为分类添加尺码维度
        size_dimension_data = {
            "dimension_template_id": size_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        size_dimension_response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/dimensions",
            json=size_dimension_data,
            headers=auth_headers
        )
        assert size_dimension_response.status_code == 201
        size_dimension_data_response = size_dimension_response.json()
        
        # 创建维度值
        color_values = [
            {"value_code": "red", "value_name": "红色", "value_type": "normal"},
            {"value_code": "blue", "value_name": "蓝色", "value_type": "normal"}
        ]
        
        size_values = [
            {"value_code": "S", "value_name": "小号", "value_type": "normal"},
            {"value_code": "M", "value_name": "中号", "value_type": "normal"}
        ]
        
        for value_data in color_values:
            value_data["category_dimension_id"] = color_dimension_data_response["id"]
            await client.post(
                "/api/v1/product-dimension-values",
                json=value_data,
                headers=auth_headers
            )
        
        for value_data in size_values:
            value_data["category_dimension_id"] = size_dimension_data_response["id"]
            await client.post(
                "/api/v1/product-dimension-values",
                json=value_data,
                headers=auth_headers
            )
        
        # 为产品分配分类
        assignment_data = {
            "category_id": sample_category.id,
            "is_primary": True
        }
        
        assignment_response = await client.post(
            f"/api/v1/products/{sample_product.id}/categories",
            json=assignment_data,
            headers=auth_headers
        )
        assert assignment_response.status_code == 201
        
        # 批量创建 SKU
        batch_data = {
            "dimension_combinations": [
                {"color": "red", "size": "S"},
                {"color": "red", "size": "M"},
                {"color": "blue", "size": "S"},
                {"color": "blue", "size": "M"}
            ],
            "base_data": {
                "price": 29.99,
                "cost_price": 15.00,
                "inventory_quantity": 100
            }
        }
        
        response = await client.post(
            f"/api/v1/products/{sample_product.id}/variants/batch",
            json=batch_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert len(data) == 4  # 2 * 2 = 4 种组合
        
        # 验证每个 SKU 的创建
        for variant in data:
            assert variant["product_id"] == sample_product.id
            assert variant["price"] == batch_data["base_data"]["price"]
            assert variant["cost_price"] == batch_data["base_data"]["cost_price"]
            assert variant["inventory_quantity"] == batch_data["base_data"]["inventory_quantity"]

    @pytest.mark.asyncio
    async def test_generate_cartesian_combinations(self, client: AsyncClient, auth_headers: dict, sample_product, sample_category, sample_dimension_templates):
        """测试生成笛卡尔积组合预览"""
        # 先为分类添加维度
        color_template, size_template = sample_dimension_templates
        
        # 为分类添加颜色维度
        color_dimension_data = {
            "dimension_template_id": color_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        color_dimension_response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/dimensions",
            json=color_dimension_data,
            headers=auth_headers
        )
        assert color_dimension_response.status_code == 201
        color_dimension_data_response = color_dimension_response.json()
        
        # 为分类添加尺码维度
        size_dimension_data = {
            "dimension_template_id": size_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        size_dimension_response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/dimensions",
            json=size_dimension_data,
            headers=auth_headers
        )
        assert size_dimension_response.status_code == 201
        size_dimension_data_response = size_dimension_response.json()
        
        # 创建维度值
        color_values = [
            {"value_code": "red", "value_name": "红色", "value_type": "normal"},
            {"value_code": "blue", "value_name": "蓝色", "value_type": "normal"}
        ]
        
        size_values = [
            {"value_code": "S", "value_name": "小号", "value_type": "normal"},
            {"value_code": "M", "value_name": "中号", "value_type": "normal"}
        ]
        
        for value_data in color_values:
            value_data["category_dimension_id"] = color_dimension_data_response["id"]
            await client.post(
                "/api/v1/product-dimension-values",
                json=value_data,
                headers=auth_headers
            )
        
        for value_data in size_values:
            value_data["category_dimension_id"] = size_dimension_data_response["id"]
            await client.post(
                "/api/v1/product-dimension-values",
                json=value_data,
                headers=auth_headers
            )
        
        # 为产品分配分类
        assignment_data = {
            "category_id": sample_category.id,
            "is_primary": True
        }
        
        assignment_response = await client.post(
            f"/api/v1/products/{sample_product.id}/categories",
            json=assignment_data,
            headers=auth_headers
        )
        assert assignment_response.status_code == 201
        
        # 生成笛卡尔积组合预览
        preview_data = {
            "dimension_values": {
                "color": ["red", "blue"],
                "size": ["S", "M"]
            }
        }
        
        response = await client.post(
            f"/api/v1/products/{sample_product.id}/variants/cartesian-preview",
            json=preview_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 4  # 2 * 2 = 4 种组合
        
        # 验证组合内容
        expected_combinations = [
            {"color": "red", "size": "S"},
            {"color": "red", "size": "M"},
            {"color": "blue", "size": "S"},
            {"color": "blue", "size": "M"}
        ]
        
        for combination in expected_combinations:
            assert combination in data

    @pytest.mark.asyncio
    async def test_create_variant_with_dimensions_success(self, client: AsyncClient, auth_headers: dict, sample_product, sample_category, sample_dimension_templates):
        """测试成功创建带维度值的 SKU"""
        # 先为分类添加维度
        color_template, size_template = sample_dimension_templates
        
        # 为分类添加颜色维度
        color_dimension_data = {
            "dimension_template_id": color_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        color_dimension_response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/dimensions",
            json=color_dimension_data,
            headers=auth_headers
        )
        assert color_dimension_response.status_code == 201
        color_dimension_data_response = color_dimension_response.json()
        
        # 为分类添加尺码维度
        size_dimension_data = {
            "dimension_template_id": size_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        size_dimension_response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/dimensions",
            json=size_dimension_data,
            headers=auth_headers
        )
        assert size_dimension_response.status_code == 201
        size_dimension_data_response = size_dimension_response.json()
        
        # 创建维度值
        color_value_data = {
            "category_dimension_id": color_dimension_data_response["id"],
            "value_code": "red",
            "value_name": "红色",
            "value_type": "normal"
        }
        
        color_value_response = await client.post(
            "/api/v1/product-dimension-values",
            json=color_value_data,
            headers=auth_headers
        )
        assert color_value_response.status_code == 201
        color_value_data_response = color_value_response.json()
        
        size_value_data = {
            "category_dimension_id": size_dimension_data_response["id"],
            "value_code": "S",
            "value_name": "小号",
            "value_type": "normal"
        }
        
        size_value_response = await client.post(
            "/api/v1/product-dimension-values",
            json=size_value_data,
            headers=auth_headers
        )
        assert size_value_response.status_code == 201
        size_value_data_response = size_value_response.json()
        
        # 为产品分配分类
        assignment_data = {
            "category_id": sample_category.id,
            "is_primary": True
        }
        
        assignment_response = await client.post(
            f"/api/v1/products/{sample_product.id}/categories",
            json=assignment_data,
            headers=auth_headers
        )
        assert assignment_response.status_code == 201
        
        # 创建带维度值的 SKU
        variant_data = {
            "sku": "BASIC-TSHIRT-RED-S",
            "name": "基础 T 恤 红色 小号",
            "price": 29.99,
            "cost_price": 15.00,
            "inventory_quantity": 100,
            "dimension_values": {
                "color": "red",
                "size": "S"
            }
        }
        
        response = await client.post(
            f"/api/v1/products/{sample_product.id}/variants",
            json=variant_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["sku"] == variant_data["sku"]
        assert data["name"] == variant_data["name"]
        assert data["price"] == variant_data["price"]

    @pytest.mark.asyncio
    async def test_get_variant_dimensions(self, client: AsyncClient, auth_headers: dict, sample_variant):
        """测试获取 SKU 的维度值"""
        response = await client.get(
            f"/api/v1/product-variants/{sample_variant.id}/dimensions",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_update_variant_dimensions(self, client: AsyncClient, auth_headers: dict, sample_variant):
        """测试更新 SKU 的维度值"""
        dimension_values = {
            "color": "blue",
            "size": "M"
        }
        
        response = await client.put(
            f"/api/v1/product-variants/{sample_variant.id}/dimensions",
            json=dimension_values,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestProductVariantsAPIIntegration:
    """产品 SKU 管理 API 完整集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_variant_workflow(self, client: AsyncClient, auth_headers: dict):
        """测试完整的 SKU 管理工作流"""
        # 1. 创建产品
        product_data = {
            "name": "基础 T 恤",
            "handle": "basic-tshirt",
            "description": "经典基础款 T 恤",
            "is_active": True
        }
        
        product_response = await client.post(
            "/api/v1/products",
            json=product_data,
            headers=auth_headers
        )
        assert product_response.status_code == 201
        product_data_response = product_response.json()
        
        # 2. 创建分类
        category_data = {
            "category_code": "clothing",
            "category_name": "服装",
            "description": "各类服装产品",
            "is_root": True
        }
        
        category_response = await client.post(
            "/api/v1/product-categories",
            json=category_data,
            headers=auth_headers
        )
        assert category_response.status_code == 201
        category_data_response = category_response.json()
        
        # 3. 创建维度模板
        color_template_data = {
            "dimension_code": "color",
            "dimension_name": "颜色",
            "dimension_type": "select",
            "description": "产品颜色维度"
        }
        
        color_template_response = await client.post(
            "/api/v1/product-dimension-templates",
            json=color_template_data,
            headers=auth_headers
        )
        assert color_template_response.status_code == 201
        color_template_data_response = color_template_response.json()
        
        size_template_data = {
            "dimension_code": "size",
            "dimension_name": "尺码",
            "dimension_type": "select",
            "description": "产品尺码维度"
        }
        
        size_template_response = await client.post(
            "/api/v1/product-dimension-templates",
            json=size_template_data,
            headers=auth_headers
        )
        assert size_template_response.status_code == 201
        size_template_data_response = size_template_response.json()
        
        # 4. 为分类添加维度
        color_dimension_data = {
            "dimension_template_id": color_template_data_response["id"],
            "is_required": True,
            "is_overridable": True
        }
        
        color_dimension_response = await client.post(
            f"/api/v1/product-categories/{category_data_response['id']}/dimensions",
            json=color_dimension_data,
            headers=auth_headers
        )
        assert color_dimension_response.status_code == 201
        color_dimension_data_response = color_dimension_response.json()
        
        size_dimension_data = {
            "dimension_template_id": size_template_data_response["id"],
            "is_required": True,
            "is_overridable": True
        }
        
        size_dimension_response = await client.post(
            f"/api/v1/product-categories/{category_data_response['id']}/dimensions",
            json=size_dimension_data,
            headers=auth_headers
        )
        assert size_dimension_response.status_code == 201
        size_dimension_data_response = size_dimension_response.json()
        
        # 5. 创建维度值
        color_values = [
            {"value_code": "red", "value_name": "红色", "value_type": "normal"},
            {"value_code": "blue", "value_name": "蓝色", "value_type": "normal"}
        ]
        
        size_values = [
            {"value_code": "S", "value_name": "小号", "value_type": "normal"},
            {"value_code": "M", "value_name": "中号", "value_type": "normal"}
        ]
        
        for value_data in color_values:
            value_data["category_dimension_id"] = color_dimension_data_response["id"]
            await client.post(
                "/api/v1/product-dimension-values",
                json=value_data,
                headers=auth_headers
            )
        
        for value_data in size_values:
            value_data["category_dimension_id"] = size_dimension_data_response["id"]
            await client.post(
                "/api/v1/product-dimension-values",
                json=value_data,
                headers=auth_headers
            )
        
        # 6. 为产品分配分类
        assignment_data = {
            "category_id": category_data_response["id"],
            "is_primary": True
        }
        
        assignment_response = await client.post(
            f"/api/v1/products/{product_data_response['id']}/categories",
            json=assignment_data,
            headers=auth_headers
        )
        assert assignment_response.status_code == 201
        
        # 7. 生成笛卡尔积组合预览
        preview_data = {
            "dimension_values": {
                "color": ["red", "blue"],
                "size": ["S", "M"]
            }
        }
        
        preview_response = await client.post(
            f"/api/v1/products/{product_data_response['id']}/variants/cartesian-preview",
            json=preview_data,
            headers=auth_headers
        )
        assert preview_response.status_code == 200
        preview_data_response = preview_response.json()
        assert len(preview_data_response) == 4
        
        # 8. 批量创建 SKU
        batch_data = {
            "dimension_combinations": preview_data_response,
            "base_data": {
                "price": 29.99,
                "cost_price": 15.00,
                "inventory_quantity": 100
            }
        }
        
        batch_response = await client.post(
            f"/api/v1/products/{product_data_response['id']}/variants/batch",
            json=batch_data,
            headers=auth_headers
        )
        assert batch_response.status_code == 201
        batch_data_response = batch_response.json()
        assert len(batch_data_response) == 4
        
        # 9. 获取 SKU 列表
        variants_response = await client.get(
            f"/api/v1/products/{product_data_response['id']}/variants",
            headers=auth_headers
        )
        assert variants_response.status_code == 200
        variants_data = variants_response.json()
        assert len(variants_data) == 4
        
        # 10. 更新其中一个 SKU
        update_data = {
            "name": "更新后的 SKU 名称",
            "price": 39.99
        }
        
        update_response = await client.put(
            f"/api/v1/product-variants/{batch_data_response[0]['id']}",
            json=update_data,
            headers=auth_headers
        )
        assert update_response.status_code == 200
        
        # 11. 清理：删除 SKU
        for variant in batch_data_response:
            delete_response = await client.delete(
                f"/api/v1/product-variants/{variant['id']}",
                headers=auth_headers
            )
            assert delete_response.status_code == 200
        
        # 12. 删除产品
        delete_product_response = await client.delete(
            f"/api/v1/products/{product_data_response['id']}",
            headers=auth_headers
        )
        assert delete_product_response.status_code == 200
        
        # 13. 删除分类
        delete_category_response = await client.delete(
            f"/api/v1/product-categories/{category_data_response['id']}",
            headers=auth_headers
        )
        assert delete_category_response.status_code == 200
        
        # 14. 删除维度模板
        delete_color_template_response = await client.delete(
            f"/api/v1/product-dimension-templates/{color_template_data_response['id']}",
            headers=auth_headers
        )
        assert delete_color_template_response.status_code == 200
        
        delete_size_template_response = await client.delete(
            f"/api/v1/product-dimension-templates/{size_template_data_response['id']}",
            headers=auth_headers
        )
        assert delete_size_template_response.status_code == 200

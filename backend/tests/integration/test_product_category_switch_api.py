"""
产品分类切换 API 集成测试

测试分类切换的完整 API 流程：
1. 分类切换兼容性分析
2. 维度冲突检测
3. 维度迁移处理
4. 分类切换执行
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_async_db
from app.models.product import Product, ProductVariant
from app.models.product_category import ProductCategory, ProductCategoryAssignment
from app.models.product_dimension import ProductDimensionTemplate, ProductDimensionValue
from app.core.jwt_utils import jwt_utils


class TestProductCategorySwitchAPI:
    """产品分类切换 API 集成测试"""
    
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
    async def source_category(self, db: AsyncSession, sample_tenant):
        """创建源分类（服装）"""
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
    async def target_category(self, db: AsyncSession, sample_tenant):
        """创建目标分类（电子产品）"""
        category = ProductCategory(
            tenant_id=sample_tenant.id,
            category_code="electronics",
            category_name="电子产品",
            description="各类电子设备",
            is_root=True
        )
        db.add(category)
        await db.commit()
        await db.refresh(category)
        return category
    
    @pytest.fixture
    async def clothing_dimension_template(self, db: AsyncSession, sample_tenant):
        """创建服装维度模板（颜色、尺码）"""
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
    
    @pytest.fixture
    async def electronics_dimension_template(self, db: AsyncSession, sample_tenant):
        """创建电子产品维度模板（品牌、型号）"""
        brand_template = ProductDimensionTemplate(
            tenant_id=sample_tenant.id,
            dimension_code="brand",
            dimension_name="品牌",
            dimension_type="select",
            description="产品品牌维度"
        )
        model_template = ProductDimensionTemplate(
            tenant_id=sample_tenant.id,
            dimension_code="model",
            dimension_name="型号",
            dimension_type="text",
            description="产品型号维度"
        )
        
        db.add(brand_template)
        db.add(model_template)
        await db.commit()
        await db.refresh(brand_template)
        await db.refresh(model_template)
        
        return [brand_template, model_template]

    @pytest.mark.asyncio
    async def test_analyze_category_switch_compatibility_success(self, client: AsyncClient, auth_headers: dict, sample_product, source_category, target_category):
        """测试成功分析分类切换兼容性"""
        # 先为产品分配源分类
        assignment_data = {
            "category_id": source_category.id,
            "is_primary": True
        }
        
        assignment_response = await client.post(
            f"/api/v1/products/{sample_product.id}/categories",
            json=assignment_data,
            headers=auth_headers
        )
        assert assignment_response.status_code == 201
        
        # 分析分类切换兼容性
        response = await client.post(
            f"/api/v1/products/{sample_product.id}/switch-category/preview",
            json={"target_category_id": target_category.id},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "compatible_dimensions" in data
        assert "incompatible_dimensions" in data
        assert "conflicts" in data
        assert "recommendations" in data

    @pytest.mark.asyncio
    async def test_analyze_category_switch_compatibility_product_not_found(self, client: AsyncClient, auth_headers: dict, target_category):
        """测试分析不存在的产品的分类切换兼容性"""
        response = await client.post(
            "/api/v1/products/999/switch-category/preview",
            json={"target_category_id": target_category.id},
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "产品不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_analyze_category_switch_compatibility_target_category_not_found(self, client: AsyncClient, auth_headers: dict, sample_product, source_category):
        """测试分析切换到不存在分类的兼容性"""
        # 先为产品分配源分类
        assignment_data = {
            "category_id": source_category.id,
            "is_primary": True
        }
        
        assignment_response = await client.post(
            f"/api/v1/products/{sample_product.id}/categories",
            json=assignment_data,
            headers=auth_headers
        )
        assert assignment_response.status_code == 201
        
        # 分析分类切换兼容性
        response = await client.post(
            f"/api/v1/products/{sample_product.id}/switch-category/preview",
            json={"target_category_id": 999},
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "目标分类不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_execute_category_switch_success(self, client: AsyncClient, auth_headers: dict, sample_product, source_category, target_category):
        """测试成功执行分类切换"""
        # 先为产品分配源分类
        assignment_data = {
            "category_id": source_category.id,
            "is_primary": True
        }
        
        assignment_response = await client.post(
            f"/api/v1/products/{sample_product.id}/categories",
            json=assignment_data,
            headers=auth_headers
        )
        assert assignment_response.status_code == 201
        
        # 执行分类切换
        switch_data = {
            "target_category_id": target_category.id,
            "switch_options": {
                "migrate_incompatible_dimensions": True,
                "remove_incompatible_dimensions": False,
                "keep_compatible_dimensions": True
            }
        }
        
        response = await client.post(
            f"/api/v1/products/{sample_product.id}/switch-category",
            json=switch_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "new_category_assignment" in data
        assert "migrated_dimensions" in data
        assert "removed_dimensions" in data

    @pytest.mark.asyncio
    async def test_execute_category_switch_product_not_found(self, client: AsyncClient, auth_headers: dict, target_category):
        """测试为不存在的产品执行分类切换"""
        switch_data = {
            "target_category_id": target_category.id,
            "switch_options": {}
        }
        
        response = await client.post(
            "/api/v1/products/999/switch-category",
            json=switch_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "产品不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_execute_category_switch_target_category_not_found(self, client: AsyncClient, auth_headers: dict, sample_product, source_category):
        """测试切换到不存在分类的分类切换"""
        # 先为产品分配源分类
        assignment_data = {
            "category_id": source_category.id,
            "is_primary": True
        }
        
        assignment_response = await client.post(
            f"/api/v1/products/{sample_product.id}/categories",
            json=assignment_data,
            headers=auth_headers
        )
        assert assignment_response.status_code == 201
        
        # 执行分类切换
        switch_data = {
            "target_category_id": 999,
            "switch_options": {}
        }
        
        response = await client.post(
            f"/api/v1/products/{sample_product.id}/switch-category",
            json=switch_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "目标分类不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_execute_category_switch_with_dimension_conflicts(self, client: AsyncClient, auth_headers: dict, sample_product, source_category, target_category, clothing_dimension_template, electronics_dimension_template):
        """测试执行有维度冲突的分类切换"""
        # 先为产品分配源分类
        assignment_data = {
            "category_id": source_category.id,
            "is_primary": True
        }
        
        assignment_response = await client.post(
            f"/api/v1/products/{sample_product.id}/categories",
            json=assignment_data,
            headers=auth_headers
        )
        assert assignment_response.status_code == 201
        
        # 为源分类添加维度
        color_template, size_template = clothing_dimension_template
        
        color_dimension_data = {
            "dimension_template_id": color_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        color_dimension_response = await client.post(
            f"/api/v1/product-categories/{source_category.id}/dimensions",
            json=color_dimension_data,
            headers=auth_headers
        )
        assert color_dimension_response.status_code == 201
        color_dimension_data_response = color_dimension_response.json()
        
        size_dimension_data = {
            "dimension_template_id": size_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        size_dimension_response = await client.post(
            f"/api/v1/product-categories/{source_category.id}/dimensions",
            json=size_dimension_data,
            headers=auth_headers
        )
        assert size_dimension_response.status_code == 201
        size_dimension_data_response = size_dimension_response.json()
        
        # 为目标分类添加不同的维度
        brand_template, model_template = electronics_dimension_template
        
        brand_dimension_data = {
            "dimension_template_id": brand_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        brand_dimension_response = await client.post(
            f"/api/v1/product-categories/{target_category.id}/dimensions",
            json=brand_dimension_data,
            headers=auth_headers
        )
        assert brand_dimension_response.status_code == 201
        
        model_dimension_data = {
            "dimension_template_id": model_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        model_dimension_response = await client.post(
            f"/api/v1/product-categories/{target_category.id}/dimensions",
            json=model_dimension_data,
            headers=auth_headers
        )
        assert model_dimension_response.status_code == 201
        
        # 创建 SKU 并分配维度值
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
        
        variant_response = await client.post(
            f"/api/v1/products/{sample_product.id}/variants",
            json=variant_data,
            headers=auth_headers
        )
        assert variant_response.status_code == 201
        
        # 分析分类切换兼容性
        preview_response = await client.post(
            f"/api/v1/products/{sample_product.id}/switch-category/preview",
            json={"target_category_id": target_category.id},
            headers=auth_headers
        )
        assert preview_response.status_code == 200
        preview_data = preview_response.json()
        
        # 应该检测到不兼容的维度
        assert len(preview_data["incompatible_dimensions"]) > 0
        
        # 执行分类切换（迁移不兼容维度为属性）
        switch_data = {
            "target_category_id": target_category.id,
            "switch_options": {
                "migrate_incompatible_dimensions": True,
                "remove_incompatible_dimensions": False,
                "keep_compatible_dimensions": True
            }
        }
        
        response = await client.post(
            f"/api/v1/products/{sample_product.id}/switch-category",
            json=switch_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "migrated_dimensions" in data
        assert len(data["migrated_dimensions"]) > 0

    @pytest.mark.asyncio
    async def test_get_product_current_category(self, client: AsyncClient, auth_headers: dict, sample_product, source_category):
        """测试获取产品当前分类"""
        # 先为产品分配分类
        assignment_data = {
            "category_id": source_category.id,
            "is_primary": True
        }
        
        assignment_response = await client.post(
            f"/api/v1/products/{sample_product.id}/categories",
            json=assignment_data,
            headers=auth_headers
        )
        assert assignment_response.status_code == 201
        
        # 获取产品当前分类
        response = await client.get(
            f"/api/v1/products/{sample_product.id}/current-category",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == source_category.id
        assert data["category_name"] == source_category.category_name

    @pytest.mark.asyncio
    async def test_get_product_current_category_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试获取不存在产品的当前分类"""
        response = await client.get(
            "/api/v1/products/999/current-category",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "产品不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_product_current_category_no_assignment(self, client: AsyncClient, auth_headers: dict, sample_product):
        """测试获取未分配分类的产品的当前分类"""
        response = await client.get(
            f"/api/v1/products/{sample_product.id}/current-category",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data is None

    @pytest.mark.asyncio
    async def test_validate_switch_options_success(self, client: AsyncClient, auth_headers: dict):
        """测试验证有效的切换选项"""
        valid_options = {
            "migrate_incompatible_dimensions": True,
            "remove_incompatible_dimensions": False,
            "keep_compatible_dimensions": True
        }
        
        response = await client.post(
            "/api/v1/products/switch-category/validate-options",
            json=valid_options,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_switch_options_invalid(self, client: AsyncClient, auth_headers: dict):
        """测试验证无效的切换选项"""
        invalid_options = {
            "migrate_incompatible_dimensions": "invalid_boolean",
            "remove_incompatible_dimensions": None,
            "keep_compatible_dimensions": True
        }
        
        response = await client.post(
            "/api/v1/products/switch-category/validate-options",
            json=invalid_options,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "无效的切换选项" in data["detail"]


class TestProductCategorySwitchAPIIntegration:
    """产品分类切换 API 完整集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_category_switch_workflow(self, client: AsyncClient, auth_headers: dict):
        """测试完整的分类切换工作流"""
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
        
        # 2. 创建源分类（服装）
        source_category_data = {
            "category_code": "clothing",
            "category_name": "服装",
            "description": "各类服装产品",
            "is_root": True
        }
        
        source_category_response = await client.post(
            "/api/v1/product-categories",
            json=source_category_data,
            headers=auth_headers
        )
        assert source_category_response.status_code == 201
        source_category_data_response = source_category_response.json()
        
        # 3. 创建目标分类（电子产品）
        target_category_data = {
            "category_code": "electronics",
            "category_name": "电子产品",
            "description": "各类电子设备",
            "is_root": True
        }
        
        target_category_response = await client.post(
            "/api/v1/product-categories",
            json=target_category_data,
            headers=auth_headers
        )
        assert target_category_response.status_code == 201
        target_category_data_response = target_category_response.json()
        
        # 4. 创建维度模板
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
        
        brand_template_data = {
            "dimension_code": "brand",
            "dimension_name": "品牌",
            "dimension_type": "select",
            "description": "产品品牌维度"
        }
        
        brand_template_response = await client.post(
            "/api/v1/product-dimension-templates",
            json=brand_template_data,
            headers=auth_headers
        )
        assert brand_template_response.status_code == 201
        brand_template_data_response = brand_template_response.json()
        
        # 5. 为源分类添加维度
        source_dimension_data = {
            "dimension_template_id": color_template_data_response["id"],
            "is_required": True,
            "is_overridable": True
        }
        
        source_dimension_response = await client.post(
            f"/api/v1/product-categories/{source_category_data_response['id']}/dimensions",
            json=source_dimension_data,
            headers=auth_headers
        )
        assert source_dimension_response.status_code == 201
        source_dimension_data_response = source_dimension_response.json()
        
        # 6. 为目标分类添加维度
        target_dimension_data = {
            "dimension_template_id": brand_template_data_response["id"],
            "is_required": True,
            "is_overridable": True
        }
        
        target_dimension_response = await client.post(
            f"/api/v1/product-categories/{target_category_data_response['id']}/dimensions",
            json=target_dimension_data,
            headers=auth_headers
        )
        assert target_dimension_response.status_code == 201
        
        # 7. 为产品分配源分类
        assignment_data = {
            "category_id": source_category_data_response["id"],
            "is_primary": True
        }
        
        assignment_response = await client.post(
            f"/api/v1/products/{product_data_response['id']}/categories",
            json=assignment_data,
            headers=auth_headers
        )
        assert assignment_response.status_code == 201
        
        # 8. 创建 SKU 并分配维度值
        variant_data = {
            "sku": "BASIC-TSHIRT-RED",
            "name": "基础 T 恤 红色",
            "price": 29.99,
            "cost_price": 15.00,
            "inventory_quantity": 100,
            "dimension_values": {
                "color": "red"
            }
        }
        
        variant_response = await client.post(
            f"/api/v1/products/{product_data_response['id']}/variants",
            json=variant_data,
            headers=auth_headers
        )
        assert variant_response.status_code == 201
        
        # 9. 分析分类切换兼容性
        preview_response = await client.post(
            f"/api/v1/products/{product_data_response['id']}/switch-category/preview",
            json={"target_category_id": target_category_data_response["id"]},
            headers=auth_headers
        )
        assert preview_response.status_code == 200
        preview_data = preview_response.json()
        
        # 10. 执行分类切换
        switch_data = {
            "target_category_id": target_category_data_response["id"],
            "switch_options": {
                "migrate_incompatible_dimensions": True,
                "remove_incompatible_dimensions": False,
                "keep_compatible_dimensions": True
            }
        }
        
        switch_response = await client.post(
            f"/api/v1/products/{product_data_response['id']}/switch-category",
            json=switch_data,
            headers=auth_headers
        )
        assert switch_response.status_code == 200
        switch_data_response = switch_response.json()
        
        # 11. 验证分类切换结果
        current_category_response = await client.get(
            f"/api/v1/products/{product_data_response['id']}/current-category",
            headers=auth_headers
        )
        assert current_category_response.status_code == 200
        current_category_data = current_category_response.json()
        assert current_category_data["id"] == target_category_data_response["id"]
        
        # 12. 清理：删除产品
        delete_product_response = await client.delete(
            f"/api/v1/products/{product_data_response['id']}",
            headers=auth_headers
        )
        assert delete_product_response.status_code == 200
        
        # 13. 删除分类
        delete_source_category_response = await client.delete(
            f"/api/v1/product-categories/{source_category_data_response['id']}",
            headers=auth_headers
        )
        assert delete_source_category_response.status_code == 200
        
        delete_target_category_response = await client.delete(
            f"/api/v1/product-categories/{target_category_data_response['id']}",
            headers=auth_headers
        )
        assert delete_target_category_response.status_code == 200
        
        # 14. 删除维度模板
        delete_color_template_response = await client.delete(
            f"/api/v1/product-dimension-templates/{color_template_data_response['id']}",
            headers=auth_headers
        )
        assert delete_color_template_response.status_code == 200
        
        delete_brand_template_response = await client.delete(
            f"/api/v1/product-dimension-templates/{brand_template_data_response['id']}",
            headers=auth_headers
        )
        assert delete_brand_template_response.status_code == 200

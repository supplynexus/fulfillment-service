"""
产品维度管理 API 集成测试

测试维度管理的完整 API 流程：
1. 维度模板 CRUD 操作
2. 维度值管理
3. 维度继承和覆盖
4. 维度合并
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_async_db
from app.models.product_dimension import ProductDimensionTemplate, ProductDimensionValue
from app.models.product_category import ProductCategory
from app.core.jwt_utils import jwt_utils


class TestProductDimensionsAPI:
    """产品维度管理 API 集成测试"""
    
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
    async def sample_dimension_template(self, db: AsyncSession, sample_tenant):
        """创建示例维度模板"""
        template = ProductDimensionTemplate(
            tenant_id=sample_tenant.id,
            dimension_code="color",
            dimension_name="颜色",
            dimension_type="select",
            description="产品颜色维度"
        )
        db.add(template)
        await db.commit()
        await db.refresh(template)
        return template
    
    @pytest.fixture
    async def sample_category(self, db: AsyncSession, sample_tenant):
        """创建示例分类"""
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

    @pytest.mark.asyncio
    async def test_create_dimension_template_success(self, client: AsyncClient, auth_headers: dict):
        """测试成功创建维度模板"""
        template_data = {
            "dimension_code": "size",
            "dimension_name": "尺码",
            "dimension_type": "select",
            "description": "产品尺码维度"
        }
        
        response = await client.post(
            "/api/v1/product-dimension-templates",
            json=template_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["dimension_code"] == template_data["dimension_code"]
        assert data["dimension_name"] == template_data["dimension_name"]
        assert data["dimension_type"] == template_data["dimension_type"]

    @pytest.mark.asyncio
    async def test_create_dimension_template_duplicate_code(self, client: AsyncClient, auth_headers: dict, sample_dimension_template):
        """测试创建重复编码的维度模板"""
        template_data = {
            "dimension_code": "color",  # 重复编码
            "dimension_name": "颜色2",
            "dimension_type": "select"
        }
        
        response = await client.post(
            "/api/v1/product-dimension-templates",
            json=template_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "维度编码已存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_dimension_template_by_id(self, client: AsyncClient, auth_headers: dict, sample_dimension_template):
        """测试根据ID获取维度模板"""
        response = await client.get(
            f"/api/v1/product-dimension-templates/{sample_dimension_template.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_dimension_template.id
        assert data["dimension_code"] == sample_dimension_template.dimension_code
        assert data["dimension_name"] == sample_dimension_template.dimension_name

    @pytest.mark.asyncio
    async def test_get_dimension_template_by_id_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试获取不存在的维度模板"""
        response = await client.get(
            "/api/v1/product-dimension-templates/999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "维度模板不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_dimension_templates_list(self, client: AsyncClient, auth_headers: dict, sample_dimension_template):
        """测试获取维度模板列表"""
        response = await client.get(
            "/api/v1/product-dimension-templates",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.asyncio
    async def test_update_dimension_template_success(self, client: AsyncClient, auth_headers: dict, sample_dimension_template):
        """测试成功更新维度模板"""
        update_data = {
            "dimension_name": "更新后的颜色",
            "description": "更新后的描述"
        }
        
        response = await client.put(
            f"/api/v1/product-dimension-templates/{sample_dimension_template.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["dimension_name"] == update_data["dimension_name"]
        assert data["description"] == update_data["description"]

    @pytest.mark.asyncio
    async def test_update_dimension_template_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试更新不存在的维度模板"""
        update_data = {"dimension_name": "更新后的名称"}
        
        response = await client.put(
            "/api/v1/product-dimension-templates/999",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "维度模板不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_delete_dimension_template_success(self, client: AsyncClient, auth_headers: dict, sample_dimension_template):
        """测试成功删除维度模板"""
        response = await client.delete(
            f"/api/v1/product-dimension-templates/{sample_dimension_template.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_delete_dimension_template_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试删除不存在的维度模板"""
        response = await client.delete(
            "/api/v1/product-dimension-templates/999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "维度模板不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_create_dimension_value_success(self, client: AsyncClient, auth_headers: dict, sample_dimension_template, sample_category):
        """测试成功创建维度值"""
        # 先为分类添加维度
        dimension_data = {
            "dimension_template_id": sample_dimension_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        dimension_response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/dimensions",
            json=dimension_data,
            headers=auth_headers
        )
        assert dimension_response.status_code == 201
        dimension_data_response = dimension_response.json()
        
        # 创建维度值
        value_data = {
            "category_dimension_id": dimension_data_response["id"],
            "value_code": "red",
            "value_name": "红色",
            "value_type": "normal",
            "is_default": False
        }
        
        response = await client.post(
            "/api/v1/product-dimension-values",
            json=value_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["value_code"] == value_data["value_code"]
        assert data["value_name"] == value_data["value_name"]
        assert data["value_type"] == value_data["value_type"]

    @pytest.mark.asyncio
    async def test_create_dimension_value_duplicate_code(self, client: AsyncClient, auth_headers: dict, sample_dimension_template, sample_category):
        """测试创建重复编码的维度值"""
        # 先为分类添加维度
        dimension_data = {
            "dimension_template_id": sample_dimension_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        dimension_response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/dimensions",
            json=dimension_data,
            headers=auth_headers
        )
        assert dimension_response.status_code == 201
        dimension_data_response = dimension_response.json()
        
        # 创建第一个维度值
        value_data = {
            "category_dimension_id": dimension_data_response["id"],
            "value_code": "red",
            "value_name": "红色",
            "value_type": "normal"
        }
        
        first_response = await client.post(
            "/api/v1/product-dimension-values",
            json=value_data,
            headers=auth_headers
        )
        assert first_response.status_code == 201
        
        # 创建重复编码的维度值
        duplicate_value_data = {
            "category_dimension_id": dimension_data_response["id"],
            "value_code": "red",  # 重复编码
            "value_name": "红色2",
            "value_type": "normal"
        }
        
        response = await client.post(
            "/api/v1/product-dimension-values",
            json=duplicate_value_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "维度值编码已存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_dimension_values_by_template(self, client: AsyncClient, auth_headers: dict, sample_dimension_template):
        """测试根据维度模板获取维度值列表"""
        response = await client.get(
            f"/api/v1/product-dimension-templates/{sample_dimension_template.id}/values",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_update_dimension_value_success(self, client: AsyncClient, auth_headers: dict, sample_dimension_template, sample_category):
        """测试成功更新维度值"""
        # 先创建维度值和分类维度关联
        dimension_data = {
            "dimension_template_id": sample_dimension_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        dimension_response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/dimensions",
            json=dimension_data,
            headers=auth_headers
        )
        assert dimension_response.status_code == 201
        dimension_data_response = dimension_response.json()
        
        # 创建维度值
        value_data = {
            "category_dimension_id": dimension_data_response["id"],
            "value_code": "red",
            "value_name": "红色",
            "value_type": "normal"
        }
        
        create_response = await client.post(
            "/api/v1/product-dimension-values",
            json=value_data,
            headers=auth_headers
        )
        assert create_response.status_code == 201
        value_data_response = create_response.json()
        
        # 更新维度值
        update_data = {
            "value_name": "更新后的红色",
            "is_default": True
        }
        
        response = await client.put(
            f"/api/v1/product-dimension-values/{value_data_response['id']}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["value_name"] == update_data["value_name"]
        assert data["is_default"] == update_data["is_default"]

    @pytest.mark.asyncio
    async def test_delete_dimension_value_success(self, client: AsyncClient, auth_headers: dict, sample_dimension_template, sample_category):
        """测试成功删除维度值"""
        # 先创建维度值和分类维度关联
        dimension_data = {
            "dimension_template_id": sample_dimension_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        dimension_response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/dimensions",
            json=dimension_data,
            headers=auth_headers
        )
        assert dimension_response.status_code == 201
        dimension_data_response = dimension_response.json()
        
        # 创建维度值
        value_data = {
            "category_dimension_id": dimension_data_response["id"],
            "value_code": "red",
            "value_name": "红色",
            "value_type": "normal"
        }
        
        create_response = await client.post(
            "/api/v1/product-dimension-values",
            json=value_data,
            headers=auth_headers
        )
        assert create_response.status_code == 201
        value_data_response = create_response.json()
        
        # 删除维度值
        response = await client.delete(
            f"/api/v1/product-dimension-values/{value_data_response['id']}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_merge_dimension_values_success(self, client: AsyncClient, auth_headers: dict, sample_dimension_template, sample_category):
        """测试成功合并维度值"""
        # 先创建维度值和分类维度关联
        dimension_data = {
            "dimension_template_id": sample_dimension_template.id,
            "is_required": True,
            "is_overridable": True
        }
        
        dimension_response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/dimensions",
            json=dimension_data,
            headers=auth_headers
        )
        assert dimension_response.status_code == 201
        dimension_data_response = dimension_response.json()
        
        # 创建两个维度值
        value1_data = {
            "category_dimension_id": dimension_data_response["id"],
            "value_code": "red1",
            "value_name": "红色1",
            "value_type": "normal"
        }
        
        value2_data = {
            "category_dimension_id": dimension_data_response["id"],
            "value_code": "red2",
            "value_name": "红色2",
            "value_type": "normal"
        }
        
        create1_response = await client.post(
            "/api/v1/product-dimension-values",
            json=value1_data,
            headers=auth_headers
        )
        assert create1_response.status_code == 201
        value1_data_response = create1_response.json()
        
        create2_response = await client.post(
            "/api/v1/product-dimension-values",
            json=value2_data,
            headers=auth_headers
        )
        assert create2_response.status_code == 201
        value2_data_response = create2_response.json()
        
        # 合并维度值
        merge_data = {
            "source_value_id": value2_data_response["id"],
            "target_value_id": value1_data_response["id"]
        }
        
        response = await client.post(
            "/api/v1/product-dimension-values/merge",
            json=merge_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_get_dimension_values_by_category(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试根据分类获取维度值"""
        response = await client.get(
            f"/api/v1/product-categories/{sample_category.id}/dimension-values",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_dimension_values_by_template_and_category(self, client: AsyncClient, auth_headers: dict, sample_dimension_template, sample_category):
        """测试根据维度模板和分类获取维度值"""
        response = await client.get(
            f"/api/v1/product-dimension-templates/{sample_dimension_template.id}/categories/{sample_category.id}/values",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestProductDimensionsAPIIntegration:
    """产品维度管理 API 完整集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_dimension_workflow(self, client: AsyncClient, auth_headers: dict):
        """测试完整的维度管理工作流"""
        # 1. 创建维度模板
        template_data = {
            "dimension_code": "color",
            "dimension_name": "颜色",
            "dimension_type": "select",
            "description": "产品颜色维度"
        }
        
        template_response = await client.post(
            "/api/v1/product-dimension-templates",
            json=template_data,
            headers=auth_headers
        )
        assert template_response.status_code == 201
        template_data_response = template_response.json()
        
        # 2. 创建分类
        category_data = {
            "category_code": "electronics",
            "category_name": "电子产品",
            "description": "电子产品分类",
            "is_root": True
        }
        
        category_response = await client.post(
            "/api/v1/product-categories",
            json=category_data,
            headers=auth_headers
        )
        assert category_response.status_code == 201
        category_data_response = category_response.json()
        
        # 3. 为分类添加维度
        dimension_data = {
            "dimension_template_id": template_data_response["id"],
            "is_required": True,
            "is_overridable": True
        }
        
        dimension_response = await client.post(
            f"/api/v1/product-categories/{category_data_response['id']}/dimensions",
            json=dimension_data,
            headers=auth_headers
        )
        assert dimension_response.status_code == 201
        dimension_data_response = dimension_response.json()
        
        # 4. 创建维度值
        value_data = {
            "category_dimension_id": dimension_data_response["id"],
            "value_code": "red",
            "value_name": "红色",
            "value_type": "normal",
            "is_default": False
        }
        
        value_response = await client.post(
            "/api/v1/product-dimension-values",
            json=value_data,
            headers=auth_headers
        )
        assert value_response.status_code == 201
        value_data_response = value_response.json()
        
        # 5. 创建另一个维度值
        value2_data = {
            "category_dimension_id": dimension_data_response["id"],
            "value_code": "blue",
            "value_name": "蓝色",
            "value_type": "normal",
            "is_default": False
        }
        
        value2_response = await client.post(
            "/api/v1/product-dimension-values",
            json=value2_data,
            headers=auth_headers
        )
        assert value2_response.status_code == 201
        
        # 6. 获取分类的有效维度
        dimensions_response = await client.get(
            f"/api/v1/product-categories/{category_data_response['id']}/dimensions",
            headers=auth_headers
        )
        assert dimensions_response.status_code == 200
        dimensions_data = dimensions_response.json()
        assert len(dimensions_data) >= 1)
        
        # 7. 获取维度值列表
        values_response = await client.get(
            f"/api/v1/product-dimension-templates/{template_data_response['id']}/values",
            headers=auth_headers
        )
        assert values_response.status_code == 200
        values_data = values_response.json()
        assert len(values_data) >= 2
        
        # 8. 更新维度值
        update_data = {
            "value_name": "更新后的红色",
            "is_default": True
        }
        
        update_response = await client.put(
            f"/api/v1/product-dimension-values/{value_data_response['id']}",
            json=update_data,
            headers=auth_headers
        )
        assert update_response.status_code == 200
        
        # 9. 清理：删除维度值
        delete_value_response = await client.delete(
            f"/api/v1/product-dimension-values/{value_data_response['id']}",
            headers=auth_headers
        )
        assert delete_value_response.status_code == 200
        
        # 10. 删除分类维度
        delete_dimension_response = await client.delete(
            f"/api/v1/product-categories/{category_data_response['id']}/dimensions/{dimension_data_response['id']}",
            headers=auth_headers
        )
        assert delete_dimension_response.status_code == 200
        
        # 11. 删除分类
        delete_category_response = await client.delete(
            f"/api/v1/product-categories/{category_data_response['id']}",
            headers=auth_headers
        )
        assert delete_category_response.status_code == 200
        
        # 12. 删除维度模板
        delete_template_response = await client.delete(
            f"/api/v1/product-dimension-templates/{template_data_response['id']}",
            headers=auth_headers
        )
        assert delete_template_response.status_code == 200

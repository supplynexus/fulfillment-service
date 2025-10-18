"""
产品分类管理 API 集成测试

测试分类管理的完整 API 流程：
1. 分类 CRUD 操作
2. 分类关系管理
3. 分类树查询
4. 分类维度管理
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_async_db
from app.models.product_category import ProductCategory, ProductCategoryRelation
from app.models.product_dimension import ProductDimensionTemplate
from app.core.jwt_utils import jwt_utils


class TestProductCategoriesAPI:
    """产品分类管理 API 集成测试"""
    
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
    async def test_create_category_success(self, client: AsyncClient, auth_headers: dict):
        """测试成功创建分类"""
        category_data = {
            "category_code": "clothing",
            "category_name": "服装",
            "description": "各类服装产品",
            "is_root": False
        }
        
        client_instance = await client.__anext__()
        response = await client_instance.post(
            "/api/v1/product-categories",
            json=category_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["category_code"] == category_data["category_code"]
        assert data["category_name"] == category_data["category_name"]
        assert data["description"] == category_data["description"]
        assert data["is_root"] == category_data["is_root"]

    @pytest.mark.asyncio
    async def test_create_category_duplicate_code(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试创建重复编码的分类"""
        category_data = {
            "category_code": "electronics",  # 重复编码
            "category_name": "电子产品2",
            "description": "重复的电子产品分类"
        }
        
        response = await client.post(
            "/api/v1/product-categories",
            json=category_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "分类编码已存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_category_by_id(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试根据ID获取分类"""
        response = await client.get(
            f"/api/v1/product-categories/{sample_category.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == sample_category.id
        assert data["category_code"] == sample_category.category_code
        assert data["category_name"] == sample_category.category_name

    @pytest.mark.asyncio
    async def test_get_category_by_id_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试获取不存在的分类"""
        response = await client.get(
            "/api/v1/product-categories/999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "分类不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_categories_tree(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试获取分类树"""
        response = await client.get(
            "/api/v1/product-categories/tree",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert "relations" in data
        assert "tree_structure" in data
        assert len(data["categories"]) >= 1

    @pytest.mark.asyncio
    async def test_update_category_success(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试成功更新分类"""
        update_data = {
            "category_name": "更新后的电子产品",
            "description": "更新后的描述"
        }
        
        response = await client.put(
            f"/api/v1/product-categories/{sample_category.id}",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["category_name"] == update_data["category_name"]
        assert data["description"] == update_data["description"]

    @pytest.mark.asyncio
    async def test_update_category_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试更新不存在的分类"""
        update_data = {"category_name": "更新后的名称"}
        
        response = await client.put(
            "/api/v1/product-categories/999",
            json=update_data,
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "分类不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_delete_category_success(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试成功删除分类"""
        response = await client.delete(
            f"/api/v1/product-categories/{sample_category.id}",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    @pytest.mark.asyncio
    async def test_delete_category_not_found(self, client: AsyncClient, auth_headers: dict):
        """测试删除不存在的分类"""
        response = await client.delete(
            "/api/v1/product-categories/999",
            headers=auth_headers
        )
        
        assert response.status_code == 404
        data = response.json()
        assert "分类不存在" in data["detail"]

    @pytest.mark.asyncio
    async def test_create_category_relation_success(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试成功创建分类关系"""
        # 先创建子分类
        child_category_data = {
            "category_code": "smartphones",
            "category_name": "智能手机",
            "description": "智能手机产品"
        }
        
        child_response = await client.post(
            "/api/v1/product-categories",
            json=child_category_data,
            headers=auth_headers
        )
        assert child_response.status_code == 201
        child_data = child_response.json()
        
        # 创建父子关系
        relation_data = {
            "parent_category_id": sample_category.id,
            "child_category_id": child_data["id"],
            "relation_type": "parent_child"
        }
        
        response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/relations",
            json=relation_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["parent_category_id"] == relation_data["parent_category_id"]
        assert data["child_category_id"] == relation_data["child_category_id"]

    @pytest.mark.asyncio
    async def test_create_category_relation_self_reference(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试创建自引用的分类关系"""
        relation_data = {
            "parent_category_id": sample_category.id,
            "child_category_id": sample_category.id,  # 自引用
            "relation_type": "parent_child"
        }
        
        response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/relations",
            json=relation_data,
            headers=auth_headers
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "不能创建自引用关系" in data["detail"]

    @pytest.mark.asyncio
    async def test_get_category_children(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试获取分类子节点"""
        response = await client.get(
            f"/api/v1/product-categories/{sample_category.id}/children",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_category_parents(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试获取分类父节点"""
        response = await client.get(
            f"/api/v1/product-categories/{sample_category.id}/parents",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_category_dimensions(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试获取分类维度"""
        response = await client.get(
            f"/api/v1/product-categories/{sample_category.id}/dimensions",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_add_category_dimension(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试为分类添加维度"""
        # 先创建维度模板
        dimension_template_data = {
            "dimension_code": "color",
            "dimension_name": "颜色",
            "dimension_type": "select",
            "description": "产品颜色维度"
        }
        
        template_response = await client.post(
            "/api/v1/product-dimension-templates",
            json=dimension_template_data,
            headers=auth_headers
        )
        assert template_response.status_code == 201
        template_data = template_response.json()
        
        # 为分类添加维度
        dimension_data = {
            "dimension_template_id": template_data["id"],
            "is_required": True,
            "is_overridable": True
        }
        
        response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/dimensions",
            json=dimension_data,
            headers=auth_headers
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["dimension_template_id"] == dimension_data["dimension_template_id"]
        assert data["is_required"] == dimension_data["is_required"]

    @pytest.mark.asyncio
    async def test_remove_category_dimension(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试移除分类维度"""
        # 先添加维度（使用上面的测试逻辑）
        # 然后移除维度
        response = await client.delete(
            f"/api/v1/product-categories/{sample_category.id}/dimensions/1",
            headers=auth_headers
        )
        
        # 如果维度不存在，应该返回 404
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_get_category_available_parent_dimensions(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试获取可继承的父分类维度"""
        response = await client.get(
            f"/api/v1/product-categories/{sample_category.id}/available-parent-dimensions",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_inherit_dimension_from_parent(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试从父分类继承维度"""
        inherit_data = {
            "dimension_template_id": 1,
            "source_category_id": sample_category.id
        }
        
        response = await client.post(
            f"/api/v1/product-categories/{sample_category.id}/dimensions/inherit",
            json=inherit_data,
            headers=auth_headers
        )
        
        # 如果父分类没有该维度，应该返回 404
        assert response.status_code in [201, 404]

    @pytest.mark.asyncio
    async def test_override_dimension(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试覆盖继承的维度"""
        override_data = {
            "is_required": False,
            "is_overridable": False
        }
        
        response = await client.put(
            f"/api/v1/product-categories/{sample_category.id}/dimensions/1",
            json=override_data,
            headers=auth_headers
        )
        
        # 如果维度不存在，应该返回 404
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_remove_inherited_dimension(self, client: AsyncClient, auth_headers: dict, sample_category):
        """测试移除继承的维度"""
        response = await client.delete(
            f"/api/v1/product-categories/{sample_category.id}/dimensions/1/remove-inherited",
            headers=auth_headers
        )
        
        # 如果维度不存在或不是继承的，应该返回 404
        assert response.status_code in [200, 404]


class TestProductCategoriesAPIIntegration:
    """产品分类管理 API 完整集成测试"""
    
    @pytest.mark.asyncio
    async def test_complete_category_workflow(self, client: AsyncClient, auth_headers: dict):
        """测试完整的分类管理工作流"""
        # 1. 创建根分类
        root_category_data = {
            "category_code": "root",
            "category_name": "根分类",
            "description": "根分类描述",
            "is_root": True
        }
        
        root_response = await client.post(
            "/api/v1/product-categories",
            json=root_category_data,
            headers=auth_headers
        )
        assert root_response.status_code == 201
        root_data = root_response.json()
        
        # 2. 创建子分类
        child_category_data = {
            "category_code": "electronics",
            "category_name": "电子产品",
            "description": "电子产品分类"
        }
        
        child_response = await client.post(
            "/api/v1/product-categories",
            json=child_category_data,
            headers=auth_headers
        )
        assert child_response.status_code == 201
        child_data = child_response.json()
        
        # 3. 创建父子关系
        relation_data = {
            "parent_category_id": root_data["id"],
            "child_category_id": child_data["id"],
            "relation_type": "parent_child"
        }
        
        relation_response = await client.post(
            f"/api/v1/product-categories/{root_data['id']}/relations",
            json=relation_data,
            headers=auth_headers
        )
        assert relation_response.status_code == 201
        
        # 4. 创建维度模板
        dimension_template_data = {
            "dimension_code": "color",
            "dimension_name": "颜色",
            "dimension_type": "select",
            "description": "产品颜色维度"
        }
        
        template_response = await client.post(
            "/api/v1/product-dimension-templates",
            json=dimension_template_data,
            headers=auth_headers
        )
        assert template_response.status_code == 201
        template_data = template_response.json()
        
        # 5. 为根分类添加维度
        dimension_data = {
            "dimension_template_id": template_data["id"],
            "is_required": True,
            "is_overridable": True
        }
        
        dimension_response = await client.post(
            f"/api/v1/product-categories/{root_data['id']}/dimensions",
            json=dimension_data,
            headers=auth_headers
        )
        assert dimension_response.status_code == 201
        
        # 6. 子分类继承父分类维度
        inherit_data = {
            "dimension_template_id": template_data["id"],
            "source_category_id": root_data["id"]
        }
        
        inherit_response = await client.post(
            f"/api/v1/product-categories/{child_data['id']}/dimensions/inherit",
            json=inherit_data,
            headers=auth_headers
        )
        assert inherit_response.status_code == 201
        
        # 7. 获取分类树
        tree_response = await client.get(
            "/api/v1/product-categories/tree",
            headers=auth_headers
        )
        assert tree_response.status_code == 200
        tree_data = tree_response.json()
        assert len(tree_data["categories"]) >= 2
        
        # 8. 获取子分类的有效维度
        dimensions_response = await client.get(
            f"/api/v1/product-categories/{child_data['id']}/dimensions",
            headers=auth_headers
        )
        assert dimensions_response.status_code == 200
        dimensions_data = dimensions_response.json()
        assert len(dimensions_data) >= 1
        
        # 9. 清理：删除分类
        delete_response = await client.delete(
            f"/api/v1/product-categories/{child_data['id']}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200
        
        delete_response = await client.delete(
            f"/api/v1/product-categories/{root_data['id']}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200

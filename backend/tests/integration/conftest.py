"""
集成测试配置文件

提供集成测试所需的公共 fixtures 和配置
"""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

from app.main import app
from app.core.database import get_async_db, Base
from app.core.jwt_utils import jwt_utils
from app.models.tenant import Tenant
from app.models.user import User
from app.models.product import Product, ProductVariant
from app.models.product_category import ProductCategory, ProductCategoryDimension
from app.models.product_dimension import ProductDimensionTemplate


# 测试数据库配置
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# 创建测试数据库引擎
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
    future=True
)

# 创建测试会话
TestSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """创建事件循环"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def setup_test_db():
    """设置测试数据库"""
    # 创建所有表
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    # 清理测试数据库
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(setup_test_db):
    """创建数据库会话"""
    async with TestSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def client(db_session):
    """创建测试客户端"""
    def override_get_db():
        return db_session
    
    app.dependency_overrides[get_async_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def auth_headers():
    """创建认证头"""
    token = jwt_utils.generate_access_token(
        user_id=1,
        tenant_id=1,
        email="test_user@example.com",
        tenant_name="test_tenant"
    )
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def sample_tenant(db_session: AsyncSession):
    """创建示例租户"""
    tenant = Tenant(
        name="test_tenant",
        domain="test.com",
        is_active=True
    )
    db_session.add(tenant)
    await db_session.commit()
    await db_session.refresh(tenant)
    return tenant


@pytest.fixture
async def sample_user(db_session: AsyncSession, sample_tenant):
    """创建示例用户"""
    user = User(
        tenant_id=sample_tenant.id,
        username="test_user",
        email="test@example.com",
        is_active=True
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def sample_product(db_session: AsyncSession, sample_tenant):
    """创建示例产品"""
    from app.models.product import Product
    
    product = Product(
        tenant_id=sample_tenant.id,
        name="测试产品",
        handle="test-product",
        description="测试产品描述",
        is_active=True
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def sample_category(db_session: AsyncSession, sample_tenant):
    """创建示例分类"""
    from app.models.product_category import ProductCategory
    
    category = ProductCategory(
        tenant_id=sample_tenant.id,
        category_code="test_category",
        category_name="测试分类",
        description="测试分类描述",
        is_root=True
    )
    db_session.add(category)
    await db_session.commit()
    await db_session.refresh(category)
    return category


@pytest.fixture
async def sample_dimension_template(db_session: AsyncSession, sample_tenant):
    """创建示例维度模板"""
    from app.models.product_dimension import ProductDimensionTemplate
    
    template = ProductDimensionTemplate(
        tenant_id=sample_tenant.id,
        dimension_code="test_dimension",
        dimension_name="测试维度",
        dimension_type="select",
        description="测试维度描述"
    )
    db_session.add(template)
    await db_session.commit()
    await db_session.refresh(template)
    return template


@pytest.fixture
async def sample_variant(db_session: AsyncSession, sample_product):
    """创建示例 SKU"""
    from app.models.product import ProductVariant
    
    variant = ProductVariant(
        product_id=sample_product.id,
        sku="TEST-SKU",
        name="测试 SKU",
        price=29.99,
        cost_price=15.00,
        inventory_quantity=100,
        is_active=True
    )
    db_session.add(variant)
    await db_session.commit()
    await db_session.refresh(variant)
    return variant


@pytest.fixture(autouse=True)
async def cleanup_test_data(db_session: AsyncSession):
    """自动清理测试数据"""
    yield
    
    # 清理所有测试数据
    try:
        # 删除所有表的数据
        for table in reversed(Base.metadata.sorted_tables):
            await db_session.execute(f"DELETE FROM {table.name}")
        await db_session.commit()
    except Exception as e:
        await db_session.rollback()
        print(f"清理测试数据时出错: {e}")


# 测试工具函数
class TestUtils:
    """测试工具类"""
    
    @staticmethod
    async def create_test_tenant(db_session: AsyncSession, name: str = "test_tenant") -> Tenant:
        """创建测试租户"""
        tenant = Tenant(
            name=name,
            domain=f"{name}.com",
            is_active=True
        )
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        return tenant
    
    @staticmethod
    async def create_test_user(db_session: AsyncSession, tenant_id: int, username: str = "test_user") -> User:
        """创建测试用户"""
        user = User(
            tenant_id=tenant_id,
            username=username,
            email=f"{username}@example.com",
            is_active=True
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    
    @staticmethod
    async def create_test_product(db_session: AsyncSession, tenant_id: int, name: str = "测试产品") -> Product:
        """创建测试产品"""
        from app.models.product import Product
        
        product = Product(
            tenant_id=tenant_id,
            name=name,
            handle=name.lower().replace(" ", "-"),
            description=f"{name}描述",
            is_active=True
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)
        return product
    
    @staticmethod
    async def create_test_category(db_session: AsyncSession, tenant_id: int, category_code: str = "test_category") -> ProductCategory:
        """创建测试分类"""
        from app.models.product_category import ProductCategory
        
        category = ProductCategory(
            tenant_id=tenant_id,
            category_code=category_code,
            category_name=f"{category_code}分类",
            description=f"{category_code}分类描述",
            is_root=True
        )
        db_session.add(category)
        await db_session.commit()
        await db_session.refresh(category)
        return category
    
    @staticmethod
    async def create_test_dimension_template(db_session: AsyncSession, tenant_id: int, dimension_code: str = "test_dimension") -> ProductDimensionTemplate:
        """创建测试维度模板"""
        from app.models.product_dimension import ProductDimensionTemplate
        
        template = ProductDimensionTemplate(
            tenant_id=tenant_id,
            dimension_code=dimension_code,
            dimension_name=f"{dimension_code}维度",
            dimension_type="select",
            description=f"{dimension_code}维度描述"
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)
        return template


# 测试数据工厂
class TestDataFactory:
    """测试数据工厂"""
    
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session
    
    async def create_tenant_with_user(self, tenant_name: str = "test_tenant", username: str = "test_user") -> tuple[Tenant, User]:
        """创建租户和用户"""
        tenant = await TestUtils.create_test_tenant(self.db_session, tenant_name)
        user = await TestUtils.create_test_user(self.db_session, tenant.id, username)
        return tenant, user
    
    async def create_product_with_variants(self, tenant_id: int, product_name: str = "测试产品", variant_count: int = 3) -> tuple[Product, list[ProductVariant]]:
        """创建产品和 SKU"""
        from app.models.product import ProductVariant
        
        product = await TestUtils.create_test_product(self.db_session, tenant_id, product_name)
        variants = []
        
        for i in range(variant_count):
            variant = ProductVariant(
                product_id=product.id,
                sku=f"{product.handle}-variant-{i+1}",
                name=f"{product_name} 变体 {i+1}",
                price=29.99 + i * 10,
                cost_price=15.00 + i * 5,
                inventory_quantity=100 - i * 10,
                is_active=True
            )
            self.db_session.add(variant)
            variants.append(variant)
        
        await self.db_session.commit()
        for variant in variants:
            await self.db_session.refresh(variant)
        
        return product, variants
    
    async def create_category_with_dimensions(self, tenant_id: int, category_code: str = "test_category", dimension_count: int = 2) -> tuple[ProductCategory, list[ProductDimensionTemplate]]:
        """创建分类和维度"""
        from app.models.product_dimension import ProductDimensionTemplate
        from app.models.product_category import ProductCategoryDimension
        
        category = await TestUtils.create_test_category(self.db_session, tenant_id, category_code)
        dimensions = []
        
        for i in range(dimension_count):
            template = ProductDimensionTemplate(
                tenant_id=tenant_id,
                dimension_code=f"{category_code}_dimension_{i+1}",
                dimension_name=f"{category_code}维度{i+1}",
                dimension_type="select",
                description=f"{category_code}维度{i+1}描述"
            )
            self.db_session.add(template)
            dimensions.append(template)
        
        await self.db_session.commit()
        for template in dimensions:
            await self.db_session.refresh(template)
        
        # 为分类添加维度
        for template in dimensions:
            category_dimension = ProductCategoryDimension(
                category_id=category.id,
                dimension_template_id=template.id,
                source_type="own",
                is_required=True,
                is_overridable=True
            )
            self.db_session.add(category_dimension)
        
        await self.db_session.commit()
        
        return category, dimensions


# 测试断言工具
class TestAssertions:
    """测试断言工具类"""
    
    @staticmethod
    def assert_success_response(response, expected_status_code: int = 200):
        """断言成功响应"""
        assert response.status_code == expected_status_code
        assert response.json() is not None
    
    @staticmethod
    def assert_error_response(response, expected_status_code: int = 400, expected_error_message: str = None):
        """断言错误响应"""
        assert response.status_code == expected_status_code
        data = response.json()
        assert "detail" in data
        if expected_error_message:
            assert expected_error_message in data["detail"]
    
    @staticmethod
    def assert_created_response(response, expected_fields: list = None):
        """断言创建响应"""
        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        if expected_fields:
            for field in expected_fields:
                assert field in data
    
    @staticmethod
    def assert_list_response(response, expected_count: int = None):
        """断言列表响应"""
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if expected_count is not None:
            assert len(data) == expected_count
    
    @staticmethod
    def assert_paginated_response(response, expected_fields: list = None):
        """断言分页响应"""
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "size" in data
        if expected_fields:
            for field in expected_fields:
                assert field in data

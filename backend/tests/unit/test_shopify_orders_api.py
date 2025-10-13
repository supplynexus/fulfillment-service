"""
Shopify Orders API 测试用例
按照测试优先开发原则，先编写测试用例来验证 API 行为
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.main import app
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.shopify_order import ShopifyOrderCreate


class TestShopifyOrdersAPI:
    """Shopify 订单 API 测试类"""
    
    @pytest.fixture
    def client(self):
        """测试客户端"""
        return TestClient(app)
    
    @pytest.fixture
    def mock_auth(self):
        """模拟认证信息"""
        tenant = Tenant(id=1, name="test_tenant", display_name="Test Tenant")
        user = User(id=1, email="test@example.com", full_name="Test User")
        return (tenant, user)
    
    @pytest.fixture
    def sample_order_data(self):
        """示例订单数据"""
        return {
            "shopify_order_id": "gid://shopify/Order/5849204457572",
            "name": "#1001",
            "email": "customer@example.com",
            "total_price": "29.99",
            "currency": "USD",
            "financial_status": "paid",
            "fulfillment_status": "unfulfilled",
            "confirmed": True,
            "closed": False,
            "cancelled": False,
            "customer_data": {
                "id": 12345,
                "email": "customer@example.com",
                "first_name": "John",
                "last_name": "Doe"
            },
            "billing_address": {
                "first_name": "John",
                "last_name": "Doe",
                "address1": "123 Main St",
                "city": "New York",
                "province": "NY",
                "country": "United States",
                "zip": "10001"
            },
            "shipping_address": {
                "first_name": "John",
                "last_name": "Doe",
                "address1": "123 Main St",
                "city": "New York",
                "province": "NY",
                "country": "United States",
                "zip": "10001"
            },
            "line_items": [
                {
                    "id": 67890,
                    "product_id": 123,
                    "variant_id": 456,
                    "title": "Test Product",
                    "variant_title": "Small",
                    "quantity": 1,
                    "price": "29.99"
                }
            ]
        }
    
    def test_create_shopify_order_success(self, client, mock_auth, sample_order_data):
        """测试成功创建 Shopify 订单"""
        # Given: 模拟认证和数据库操作
        with patch('app.core.tenant_auth_dependency.verify_tenant_auth', return_value=mock_auth):
            with patch('app.core.database.get_async_db') as mock_db:
                mock_session = AsyncMock(spec=AsyncSession)
                mock_db.return_value = mock_session
                
                # Mock 数据库查询 - 检查订单是否已存在
                mock_session.execute.return_value.scalar.return_value = None
                
                # Mock 数据库添加和提交
                mock_session.add = AsyncMock()
                mock_session.commit = AsyncMock()
                mock_session.refresh = AsyncMock()
                
                # When: 发送 POST 请求
                response = client.post(
                    "/api/v1/shopify-orders/",
                    json=sample_order_data,
                    headers={
                        "X-Tenant-Name": "test_tenant",
                        "X-User-ID": "1",
                        "X-Timestamp": "1234567890",
                        "X-Nonce": "test_nonce",
                        "X-Signature": "test_signature"
                    }
                )
                
                # Then: 验证响应
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "id" in data
                assert data["shopify_order_id"] == sample_order_data["shopify_order_id"]
    
    def test_create_shopify_order_duplicate(self, client, mock_auth, sample_order_data):
        """测试创建重复的 Shopify 订单"""
        # Given: 模拟订单已存在
        with patch('app.core.tenant_auth_dependency.verify_tenant_auth', return_value=mock_auth):
            with patch('app.core.database.get_async_db') as mock_db:
                mock_session = AsyncMock(spec=AsyncSession)
                mock_db.return_value = mock_session
                
                # Mock 数据库查询 - 订单已存在
                mock_session.execute.return_value.scalar.return_value = 1
                
                # When: 发送 POST 请求
                response = client.post(
                    "/api/v1/shopify-orders/",
                    json=sample_order_data,
                    headers={
                        "X-Tenant-Name": "test_tenant",
                        "X-User-ID": "1",
                        "X-Timestamp": "1234567890",
                        "X-Nonce": "test_nonce",
                        "X-Signature": "test_signature"
                    }
                )
                
                # Then: 验证响应
                assert response.status_code == 400
                data = response.json()
                assert "already exists" in data["detail"].lower()
    
    def test_create_shopify_order_invalid_data(self, client, mock_auth):
        """测试使用无效数据创建 Shopify 订单"""
        # Given: 无效的订单数据（缺少必填字段）
        invalid_data = {
            "shopify_order_id": "",  # 空的订单 ID
            "name": "#1001"
        }
        
        with patch('app.core.tenant_auth_dependency.verify_tenant_auth', return_value=mock_auth):
            with patch('app.core.database.get_async_db') as mock_db:
                mock_session = AsyncMock(spec=AsyncSession)
                mock_db.return_value = mock_session
                
                # When: 发送 POST 请求
                response = client.post(
                    "/api/v1/shopify-orders/",
                    json=invalid_data,
                    headers={
                        "X-Tenant-Name": "test_tenant",
                        "X-User-ID": "1",
                        "X-Timestamp": "1234567890",
                        "X-Nonce": "test_nonce",
                        "X-Signature": "test_signature"
                    }
                )
                
                # Then: 验证响应
                assert response.status_code == 422  # Validation error
    
    def test_get_shopify_orders_success(self, client, mock_auth):
        """测试成功获取 Shopify 订单列表"""
        # Given: 模拟认证和数据库操作
        with patch('app.core.tenant_auth_dependency.verify_tenant_auth', return_value=mock_auth):
            with patch('app.core.database.get_async_db') as mock_db:
                mock_session = AsyncMock(spec=AsyncSession)
                mock_db.return_value = mock_session
                
                # Mock 数据库查询结果
                mock_orders = [
                    {
                        "id": 1,
                        "shopify_order_id": "gid://shopify/Order/5849204457572",
                        "name": "#1001",
                        "total_price": "29.99",
                        "currency": "USD",
                        "financial_status": "paid",
                        "fulfillment_status": "unfulfilled"
                    }
                ]
                mock_session.execute.return_value.scalars.return_value.all.return_value = mock_orders
                mock_session.execute.return_value.scalar.return_value = 1
                
                # When: 发送 GET 请求
                response = client.get(
                    "/api/v1/shopify-orders/",
                    headers={
                        "X-Tenant-Name": "test_tenant",
                        "X-User-ID": "1",
                        "X-Timestamp": "1234567890",
                        "X-Nonce": "test_nonce",
                        "X-Signature": "test_signature"
                    }
                )
                
                # Then: 验证响应
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "orders" in data
                assert len(data["orders"]) == 1
                assert data["total"] == 1
    
    def test_get_shopify_orders_with_filters(self, client, mock_auth):
        """测试使用过滤条件获取 Shopify 订单列表"""
        # Given: 模拟认证和数据库操作
        with patch('app.core.tenant_auth_dependency.verify_tenant_auth', return_value=mock_auth):
            with patch('app.core.database.get_async_db') as mock_db:
                mock_session = AsyncMock(spec=AsyncSession)
                mock_db.return_value = mock_session
                
                # Mock 数据库查询结果
                mock_session.execute.return_value.scalars.return_value.all.return_value = []
                mock_session.execute.return_value.scalar.return_value = 0
                
                # When: 发送带过滤条件的 GET 请求
                response = client.get(
                    "/api/v1/shopify-orders/?financial_status=paid&fulfillment_status=unfulfilled&search=test",
                    headers={
                        "X-Tenant-Name": "test_tenant",
                        "X-User-ID": "1",
                        "X-Timestamp": "1234567890",
                        "X-Nonce": "test_nonce",
                        "X-Signature": "test_signature"
                    }
                )
                
                # Then: 验证响应
                assert response.status_code == 200
                data = response.json()
                assert data["success"] is True
                assert "orders" in data
                assert data["total"] == 0
    
    def test_shopify_orders_unauthorized(self, client, sample_order_data):
        """测试未授权访问 Shopify 订单 API"""
        # When: 发送没有认证头的请求
        response = client.post(
            "/api/v1/shopify-orders/",
            json=sample_order_data
        )
        
        # Then: 验证响应
        assert response.status_code == 401
    
    def test_shopify_orders_invalid_signature(self, client, sample_order_data):
        """测试无效签名访问 Shopify 订单 API"""
        # When: 发送无效签名的请求
        response = client.post(
            "/api/v1/shopify-orders/",
            json=sample_order_data,
            headers={
                "X-Tenant-Name": "test_tenant",
                "X-User-ID": "1",
                "X-Timestamp": "1234567890",
                "X-Nonce": "test_nonce",
                "X-Signature": "invalid_signature"
            }
        )
        
        # Then: 验证响应
        assert response.status_code == 401


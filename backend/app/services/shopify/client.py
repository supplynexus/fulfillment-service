"""
Shopify GraphQL API 客户端
用于批量获取订单和其他数据
"""
import asyncio
import aiohttp
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from datetime import datetime, timedelta
import logging

from app.core.config import settings
from app.utils.retry_client import RetryableHTTPClient, create_shopify_retry_config, retry_async

logger = logging.getLogger(__name__)


class ShopifyGraphQLClient:
    """Shopify GraphQL API 客户端"""
    
    def __init__(self, shop_name: str, access_token: str):
        self.shop_name = shop_name
        self.access_token = access_token
        self.base_url = f"https://{shop_name}.myshopify.com/admin/api/unstable/graphql.json"
        self.headers = {
            'Content-Type': 'application/json',
            'X-Shopify-Access-Token': access_token
        }
        # 创建针对Shopify优化的重试配置
        self.retry_config = create_shopify_retry_config()
    
    @retry_async(max_retries=5, base_delay=2.0, max_delay=60.0)
    async def _make_request(self, query: str, variables: Dict = None) -> Dict[str, Any]:
        """发送 GraphQL 请求（带重试机制）"""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        
        # 使用可重试的HTTP客户端
        async with RetryableHTTPClient(self.retry_config) as client:
            response = await client.post(
                self.base_url,
                headers=self.headers,
                json_data=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            )
            
            if response.status == 200:
                data = await response.json()
                if 'errors' in data:
                    logger.error(f"GraphQL errors: {data['errors']}")
                    raise Exception(f"GraphQL errors: {data['errors']}")
                return data.get('data', {})
            else:
                error_text = await response.text()
                logger.error(f"HTTP {response.status}: {error_text}")
                raise Exception(f"HTTP {response.status}: {error_text}")
    
    async def get_shop_info(self) -> Dict[str, Any]:
        """获取商店基本信息"""
        query = """
        query {
          shop {
            name
            email
            myshopifyDomain
            currencyCode
            timezoneAbbreviation
            plan {
              displayName
            }
          }
        }
        """
        result = await self._make_request(query)
        return result.get('shop', {})
    
    async def get_orders_batch(
        self, 
        limit: int = 250,
        cursor: Optional[str] = None,
        query_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量获取订单
        
        Args:
            limit: 每次获取的订单数量 (最大250)
            cursor: 分页游标
            query_filter: 订单过滤条件
        """
        # 构建查询参数
        args = [f"first: {min(limit, 250)}"]
        if cursor:
            args.append(f'after: "{cursor}"')
        if query_filter:
            args.append(f'query: "{query_filter}"')
        
        query = f"""
        query {{
          orders({", ".join(args)}) {{
            edges {{
              cursor
              node {{
                id
                name
                email
                phone
                createdAt
                updatedAt
                processedAt
                displayFinancialStatus
                displayFulfillmentStatus
                totalPriceSet {{
                  shopMoney {{
                    amount
                    currencyCode
                  }}
                }}
                subtotalPriceSet {{
                  shopMoney {{
                    amount
                    currencyCode
                  }}
                }}
                totalTaxSet {{
                  shopMoney {{
                    amount
                    currencyCode
                  }}
                }}
                customer {{
                  id
                  displayName
                  email
                  phone
                }}
                shippingAddress {{
                  firstName
                  lastName
                  company
                  address1
                  address2
                  city
                  province
                  country
                  zip
                  phone
                }}
                billingAddress {{
                  firstName
                  lastName
                  company
                  address1
                  address2
                  city
                  province
                  country
                  zip
                  phone
                }}
                lineItems(first: 50) {{
                  edges {{
                    node {{
                      id
                      title
                      quantity
                      variantTitle
                      vendor
                      sku
                      fulfillmentStatus
                      originalUnitPriceSet {{
                        shopMoney {{
                          amount
                          currencyCode
                        }}
                      }}
                      discountedUnitPriceSet {{
                        shopMoney {{
                          amount
                          currencyCode
                        }}
                      }}
                    }}
                  }}
                }}
                fulfillments {{
                  id
                  status
                  createdAt
                  updatedAt
                }}
                note
                tags
                metafields(first: 10) {{
                  edges {{
                    node {{
                      key
                      value
                      namespace
                    }}
                  }}
                }}
              }}
            }}
            pageInfo {{
              hasNextPage
              hasPreviousPage
              startCursor
              endCursor
            }}
          }}
        }}
        """
        
        return await self._make_request(query)
    
    async def get_all_orders(
        self, 
        query_filter: Optional[str] = None,
        max_orders: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        获取所有订单（自动分页）
        
        Args:
            query_filter: 订单过滤条件，例如:
                - "created_at:>2024-01-01"
                - "financial_status:paid"
                - "fulfillment_status:unfulfilled"
            max_orders: 最大订单数量限制
        
        Yields:
            单个订单数据
        """
        cursor = None
        total_fetched = 0
        
        while True:
            try:
                # 获取一批订单
                result = await self.get_orders_batch(
                    limit=250,
                    cursor=cursor,
                    query_filter=query_filter
                )
                
                orders_data = result.get('orders', {})
                edges = orders_data.get('edges', [])
                page_info = orders_data.get('pageInfo', {})
                
                # 处理这批订单
                for edge in edges:
                    order = edge.get('node', {})
                    yield order
                    
                    total_fetched += 1
                    if max_orders and total_fetched >= max_orders:
                        logger.info(f"达到最大订单数量限制: {max_orders}")
                        return
                
                # 检查是否还有下一页
                if not page_info.get('hasNextPage', False):
                    logger.info(f"所有订单获取完成，总计: {total_fetched}")
                    break
                
                # 更新游标
                cursor = page_info.get('endCursor')
                logger.info(f"已获取 {total_fetched} 个订单，继续获取下一批...")
                
                # 避免请求过于频繁
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"获取订单批次时出错: {e}")
                raise

    async def get_recent_orders(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        获取最近的订单
        
        Args:
            hours: 最近几小时的订单
        """
        # 计算时间过滤条件
        since_time = datetime.utcnow() - timedelta(hours=hours)
        query_filter = f"created_at:>={since_time.isoformat()}"
        
        orders = []
        async for order in self.get_all_orders(query_filter=query_filter):
            orders.append(order)
        
        return orders

    async def get_unfulfilled_orders(self) -> List[Dict[str, Any]]:
        """获取未履约的订单"""
        query_filter = "fulfillment_status:unfulfilled"
        
        orders = []
        async for order in self.get_all_orders(query_filter=query_filter):
            orders.append(order)
        
        return orders

    async def get_paid_orders(self) -> List[Dict[str, Any]]:
        """获取已支付的订单"""
        query_filter = "financial_status:paid"
        
        orders = []
        async for order in self.get_all_orders(query_filter=query_filter):
            orders.append(order)
        
        return orders

    async def get_products_batch(
        self, 
        limit: int = 250,
        cursor: Optional[str] = None,
        query_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        批量获取商品
        
        Args:
            limit: 每次获取的商品数量 (最大250)
            cursor: 分页游标
            query_filter: 商品过滤条件
        """
        # 构建查询参数
        args = [f"first: {min(limit, 250)}"]
        if cursor:
            args.append(f'after: "{cursor}"')
        if query_filter:
            args.append(f'query: "{query_filter}"')
        
        query = f"""
        query {{
          products({", ".join(args)}) {{
            edges {{
              cursor
              node {{
                id
                title
                description
                status
                createdAt
                updatedAt
                tags
                images(first: 10) {{
                  edges {{
                    node {{
                      id
                      url
                      altText
                    }}
                  }}
                }}
                variants(first: 50) {{
                  edges {{
                    node {{
                      id
                      title
                      sku
                      price
                      compareAtPrice
                      inventoryQuantity
                    }}
                  }}
                }}
              }}
            }}
            pageInfo {{
              hasNextPage
              endCursor
            }}
          }}
        }}
        """
        
        result = await self._make_request(query)
        return result.get('products', {})
    
    async def get_all_products(
        self,
        query_filter: Optional[str] = None,
        max_products: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        获取所有商品
        
        Args:
            query_filter: 商品过滤条件，例如:
                - "updated_at:>2024-01-01"
                - "status:active"
                - "available_for_sale:true"
            max_products: 最大商品数量限制
        
        Yields:
            单个商品数据
        """
        cursor = None
        total_fetched = 0
        
        while True:
            try:
                # 获取一批商品
                result = await self.get_products_batch(
                    limit=250,
                    cursor=cursor,
                    query_filter=query_filter
                )
                
                products_data = result
                edges = products_data.get('edges', [])
                page_info = products_data.get('pageInfo', {})
                
                # 处理这批商品
                for edge in edges:
                    product = edge.get('node', {})
                    yield product
                    
                    total_fetched += 1
                    if max_products and total_fetched >= max_products:
                        logger.info(f"达到最大商品数量限制: {max_products}")
                        return
                
                # 检查是否还有下一页
                if not page_info.get('hasNextPage', False):
                    logger.info(f"所有商品获取完成，总计: {total_fetched}")
                    break
                
                # 更新游标
                cursor = page_info.get('endCursor')
                logger.info(f"已获取 {total_fetched} 个商品，继续获取下一批...")
                
                # 避免请求过于频繁
                await asyncio.sleep(0.5)
                
            except Exception as e:
                logger.error(f"获取商品批次时出错: {e}")
                raise

    async def get_recent_products(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        获取最近的商品
        
        Args:
            hours: 最近几小时的商品
        """
        # 计算时间过滤条件
        since_time = datetime.utcnow() - timedelta(hours=hours)
        query_filter = f"updated_at:>={since_time.isoformat()}"
        
        products = []
        async for product in self.get_all_products(query_filter=query_filter):
            products.append(product)
        
        return products

    async def get_active_products(self) -> List[Dict[str, Any]]:
        """获取活跃的商品"""
        query_filter = "status:active"
        
        products = []
        async for product in self.get_all_products(query_filter=query_filter):
            products.append(product)
        
        return products

    async def get_available_products(self) -> List[Dict[str, Any]]:
        """获取可购买的商品"""
        query_filter = "available_for_sale:true"
        
        products = []
        async for product in self.get_all_products(query_filter=query_filter):
            products.append(product)
        
        return products


# 工厂函数
def create_shopify_client(shop_name: str, access_token: str) -> ShopifyGraphQLClient:
    """创建 Shopify 客户端实例
    
    Args:
        shop_name: Shopify 商店名称（必需）
        access_token: Shopify 访问令牌（必需）
    
    Returns:
        ShopifyGraphQLClient 实例
    
    Raises:
        ValueError: 如果缺少必需的参数
    """
    if not shop_name or not access_token:
        raise ValueError("shop_name 和 access_token 都是必需的参数")
    
    return ShopifyGraphQLClient(shop_name, access_token)

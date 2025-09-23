"""
Shopify Product Service for GraphQL Admin API
"""

import httpx
import asyncio
from typing import List, Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.external_system import ExternalSystem
from app.models.product_new import Product
from app.services.product_mapper import ProductMapper
from app.core.logging import get_logger

logger = get_logger(__name__)


class ShopifyProductService:
    """Shopify Product service for GraphQL API operations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.graphql_url = "https://{shop}.myshopify.com/admin/api/unstable/graphql.json"
    
    async def get_shopify_system(self, tenant_id: int) -> Optional[ExternalSystem]:
        """Get Shopify external system configuration"""
        try:
            result = await self.db.execute(
                select(ExternalSystem).where(
                    ExternalSystem.tenant_id == tenant_id,
                    ExternalSystem.system_type == "SHOPIFY"
                )
            )
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error getting Shopify system for tenant {tenant_id}: {e}")
            return None
    
    async def fetch_and_save_products(
        self, 
        tenant_id: int, 
        limit: int = 10,
        after: Optional[str] = None,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch products from Shopify and save to database
        """
        try:
            # Fetch products from Shopify
            shopify_response = await self.fetch_products(tenant_id, limit, after, query)
            
            # Get Shopify system for mapping
            shopify_system = await self.get_shopify_system(tenant_id)
            if not shopify_system:
                raise Exception("Shopify system not found")
            
            # Map and save products
            mapped_products = ProductMapper.map_shopify_products_list(
                shopify_response, tenant_id, shopify_system.id
            )
            
            saved_products = []
            for product_data in mapped_products:
                saved_product = await self._save_or_update_product(product_data)
                saved_products.append(saved_product)
            
            # Add saved products info to response
            shopify_response["saved_products"] = {
                "count": len(saved_products),
                "products": [{"id": p.id, "title": p.title} for p in saved_products]
            }
            
            return shopify_response
            
        except Exception as e:
            logger.error(f"Error fetching and saving products for tenant {tenant_id}: {e}")
            raise
    
    async def fetch_and_save_product_by_id(self, tenant_id: int, product_id: str) -> Dict[str, Any]:
        """
        Fetch a single product by ID from Shopify and save to database
        """
        try:
            # Fetch product from Shopify
            shopify_response = await self.fetch_product_by_id(tenant_id, product_id)
            
            # Get Shopify system for mapping
            shopify_system = await self.get_shopify_system(tenant_id)
            if not shopify_system:
                raise Exception("Shopify system not found")
            
            # Map and save product
            mapped_product = ProductMapper.map_single_shopify_product(
                shopify_response, tenant_id, shopify_system.id
            )
            
            if mapped_product:
                saved_product = await self._save_or_update_product(mapped_product)
                shopify_response["saved_product"] = {
                    "id": saved_product.id,
                    "title": saved_product.title
                }
            
            return shopify_response
            
        except Exception as e:
            logger.error(f"Error fetching and saving product {product_id} for tenant {tenant_id}: {e}")
            raise
    
    async def _save_or_update_product(self, product_data: Dict[str, Any]) -> Product:
        """
        Save or update a product in the database
        """
        try:
            # Check if product already exists
            external_product_id = product_data.get("external_product_id")
            tenant_id = product_data.get("tenant_id")
            
            if external_product_id:
                # Try to find existing product
                result = await self.db.execute(
                    select(Product).where(
                        Product.external_product_id == external_product_id,
                        Product.tenant_id == tenant_id
                    )
                )
                existing_product = result.scalar_one_or_none()
                
                if existing_product:
                    # Update existing product
                    for key, value in product_data.items():
                        if hasattr(existing_product, key):
                            setattr(existing_product, key, value)
                    
                    await self.db.commit()
                    await self.db.refresh(existing_product)
                    logger.info(f"Updated product: {existing_product.title}")
                    return existing_product
            
            # Create new product
            new_product = Product(**product_data)
            self.db.add(new_product)
            await self.db.commit()
            await self.db.refresh(new_product)
            
            logger.info(f"Created new product: {new_product.title}")
            return new_product
            
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Error saving product: {e}")
            raise
    
    async def get_local_products(
        self, 
        tenant_id: int, 
        skip: int = 0, 
        limit: int = 10,
        product_type: Optional[str] = None,
        vendor: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Product]:
        """
        Get products from local database
        """
        try:
            query = select(Product).where(Product.tenant_id == tenant_id)
            
            if product_type:
                query = query.where(Product.product_type == product_type)
            if vendor:
                query = query.where(Product.vendor == vendor)
            if status:
                query = query.where(Product.status == status)
            
            query = query.offset(skip).limit(limit)
            
            result = await self.db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            logger.error(f"Error getting local products for tenant {tenant_id}: {e}")
            raise
    
    async def get_local_product_by_id(self, tenant_id: int, product_id: int) -> Optional[Product]:
        """
        Get a single product from local database
        """
        try:
            result = await self.db.execute(
                select(Product).where(
                    Product.id == product_id,
                    Product.tenant_id == tenant_id
                )
            )
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Error getting local product {product_id} for tenant {tenant_id}: {e}")
            raise
    
    async def fetch_products(
        self, 
        tenant_id: int, 
        limit: int = 10,
        after: Optional[str] = None,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Fetch products from Shopify using GraphQL
        """
        try:
            # Get Shopify system configuration
            shopify_system = await self.get_shopify_system(tenant_id)
            if not shopify_system:
                raise Exception("Shopify system not found")
            
            # Parse credentials
            credentials = shopify_system.credentials
            shop_name = credentials.get("shop_id") or credentials.get("shop_name")
            access_token = credentials.get("access_token")
            
            if not shop_name or not access_token:
                raise Exception("Invalid Shopify credentials")
            
            # Construct GraphQL query
            graphql_query = self._build_products_query(limit, after, query)
            
            # Make GraphQL request
            headers = {
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": access_token
            }
            
            url = self.graphql_url.format(shop=shop_name)
            payload = {"query": graphql_query}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                if "errors" in data:
                    logger.error(f"GraphQL errors: {data['errors']}")
                    raise Exception(f"GraphQL errors: {data['errors']}")
                
                return data
                
        except Exception as e:
            logger.error(f"Error fetching products for tenant {tenant_id}: {e}")
            raise
    
    async def fetch_product_by_id(self, tenant_id: int, product_id: str) -> Dict[str, Any]:
        """
        Fetch a single product by ID from Shopify
        """
        try:
            # Get Shopify system configuration
            shopify_system = await self.get_shopify_system(tenant_id)
            if not shopify_system:
                raise Exception("Shopify system not found")
            
            # Parse credentials
            credentials = shopify_system.credentials
            shop_name = credentials.get("shop_id") or credentials.get("shop_name")
            access_token = credentials.get("access_token")
            
            if not shop_name or not access_token:
                raise Exception("Invalid Shopify credentials")
            
            # Construct GraphQL query
            graphql_query = self._build_single_product_query(product_id)
            
            # Make GraphQL request
            headers = {
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": access_token
            }
            
            url = self.graphql_url.format(shop=shop_name)
            payload = {"query": graphql_query}
            
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                
                data = response.json()
                
                if "errors" in data:
                    logger.error(f"GraphQL errors: {data['errors']}")
                    raise Exception(f"GraphQL errors: {data['errors']}")
                
                return data
                
        except Exception as e:
            logger.error(f"Error fetching product {product_id} for tenant {tenant_id}: {e}")
            raise
    
    def _build_products_query(
        self, 
        limit: int = 10, 
        after: Optional[str] = None,
        query: Optional[str] = None
    ) -> str:
        """Build GraphQL query for products list"""
        
        # Build arguments
        args = [f"first: {limit}"]
        if after:
            args.append(f'after: "{after}"')
        if query:
            args.append(f'query: "{query}"')
        
        args_str = ", ".join(args)
        
        return f"""
        query GetProducts {{
            products({args_str}) {{
                nodes {{
                    id
                    title
                    handle
                    description
                    descriptionHtml
                    productType
                    vendor
                    tags
                    status
                    createdAt
                    updatedAt
                    publishedAt
                    totalInventory
                    tracksInventory
                    hasOnlyDefaultVariant
                    hasOutOfStockVariants
                    priceRangeV2 {{
                        minVariantPrice {{
                            amount
                            currencyCode
                        }}
                        maxVariantPrice {{
                            amount
                            currencyCode
                        }}
                    }}
                    options {{
                        id
                        name
                        position
                        values
                    }}
                    variants(first: 10) {{
                        nodes {{
                            id
                            title
                            sku
                            barcode
                            price
                            compareAtPrice
                            inventoryQuantity
                            selectedOptions {{
                                name
                                value
                            }}
                        }}
                    }}
                    media(first: 10) {{
                        nodes {{
                            id
                            alt
                            mediaContentType
                            ... on MediaImage {{
                                image {{
                                    url
                                    width
                                    height
                                    altText
                                }}
                            }}
                            ... on Video {{
                                sources {{
                                    url
                                    format
                                    height
                                    width
                                    mimeType
                                }}
                            }}
                        }}
                    }}
                    seo {{
                        title
                        description
                    }}
                    onlineStoreUrl
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
    
    def _build_single_product_query(self, product_id: str) -> str:
        """Build GraphQL query for single product"""
        
        return f"""
        query GetProduct {{
            product(id: "{product_id}") {{
                id
                title
                handle
                description
                descriptionHtml
                productType
                vendor
                tags
                status
                createdAt
                updatedAt
                publishedAt
                totalInventory
                tracksInventory
                hasOnlyDefaultVariant
                hasOutOfStockVariants
                priceRangeV2 {{
                    minVariantPrice {{
                        amount
                        currencyCode
                    }}
                    maxVariantPrice {{
                        amount
                        currencyCode
                    }}
                }}
                options {{
                    id
                    name
                    position
                    values
                }}
                variants(first: 50) {{
                    nodes {{
                        id
                        title
                        sku
                        barcode
                        price
                        compareAtPrice
                        inventoryQuantity
                        selectedOptions {{
                            name
                            value
                        }}
                        media(first: 10) {{
                            nodes {{
                                id
                                alt
                                mediaContentType
                                ... on MediaImage {{
                                    image {{
                                        url
                                        width
                                        height
                                        altText
                                    }}
                                }}
                            }}
                        }}
                    }}
                }}
                media(first: 20) {{
                    nodes {{
                        id
                        alt
                        mediaContentType
                        ... on MediaImage {{
                            image {{
                                url
                                width
                                height
                                altText
                            }}
                        }}
                        ... on Video {{
                            sources {{
                                url
                                format
                                height
                                width
                                mimeType
                            }}
                        }}
                        ... on ExternalVideo {{
                            host
                            originUrl
                        }}
                        ... on Model3d {{
                            sources {{
                                url
                                format
                                mimeType
                            }}
                        }}
                    }}
                }}
                seo {{
                    title
                    description
                }}
                onlineStoreUrl
                collections(first: 10) {{
                    nodes {{
                        id
                        title
                        handle
                    }}
                }}
                metafields(first: 20) {{
                    nodes {{
                        id
                        namespace
                        key
                        value
                        type
                    }}
                }}
            }}
        }}
        """
    
    async def search_products(
        self, 
        tenant_id: int, 
        search_term: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Search products by term
        """
        return await self.fetch_products(
            tenant_id=tenant_id,
            limit=limit,
            query=search_term
        )
    
    async def get_products_by_type(
        self, 
        tenant_id: int, 
        product_type: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get products by product type
        """
        return await self.fetch_products(
            tenant_id=tenant_id,
            limit=limit,
            query=f'product_type:"{product_type}"'
        )
    
    async def get_products_by_vendor(
        self, 
        tenant_id: int, 
        vendor: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get products by vendor
        """
        return await self.fetch_products(
            tenant_id=tenant_id,
            limit=limit,
            query=f'vendor:"{vendor}"'
        )
    
    async def get_products_by_tag(
        self, 
        tenant_id: int, 
        tag: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get products by tag
        """
        return await self.fetch_products(
            tenant_id=tenant_id,
            limit=limit,
            query=f'tag:"{tag}"'
        )
    
    async def get_products_by_status(
        self, 
        tenant_id: int, 
        status: str,
        limit: int = 10
    ) -> Dict[str, Any]:
        """
        Get products by status (ACTIVE, DRAFT, ARCHIVED)
        """
        return await self.fetch_products(
            tenant_id=tenant_id,
            limit=limit,
            query=f'status:{status}'
        )

"""
Shopify Products API endpoints
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_db
from app.core.timestamp_auth_middleware import verify_timestamp_auth
from app.services.shopify_product_service import ShopifyProductService

router = APIRouter()


@router.get("/shopify/products", response_model=dict)
async def get_shopify_products(
    tenant_id: int = Query(..., description="Tenant ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of products to retrieve"),
    after: str = Query(None, description="Cursor for pagination"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Get Shopify products list
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Initialize Shopify product service
        shopify_service = ShopifyProductService(db)
        
        # Fetch products
        result = await shopify_service.fetch_products(
            tenant_id=tenant_id,
            limit=limit,
            after=after
        )
        
        return {
            "success": True,
            "data": result.get("data", {}),
            "message": "Products retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving products: {str(e)}"
        )


@router.post("/shopify/products/sync", response_model=dict)
async def sync_shopify_products(
    tenant_id: int = Query(..., description="Tenant ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of products to sync"),
    after: str = Query(None, description="Cursor for pagination"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Fetch Shopify products and save to local database
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Initialize Shopify product service
        shopify_service = ShopifyProductService(db)
        
        # Fetch and save products
        result = await shopify_service.fetch_and_save_products(
            tenant_id=tenant_id,
            limit=limit,
            after=after
        )
        
        saved_info = result.get("saved_products", {})
        
        return {
            "success": True,
            "data": result.get("data", {}),
            "saved_products": saved_info,
            "message": f"Successfully synced {saved_info.get('count', 0)} products"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing products: {str(e)}"
        )


@router.post("/shopify/products/{product_id}/sync", response_model=dict)
async def sync_shopify_product(
    product_id: str,
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Fetch a single Shopify product and save to local database
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Initialize Shopify product service
        shopify_service = ShopifyProductService(db)
        
        # Fetch and save product
        result = await shopify_service.fetch_and_save_product_by_id(
            tenant_id=tenant_id,
            product_id=product_id
        )
        
        saved_info = result.get("saved_product", {})
        
        return {
            "success": True,
            "data": result.get("data", {}),
            "saved_product": saved_info,
            "message": f"Successfully synced product: {saved_info.get('title', 'Unknown')}"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error syncing product: {str(e)}"
        )


@router.get("/products", response_model=dict)
async def get_local_products(
    tenant_id: int = Query(..., description="Tenant ID"),
    skip: int = Query(0, ge=0, description="Number of products to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of products to retrieve"),
    product_type: str = Query(None, description="Filter by product type"),
    vendor: str = Query(None, description="Filter by vendor"),
    status: str = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Get products from local database
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Initialize Shopify product service
        shopify_service = ShopifyProductService(db)
        
        # Get local products
        products = await shopify_service.get_local_products(
            tenant_id=tenant_id,
            skip=skip,
            limit=limit,
            product_type=product_type,
            vendor=vendor,
            status=status
        )
        
        # Convert to dict for response
        products_data = []
        for product in products:
            product_dict = {
                "id": product.id,
                "title": product.title,
                "handle": product.handle,
                "description": product.description,
                "product_type": product.product_type,
                "vendor": product.vendor,
                "tags": product.tags,
                "status": product.status,
                "total_inventory": product.total_inventory,
                "tracks_inventory": product.tracks_inventory,
                "has_out_of_stock_variants": product.has_out_of_stock_variants,
                "has_only_default_variant": product.has_only_default_variant,
                "price": float(product.price) if product.price else None,
                "compare_at_price": float(product.compare_at_price) if product.compare_at_price else None,
                "seo": product.seo,
                "online_store_url": product.online_store_url,
                "published_at": product.published_at.isoformat() if product.published_at else None,
                "variants": product.variants,
                "images": product.images,
                "is_active": product.is_active,
                "is_available": product.is_available,
                "created_at": product.created_at.isoformat() if product.created_at else None,
                "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                "last_synced_at": product.last_synced_at.isoformat() if product.last_synced_at else None,
                "external_product_id": product.external_product_id,
                "external_system_id": product.external_system_id
            }
            products_data.append(product_dict)
        
        return {
            "success": True,
            "data": {
                "products": products_data,
                "total": len(products_data),
                "skip": skip,
                "limit": limit
            },
            "message": "Local products retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving local products: {str(e)}"
        )


@router.get("/products/{product_id}", response_model=dict)
async def get_local_product(
    product_id: int,
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Get a single product from local database
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Initialize Shopify product service
        shopify_service = ShopifyProductService(db)
        
        # Get local product
        product = await shopify_service.get_local_product_by_id(
            tenant_id=tenant_id,
            product_id=product_id
        )
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Convert to dict for response
        product_dict = {
            "id": product.id,
            "title": product.title,
            "handle": product.handle,
            "description": product.description,
            "product_type": product.product_type,
            "vendor": product.vendor,
            "tags": product.tags,
            "status": product.status,
            "total_inventory": product.total_inventory,
            "tracks_inventory": product.tracks_inventory,
            "has_out_of_stock_variants": product.has_out_of_stock_variants,
            "has_only_default_variant": product.has_only_default_variant,
            "price": float(product.price) if product.price else None,
            "compare_at_price": float(product.compare_at_price) if product.compare_at_price else None,
            "seo": product.seo,
            "online_store_url": product.online_store_url,
            "published_at": product.published_at.isoformat() if product.published_at else None,
            "variants": product.variants,
            "images": product.images,
            "is_active": product.is_active,
            "is_available": product.is_available,
            "created_at": product.created_at.isoformat() if product.created_at else None,
            "updated_at": product.updated_at.isoformat() if product.updated_at else None,
            "last_synced_at": product.last_synced_at.isoformat() if product.last_synced_at else None,
            "external_product_id": product.external_product_id,
            "external_system_id": product.external_system_id,
            "external_data": product.external_data
        }
        
        return {
            "success": True,
            "data": product_dict,
            "message": "Product retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving product: {str(e)}"
        )


@router.get("/shopify/products/search", response_model=dict)
async def search_shopify_products(
    tenant_id: int = Query(..., description="Tenant ID"),
    q: str = Query(..., description="Search term"),
    limit: int = Query(10, ge=1, le=50, description="Number of products to retrieve"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Search Shopify products
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Initialize Shopify product service
        shopify_service = ShopifyProductService(db)
        
        # Search products
        result = await shopify_service.search_products(
            tenant_id=tenant_id,
            search_term=q,
            limit=limit
        )
        
        return {
            "success": True,
            "data": result.get("data", {}),
            "message": "Products search completed successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error searching products: {str(e)}"
        )


@router.get("/shopify/products/type/{product_type}", response_model=dict)
async def get_shopify_products_by_type(
    product_type: str,
    tenant_id: int = Query(..., description="Tenant ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of products to retrieve"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Get Shopify products by product type
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Initialize Shopify product service
        shopify_service = ShopifyProductService(db)
        
        # Get products by type
        result = await shopify_service.get_products_by_type(
            tenant_id=tenant_id,
            product_type=product_type,
            limit=limit
        )
        
        return {
            "success": True,
            "data": result.get("data", {}),
            "message": f"Products of type '{product_type}' retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving products by type: {str(e)}"
        )


@router.get("/shopify/products/vendor/{vendor}", response_model=dict)
async def get_shopify_products_by_vendor(
    vendor: str,
    tenant_id: int = Query(..., description="Tenant ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of products to retrieve"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Get Shopify products by vendor
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Initialize Shopify product service
        shopify_service = ShopifyProductService(db)
        
        # Get products by vendor
        result = await shopify_service.get_products_by_vendor(
            tenant_id=tenant_id,
            vendor=vendor,
            limit=limit
        )
        
        return {
            "success": True,
            "data": result.get("data", {}),
            "message": f"Products from vendor '{vendor}' retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving products by vendor: {str(e)}"
        )


@router.get("/shopify/products/tag/{tag}", response_model=dict)
async def get_shopify_products_by_tag(
    tag: str,
    tenant_id: int = Query(..., description="Tenant ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of products to retrieve"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Get Shopify products by tag
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Initialize Shopify product service
        shopify_service = ShopifyProductService(db)
        
        # Get products by tag
        result = await shopify_service.get_products_by_tag(
            tenant_id=tenant_id,
            tag=tag,
            limit=limit
        )
        
        return {
            "success": True,
            "data": result.get("data", {}),
            "message": f"Products with tag '{tag}' retrieved successfully"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving products by tag: {str(e)}"
        )


@router.get("/shopify/products/status/{status}", response_model=dict)
async def get_shopify_products_by_status(
    status: str,
    tenant_id: int = Query(..., description="Tenant ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of products to retrieve"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Get Shopify products by status (ACTIVE, DRAFT, ARCHIVED)
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Validate status
        valid_statuses = ["ACTIVE", "DRAFT", "ARCHIVED"]
        if status.upper() not in valid_statuses:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
            )
        
        # Initialize Shopify product service
        shopify_service = ShopifyProductService(db)
        
        # Get products by status
        result = await shopify_service.get_products_by_status(
            tenant_id=tenant_id,
            status=status.upper(),
            limit=limit
        )
        
        return {
            "success": True,
            "data": result.get("data", {}),
            "message": f"Products with status '{status.upper()}' retrieved successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving products by status: {str(e)}"
        )


@router.get("/shopify/products/test-connection", response_model=dict)
async def test_shopify_products_connection(
    tenant_id: int = Query(..., description="Tenant ID"),
    db: AsyncSession = Depends(get_async_db),
    auth: dict = Depends(verify_timestamp_auth)
) -> Any:
    """
    Test Shopify products API connection
    """
    try:
        # Verify tenant access
        if auth.get("tenant_id") != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied to this tenant"
            )
        
        # Initialize Shopify product service
        shopify_service = ShopifyProductService(db)
        
        # Test connection by fetching first product
        result = await shopify_service.fetch_products(
            tenant_id=tenant_id,
            limit=1
        )
        
        products = result.get("data", {}).get("products", {}).get("nodes", [])
        
        return {
            "success": True,
            "message": "Shopify products API connection successful",
            "products_count": len(products),
            "configuration": {
                "tenant_id": tenant_id,
                "api_version": "unstable",
                "endpoint": "products"
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"Shopify products connection failed: {str(e)}",
            "configuration": None
        }

"""
Product Mapper for mapping external system data to internal models
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, timezone

from app.models.product_new import Product
from app.core.logging import get_logger

logger = get_logger(__name__)


class ProductMapper:
    """Maps external system product data to internal Product model"""
    
    @staticmethod
    def map_shopify_product(shopify_data: Dict[str, Any], tenant_id: int, external_system_id: int) -> Dict[str, Any]:
        """
        Map Shopify product data to internal Product model format
        
        Args:
            shopify_data: Raw Shopify product data
            tenant_id: Tenant ID
            external_system_id: External system ID
            
        Returns:
            Dict containing mapped product data
        """
        try:
            # Extract basic product information
            product_id = shopify_data.get("id", "")
            title = shopify_data.get("title", "")
            handle = shopify_data.get("handle", "")
            description = shopify_data.get("description", "")
            description_html = shopify_data.get("descriptionHtml", "")
            product_type = shopify_data.get("productType", "")
            vendor = shopify_data.get("vendor", "")
            tags = shopify_data.get("tags", [])
            status = shopify_data.get("status", "ACTIVE")
            
            # Extract timestamps with proper timezone handling
            created_at = shopify_data.get("createdAt")
            updated_at = shopify_data.get("updatedAt")
            published_at = shopify_data.get("publishedAt")
            
            # Parse timestamps if they exist - ensure timezone-aware
            if created_at:
                # Handle both "Z" and "+00:00" formats
                if created_at.endswith("Z"):
                    created_at = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                else:
                    created_at = datetime.fromisoformat(created_at)
            if updated_at:
                if updated_at.endswith("Z"):
                    updated_at = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
                else:
                    updated_at = datetime.fromisoformat(updated_at)
            if published_at:
                if published_at.endswith("Z"):
                    published_at = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                else:
                    published_at = datetime.fromisoformat(published_at)
            
            # Extract inventory information
            total_inventory = shopify_data.get("totalInventory")
            tracks_inventory = shopify_data.get("tracksInventory", True)
            has_out_of_stock_variants = shopify_data.get("hasOutOfStockVariants", False)
            has_only_default_variant = shopify_data.get("hasOnlyDefaultVariant", True)
            
            # Extract pricing information
            price_range = shopify_data.get("priceRangeV2", {})
            min_price = price_range.get("minVariantPrice", {})
            max_price = price_range.get("maxVariantPrice", {})
            
            # Use min price as primary price, or None if not available
            price = None
            if min_price and min_price.get("amount"):
                try:
                    price = Decimal(min_price["amount"])
                except (ValueError, TypeError):
                    price = None
            
            # Extract SEO information
            seo_data = shopify_data.get("seo", {})
            seo = {
                "title": seo_data.get("title"),
                "description": seo_data.get("description")
            } if seo_data else None
            
            # Extract online store URL
            online_store_url = shopify_data.get("onlineStoreUrl")
            
            # Extract variants
            variants_data = shopify_data.get("variants", {}).get("nodes", [])
            variants = []
            for variant in variants_data:
                variant_info = {
                    "id": variant.get("id"),
                    "title": variant.get("title"),
                    "sku": variant.get("sku"),
                    "barcode": variant.get("barcode"),
                    "price": variant.get("price"),
                    "compare_at_price": variant.get("compareAtPrice"),
                    "inventory_quantity": variant.get("inventoryQuantity"),
                    "selected_options": [
                        {
                            "name": opt.get("name"),
                            "value": opt.get("value")
                        }
                        for opt in variant.get("selectedOptions", [])
                    ]
                }
                variants.append(variant_info)
            
            # Extract media/images
            media_data = shopify_data.get("media", {}).get("nodes", [])
            images = []
            for media in media_data:
                if media.get("mediaContentType") == "IMAGE":
                    image_data = media.get("image", {})
                    image_info = {
                        "id": media.get("id"),
                        "alt": media.get("alt"),
                        "url": image_data.get("url"),
                        "width": image_data.get("width"),
                        "height": image_data.get("height"),
                        "alt_text": image_data.get("altText")
                    }
                    images.append(image_info)
                elif media.get("mediaContentType") == "VIDEO":
                    video_info = {
                        "id": media.get("id"),
                        "alt": media.get("alt"),
                        "type": "video",
                        "sources": media.get("sources", [])
                    }
                    images.append(video_info)
            
            # Extract options
            options_data = shopify_data.get("options", [])
            options = []
            for option in options_data:
                option_info = {
                    "id": option.get("id"),
                    "name": option.get("name"),
                    "values": option.get("values", [])
                }
                options.append(option_info)
            
            # Build the mapped product data
            mapped_product = {
                "tenant_id": tenant_id,
                "external_system_id": external_system_id,
                "external_product_id": product_id,
                "title": title,
                "handle": handle,
                "description": description,
                "product_type": product_type,
                "vendor": vendor,
                "tags": tags,
                "status": status,
                "total_inventory": total_inventory,
                "tracks_inventory": tracks_inventory,
                "has_out_of_stock_variants": has_out_of_stock_variants,
                "has_only_default_variant": has_only_default_variant,
                "price": price,
                "seo": seo,
                "online_store_url": online_store_url,
                "variants": variants,
                "images": images,
                "options": options,
                "external_data": {
                    "description_html": description_html,
                    "price_range": price_range,
                    "raw_data": shopify_data
                },
                "created_at": created_at,
                "updated_at": updated_at,
                "published_at": published_at,
                "last_synced_at": datetime.now(timezone.utc),
            }
            
            return mapped_product
            
        except Exception as e:
            raise Exception(f"Error mapping Shopify product: {e}")
    
    @staticmethod
    def map_shopify_products_list(
        shopify_response: Dict[str, Any], 
        tenant_id: int, 
        external_system_id: int
    ) -> List[Dict[str, Any]]:
        """
        Map a list of Shopify products from GraphQL response
        
        Args:
            shopify_response: Raw Shopify GraphQL response
            tenant_id: Tenant ID
            external_system_id: External system ID
            
        Returns:
            List of mapped product data
        """
        try:
            products_data = shopify_response.get("data", {}).get("products", {}).get("nodes", [])
            mapped_products = []
            
            for product_data in products_data:
                mapped_product = ProductMapper.map_shopify_product(
                    product_data, tenant_id, external_system_id
                )
                mapped_products.append(mapped_product)
            
            return mapped_products
            
        except Exception as e:
            logger.error(f"Error mapping Shopify products list: {e}")
            raise
    
    @staticmethod
    def map_single_shopify_product(
        shopify_response: Dict[str, Any], 
        tenant_id: int, 
        external_system_id: int
    ) -> Optional[Dict[str, Any]]:
        """
        Map a single Shopify product from GraphQL response
        
        Args:
            shopify_response: Raw Shopify GraphQL response
            tenant_id: Tenant ID
            external_system_id: External system ID
            
        Returns:
            Mapped product data or None
        """
        try:
            product_data = shopify_response.get("data", {}).get("product")
            if not product_data:
                return None
            
            return ProductMapper.map_shopify_product(
                product_data, tenant_id, external_system_id
            )
            
        except Exception as e:
            logger.error(f"Error mapping single Shopify product: {e}")
            raise

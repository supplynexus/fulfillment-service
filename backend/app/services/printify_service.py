"""
Printify API service for product and order management
"""

import logging
from typing import List, Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)


class PrintifyService:
    """Service for interacting with Printify API"""
    
    def __init__(self, printify_api_token: str):
        self.base_url = "https://api.printify.com/v1"
        self.headers = {
            "Authorization": f"Bearer {printify_api_token}",
            "Content-Type": "application/json",
        }
    
    async def get_shops(self) -> List[Dict[str, Any]]:
        """Get all Printify shops"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/shops.json",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get Printify shops: {e}")
            return []
    
    async def get_products(self, shop_id: str) -> List[Dict[str, Any]]:
        """Get products from a Printify shop"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/shops/{shop_id}/products.json",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json().get("data", [])
        except Exception as e:
            logger.error(f"Failed to get Printify products: {e}")
            return []
    
    async def create_order(self, shop_id: str, order_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create an order in Printify"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/shops/{shop_id}/orders.json",
                    headers=self.headers,
                    json=order_data
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to create Printify order: {e}")
            return None
    
    async def get_order(self, shop_id: str, order_id: str) -> Optional[Dict[str, Any]]:
        """Get order details from Printify"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/shops/{shop_id}/orders/{order_id}.json",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get Printify order: {e}")
            return None

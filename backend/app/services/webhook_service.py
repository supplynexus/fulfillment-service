"""
Webhook service for handling Shopify webhook events
"""

import logging
import hmac
import hashlib
from typing import Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


class WebhookService:
    """Service for processing webhook events"""
    
    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature from Shopify"""
        try:
            # Calculate expected signature
            expected_signature = hmac.new(
                settings.WEBHOOK_SECRET.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Compare signatures
            expected = f"sha256={expected_signature}"
            return hmac.compare_digest(expected, signature)
        except Exception as e:
            logger.error(f"Failed to verify webhook signature: {e}")
            return False
    
    async def process_order_created(self, order_data: Dict[str, Any]) -> bool:
        """Process order created webhook"""
        try:
            logger.info(f"Processing order created webhook for order {order_data.get('id')}")
            # Add order processing logic here
            return True
        except Exception as e:
            logger.error(f"Failed to process order created webhook: {e}")
            return False
    
    async def process_order_updated(self, order_data: Dict[str, Any]) -> bool:
        """Process order updated webhook"""
        try:
            logger.info(f"Processing order updated webhook for order {order_data.get('id')}")
            # Add order update processing logic here
            return True
        except Exception as e:
            logger.error(f"Failed to process order updated webhook: {e}")
            return False
    
    async def process_order_fulfilled(self, order_data: Dict[str, Any]) -> bool:
        """Process order fulfilled webhook"""
        try:
            logger.info(f"Processing order fulfilled webhook for order {order_data.get('id')}")
            # Add fulfillment processing logic here
            return True
        except Exception as e:
            logger.error(f"Failed to process order fulfilled webhook: {e}")
            return False

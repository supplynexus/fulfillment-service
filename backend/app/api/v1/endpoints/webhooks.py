"""
Webhook endpoints for Shopify and Printify
"""

from fastapi import APIRouter, Request, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
import json
import hmac
import hashlib

from app.core.config import settings
from app.core.database import get_async_db
from app.services.webhook_service import WebhookService
from app.tasks.order_tasks import process_shopify_order

router = APIRouter()


def verify_shopify_webhook(data: bytes, signature: str) -> bool:
    """
    Verify Shopify webhook signature
    """
    computed_hmac = hmac.new(
        settings.WEBHOOK_SECRET.encode('utf-8'),
        data,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(computed_hmac, signature.replace('sha256=', ''))


@router.post("/shopify/orders/create")
async def shopify_order_created(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Handle Shopify order creation webhook
    """
    body = await request.body()
    signature = request.headers.get('X-Shopify-Hmac-Sha256', '')
    
    if not verify_shopify_webhook(body, signature):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")
    
    try:
        order_data = json.loads(body)
        
        # Extract shop domain from webhook headers
        shop_domain = request.headers.get('X-Shopify-Shop-Domain', '')
        if shop_domain:
            # Remove .myshopify.com if present
            shop_domain = shop_domain.replace('.myshopify.com', '')
            # Add shop domain to order data for processing
            order_data['shop_domain'] = shop_domain
        
        webhook_service = WebhookService(db)
        
        # Log webhook receipt
        await webhook_service.log_webhook(
            source="shopify",
            event_type="order_created",
            data=order_data
        )
        
        # Process order asynchronously
        background_tasks.add_task(process_shopify_order, order_data)
        
        return {"status": "success", "message": "Order webhook received"}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")


@router.post("/printify/orders/status")
async def printify_order_status(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Handle Printify order status webhook
    """
    body = await request.body()
    
    try:
        status_data = json.loads(body)
        webhook_service = WebhookService(db)
        
        # Log webhook receipt
        await webhook_service.log_webhook(
            source="printify",
            event_type="order_status_update",
            data=status_data
        )
        
        # Update order status
        await webhook_service.update_order_status(status_data)
        
        return {"status": "success", "message": "Status update received"}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

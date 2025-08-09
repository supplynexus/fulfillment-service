"""
Product management endpoints
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_async_db
from app.schemas.product import ProductResponse
from app.services.printify_service import PrintifyService

router = APIRouter()


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get available products from Printify
    """
    printify_service = PrintifyService()
    products = await printify_service.get_products(skip=skip, limit=limit)
    return products


@router.get("/catalog")
async def sync_product_catalog(
    db: AsyncSession = Depends(get_async_db)
):
    """
    Sync product catalog from Printify
    """
    printify_service = PrintifyService()
    result = await printify_service.sync_catalog()
    return {"message": "Product catalog sync initiated", "task_id": result}

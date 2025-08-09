"""
Customer management endpoints
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_async_db
from app.schemas.customer import CustomerResponse, CustomerCreate, CustomerUpdate
from app.services.customer_service import CustomerService

router = APIRouter()


@router.get("/", response_model=List[CustomerResponse])
async def get_customers(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get all customers
    """
    customer_service = CustomerService(db)
    customers = await customer_service.get_multi(skip=skip, limit=limit)
    return customers


@router.post("/", response_model=CustomerResponse)
async def create_customer(
    customer_in: CustomerCreate,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Create new customer
    """
    customer_service = CustomerService(db)
    customer = await customer_service.create(obj_in=customer_in)
    return customer


@router.get("/{customer_id}", response_model=CustomerResponse)
async def get_customer(
    customer_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    Get customer by ID
    """
    customer_service = CustomerService(db)
    customer = await customer_service.get(id=customer_id)
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer

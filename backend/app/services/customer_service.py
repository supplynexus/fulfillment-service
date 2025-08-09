"""
Customer service for business logic
"""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.customer import Customer


class CustomerService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get(self, id: int) -> Optional[Customer]:
        """Get customer by ID"""
        result = await self.db.execute(select(Customer).where(Customer.id == id))
        return result.scalar_one_or_none()

    async def get_multi(self, skip: int = 0, limit: int = 100) -> List[Customer]:
        """Get multiple customers"""
        result = await self.db.execute(
            select(Customer).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def create(self, obj_in: dict) -> Customer:
        """Create new customer"""
        db_customer = Customer(**obj_in)
        self.db.add(db_customer)
        await self.db.commit()
        await self.db.refresh(db_customer)
        return db_customer

    async def update(self, db_obj: Customer, obj_in: dict) -> Customer:
        """Update customer"""
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

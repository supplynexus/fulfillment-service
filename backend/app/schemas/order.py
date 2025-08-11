"""
Order schemas
"""

from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel


class OrderResponse(BaseModel):
    id: int
    order_number: str
    customer_id: int
    status: str
    total_amount: float
    currency: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    orders: List[OrderResponse]
    total: int
    skip: int
    limit: int

"""
Customer schemas
"""

from typing import Optional
from pydantic import BaseModel, EmailStr
from app.schemas.base import BaseResponse


class CustomerBase(BaseModel):
    name: str
    email: EmailStr
    shopify_store_url: str
    business_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    webhook_enabled: bool = True
    auto_fulfillment: bool = True


class CustomerCreate(CustomerBase):
    shopify_access_token: str
    shopify_api_secret: Optional[str] = None
    printify_shop_id: Optional[str] = None


class CustomerUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    shopify_store_url: Optional[str] = None
    business_name: Optional[str] = None
    contact_person: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    webhook_enabled: Optional[bool] = None
    auto_fulfillment: Optional[bool] = None


class CustomerResponse(CustomerBase, BaseResponse):
    id: int
    is_active: bool
    owner_id: int

"""
External system schemas
"""

from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

from app.models.external_system import ExternalSystemType


class ExternalSystemBase(BaseModel):
    """Base external system schema"""
    system_type: str = Field(..., description="Type of external system")
    name: str = Field(..., description="Human readable name")
    external_system_id: str = Field(..., description="External system's real ID (e.g., shop1.myshopify.com)")
    base_url: Optional[str] = Field(None, description="API base URL")
    webhook_url: Optional[str] = Field(None, description="Webhook endpoint URL")
    credentials: Dict[str, Any] = Field(default_factory=dict, description="System credentials")
    settings: Dict[str, Any] = Field(default_factory=dict, description="System-specific settings")
    sync_enabled: bool = Field(True, description="Enable automatic sync")
    webhook_enabled: bool = Field(True, description="Enable webhook processing")
    sync_interval_minutes: int = Field(60, description="Sync interval in minutes")


class ExternalSystemCreate(ExternalSystemBase):
    """Schema for creating external system"""
    pass


class ExternalSystemUpdate(BaseModel):
    """Schema for updating external system"""
    system_type: Optional[str] = Field(None, description="Type of external system")
    name: Optional[str] = Field(None, description="Human readable name")
    external_system_id: Optional[str] = Field(None, description="External system's real ID (e.g., shop1.myshopify.com)")
    base_url: Optional[str] = Field(None, description="API base URL")
    webhook_url: Optional[str] = Field(None, description="Webhook endpoint URL")
    credentials: Optional[Dict[str, Any]] = Field(None, description="System credentials")
    settings: Optional[Dict[str, Any]] = Field(None, description="System-specific settings")
    sync_enabled: Optional[bool] = Field(None, description="Enable automatic sync")
    webhook_enabled: Optional[bool] = Field(None, description="Enable webhook processing")
    sync_interval_minutes: Optional[int] = Field(None, description="Sync interval in minutes")
    is_active: Optional[bool] = Field(None, description="System active status")


class ExternalSystemResponse(ExternalSystemBase):
    """Schema for external system response"""
    id: int
    tenant_id: int
    external_id: Optional[str] = None  # Deprecated field
    is_active: bool
    last_sync_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ExternalSystemSecureResponse(ExternalSystemBase):
    """Secure schema for external system response - no sensitive IDs"""
    id_hashid: str = Field(..., description="Hashed system ID for frontend use")
    external_id: Optional[str] = None  # Deprecated field
    is_active: bool
    last_sync_at: Optional[datetime] = None
    last_product_sync_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ExternalSystemListResponse(BaseModel):
    """Schema for external system list response"""
    external_systems: list[ExternalSystemResponse]
    total: int
    skip: int
    limit: int


class ExternalSystemSecureListResponse(BaseModel):
    """Secure schema for external system list response - no sensitive IDs"""
    external_systems: list[ExternalSystemSecureResponse]
    total: int
    skip: int
    limit: int


class ExternalSystemTestResponse(BaseModel):
    """Schema for external system connection test response"""
    message: str
    system_type: str
    system_name: str
    status: str
    details: Optional[Dict[str, Any]] = None
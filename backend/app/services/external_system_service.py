"""
External system management service
"""

import json
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.external_system import ExternalSystem, ExternalSystemType
from app.core.security import encrypt_data, decrypt_data


class ExternalSystemService:
    """Service for managing external system integrations"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_external_system(
        self,
        tenant_id: int,
        system_type: ExternalSystemType,
        name: str,
        credentials: Dict[str, Any],
        base_url: Optional[str] = None,
        webhook_url: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None
    ) -> ExternalSystem:
        """Create a new external system integration"""
        
        # Encrypt sensitive credentials
        encrypted_credentials = {}
        for key, value in credentials.items():
            if value:  # Only encrypt non-empty values
                encrypted_credentials[key] = encrypt_data(str(value))
        
        external_system = ExternalSystem(
            tenant_id=tenant_id,
            system_type=system_type,
            name=name,
            base_url=base_url,
            webhook_url=webhook_url,
            credentials=encrypted_credentials,
            settings=settings or {}
        )
        
        self.db.add(external_system)
        await self.db.commit()
        await self.db.refresh(external_system)
        
        return external_system
    
    async def get_external_system(
        self,
        external_system_id: int,
        tenant_id: Optional[int] = None
    ) -> Optional[ExternalSystem]:
        """Get external system by ID"""
        
        query = select(ExternalSystem).where(ExternalSystem.id == external_system_id)
        if tenant_id:
            query = query.where(ExternalSystem.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_external_systems_by_tenant(
        self,
        tenant_id: int,
        system_type: Optional[ExternalSystemType] = None,
        active_only: bool = True
    ) -> List[ExternalSystem]:
        """Get all external systems for a tenant"""
        
        query = select(ExternalSystem).where(ExternalSystem.tenant_id == tenant_id)
        
        if system_type:
            query = query.where(ExternalSystem.system_type == system_type)
        
        if active_only:
            query = query.where(ExternalSystem.is_active == True)
        
        # Order by system type and name for better organization
        query = query.order_by(ExternalSystem.system_type, ExternalSystem.name)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_external_systems_by_type(
        self,
        tenant_id: int,
        system_type: ExternalSystemType,
        active_only: bool = True
    ) -> List[ExternalSystem]:
        """Get all external systems of a specific type for a tenant"""
        
        return await self.get_external_systems_by_tenant(
            tenant_id=tenant_id,
            system_type=system_type,
            active_only=active_only
        )
    
    async def get_shopify_stores(
        self,
        tenant_id: int,
        active_only: bool = True
    ) -> List[ExternalSystem]:
        """Get all Shopify stores for a tenant"""
        
        return await self.get_external_systems_by_type(
            tenant_id=tenant_id,
            system_type=ExternalSystemType.SHOPIFY,
            active_only=active_only
        )
    
    async def get_printify_accounts(
        self,
        tenant_id: int,
        active_only: bool = True
    ) -> List[ExternalSystem]:
        """Get all Printify accounts for a tenant"""
        
        return await self.get_external_systems_by_type(
            tenant_id=tenant_id,
            system_type=ExternalSystemType.PRINTIFY,
            active_only=active_only
        )
    
    async def update_external_system(
        self,
        external_system_id: int,
        tenant_id: int,
        **kwargs
    ) -> Optional[ExternalSystem]:
        """Update external system"""
        
        # Get the external system first
        external_system = await self.get_external_system(external_system_id, tenant_id)
        if not external_system:
            return None
        
        # Handle credentials encryption
        if "credentials" in kwargs:
            encrypted_credentials = {}
            for key, value in kwargs["credentials"].items():
                if value:  # Only encrypt non-empty values
                    encrypted_credentials[key] = encrypt_data(str(value))
            kwargs["credentials"] = encrypted_credentials
        
        # Update the external system
        stmt = (
            update(ExternalSystem)
            .where(ExternalSystem.id == external_system_id, ExternalSystem.tenant_id == tenant_id)
            .values(**kwargs)
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
        
        # Return updated external system
        return await self.get_external_system(external_system_id, tenant_id)
    
    async def delete_external_system(
        self,
        external_system_id: int,
        tenant_id: int
    ) -> bool:
        """Delete external system (soft delete by setting is_active=False)"""
        
        result = await self.update_external_system(
            external_system_id,
            tenant_id,
            is_active=False
        )
        
        return result is not None
    
    async def get_decrypted_credentials(
        self,
        external_system_id: int,
        tenant_id: int
    ) -> Optional[Dict[str, str]]:
        """Get decrypted credentials for an external system"""
        
        external_system = await self.get_external_system(external_system_id, tenant_id)
        if not external_system:
            return None
        
        # Decrypt credentials
        decrypted_credentials = {}
        for key, encrypted_value in external_system.credentials.items():
            try:
                decrypted_credentials[key] = decrypt_data(encrypted_value)
            except Exception:
                # If decryption fails, skip this credential
                continue
        
        return decrypted_credentials
    
    async def update_sync_status(
        self,
        external_system_id: int,
        tenant_id: int,
        last_sync_at: Optional[str] = None
    ) -> bool:
        """Update the last sync timestamp for an external system"""
        
        update_data = {}
        if last_sync_at:
            update_data["last_sync_at"] = last_sync_at
        
        result = await self.update_external_system(
            external_system_id,
            tenant_id,
            **update_data
        )
        
        return result is not None
    
    async def get_active_sync_systems(
        self,
        tenant_id: Optional[int] = None
    ) -> List[ExternalSystem]:
        """Get all active external systems that have sync enabled"""
        
        query = select(ExternalSystem).where(
            ExternalSystem.is_active == True,
            ExternalSystem.sync_enabled == True
        )
        
        if tenant_id:
            query = query.where(ExternalSystem.tenant_id == tenant_id)
        
        result = await self.db.execute(query)
        return result.scalars().all()

"""
External data management service
"""

from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from datetime import datetime

from app.models.external_data import ExternalData, ExternalDataType
from app.models.external_system import ExternalSystemType


class ExternalDataService:
    """Service for managing external data"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def store_external_data(
        self,
        external_system_id: int,
        tenant_id: int,
        data_type: ExternalDataType,
        external_id: str,
        raw_data: Dict[str, Any],
        external_reference: Optional[str] = None,
        processed_data: Optional[Dict[str, Any]] = None
    ) -> ExternalData:
        """Store data from external system"""
        
        # Check if data already exists
        existing_data = await self.get_external_data(
            external_system_id=external_system_id,
            data_type=data_type,
            external_id=external_id
        )
        
        if existing_data:
            # Update existing data
            stmt = (
                update(ExternalData)
                .where(ExternalData.id == existing_data.id)
                .values(
                    raw_data=raw_data,
                    processed_data=processed_data,
                    external_reference=external_reference,
                    last_synced_at=datetime.utcnow(),
                    sync_version=existing_data.sync_version + 1,
                    updated_at=datetime.utcnow()
                )
            )
            await self.db.execute(stmt)
            await self.db.commit()
            
            # Return updated data
            return await self.get_external_data(
                external_system_id=external_system_id,
                data_type=data_type,
                external_id=external_id
            )
        else:
            # Create new data
            external_data = ExternalData(
                external_system_id=external_system_id,
                tenant_id=tenant_id,
                data_type=data_type,
                external_id=external_id,
                external_reference=external_reference,
                raw_data=raw_data,
                processed_data=processed_data,
                last_synced_at=datetime.utcnow()
            )
            
            self.db.add(external_data)
            await self.db.commit()
            await self.db.refresh(external_data)
            
            return external_data
    
    async def get_external_data(
        self,
        external_system_id: int,
        data_type: ExternalDataType,
        external_id: str
    ) -> Optional[ExternalData]:
        """Get specific external data"""
        
        result = await self.db.execute(
            select(ExternalData).where(
                ExternalData.external_system_id == external_system_id,
                ExternalData.data_type == data_type,
                ExternalData.external_id == external_id
            )
        )
        return result.scalar_one_or_none()
    
    async def get_external_data_by_tenant(
        self,
        tenant_id: int,
        data_type: Optional[ExternalDataType] = None,
        external_system_id: Optional[int] = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 100
    ) -> List[ExternalData]:
        """Get external data for a tenant"""
        
        query = select(ExternalData).where(ExternalData.tenant_id == tenant_id)
        
        if data_type:
            query = query.where(ExternalData.data_type == data_type)
        
        if external_system_id:
            query = query.where(ExternalData.external_system_id == external_system_id)
        
        if active_only:
            query = query.where(ExternalData.is_active == True)
        
        query = query.offset(skip).limit(limit).order_by(ExternalData.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_processing_status(
        self,
        external_data_id: int,
        status: str,
        processed_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> bool:
        """Update processing status of external data"""
        
        update_data = {
            "processing_status": status,
            "is_processed": status == "completed"
        }
        
        if processed_data is not None:
            update_data["processed_data"] = processed_data
        
        if error_message is not None:
            update_data["error_message"] = error_message
        
        stmt = (
            update(ExternalData)
            .where(ExternalData.id == external_data_id)
            .values(**update_data)
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
        
        return True
    
    async def get_unprocessed_data(
        self,
        tenant_id: Optional[int] = None,
        data_type: Optional[ExternalDataType] = None
    ) -> List[ExternalData]:
        """Get unprocessed external data"""
        
        query = select(ExternalData).where(
            ExternalData.is_processed == False,
            ExternalData.is_active == True
        )
        
        if tenant_id:
            query = query.where(ExternalData.tenant_id == tenant_id)
        
        if data_type:
            query = query.where(ExternalData.data_type == data_type)
        
        query = query.order_by(ExternalData.created_at.asc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def delete_external_data(
        self,
        external_data_id: int,
        tenant_id: int
    ) -> bool:
        """Soft delete external data"""
        
        stmt = (
            update(ExternalData)
            .where(
                ExternalData.id == external_data_id,
                ExternalData.tenant_id == tenant_id
            )
            .values(is_active=False)
        )
        
        await self.db.execute(stmt)
        await self.db.commit()
        
        return True
    
    async def get_data_statistics(
        self,
        tenant_id: int
    ) -> Dict[str, Any]:
        """Get statistics about external data for a tenant"""
        
        # Get counts by data type
        result = await self.db.execute(
            select(ExternalData.data_type, ExternalData.processing_status)
            .where(ExternalData.tenant_id == tenant_id, ExternalData.is_active == True)
        )
        
        data = result.all()
        
        stats = {
            "total_records": len(data),
            "by_data_type": {},
            "by_status": {
                "pending": 0,
                "processing": 0,
                "completed": 0,
                "failed": 0
            }
        }
        
        for data_type, status in data:
            # Count by data type
            if data_type.value not in stats["by_data_type"]:
                stats["by_data_type"][data_type.value] = 0
            stats["by_data_type"][data_type.value] += 1
            
            # Count by status
            if status in stats["by_status"]:
                stats["by_status"][status] += 1
        
        return stats

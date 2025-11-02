"""
Printify Sync API endpoints
同步 Printify 商品数据到本地数据库
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Body
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.core.logging import get_logger
from app.core.hashids_utils import decode_id
from app.models.tenant import Tenant
from app.models.user import User
from app.services.printify_service import PrintifyService
from app.services.printify_product_service import PrintifyProductService

logger = get_logger(__name__)

router = APIRouter()


class SyncProductsRequest(BaseModel):
    external_system_id_hashid: str
    product_ids: Optional[List[str]] = None


class SyncProductsResponse(BaseModel):
    message: str
    total_synced: int
    total_errors: int


@router.post("/sync-products", response_model=SyncProductsResponse)
async def sync_printify_products(
    request: SyncProductsRequest,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """同步 Printify 商品到本地数据库"""
    tenant, user = auth
    
    try:
        logger.info("🔄 开始同步 Printify 商品", 
                   tenant_id=tenant.id,
                   external_system_id_hashid=request.external_system_id_hashid,
                   product_ids=request.product_ids)
        
        # 解码外部系统 ID
        try:
            external_system_id = decode_id(request.external_system_id_hashid)
            logger.info(f"✅ 外部系统ID解码成功: {request.external_system_id_hashid} -> {external_system_id}")
        except Exception as e:
            logger.error(f"❌ 外部系统ID解码失败: {str(e)}")
            raise HTTPException(status_code=400, detail="Invalid external system ID")
        
        # 获取外部系统信息
        from app.models.external_system import ExternalSystem
        from sqlalchemy import select
        
        stmt = select(ExternalSystem).where(
            ExternalSystem.id == external_system_id,
            ExternalSystem.tenant_id == tenant.id
        )
        result = await db.execute(stmt)
        external_system = result.scalar_one_or_none()
        
        if not external_system:
            logger.error(f"❌ 外部系统不存在: external_system_id={external_system_id}")
            raise HTTPException(status_code=404, detail="External system not found")
        
        # 获取 Printify 服务
        # 从外部系统获取 API token
        from app.core.security import decrypt_data
        
        encrypted_access_token = external_system.credentials.get('access_token') if external_system.credentials else None
        if not encrypted_access_token:
            logger.error(f"❌ 外部系统缺少 access_token: external_system_id={external_system_id}")
            raise HTTPException(status_code=400, detail="External system missing access token")
        
        try:
            api_token = decrypt_data(encrypted_access_token)
            logger.info(f"✅ 凭据解密成功: external_system_id={external_system_id}")
        except Exception as e:
            logger.error(f"❌ 凭据解密失败: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Failed to decrypt credentials: {str(e)}")
        
        printify_service = PrintifyService(api_token)
        
        # 获取店铺信息
        stores = await printify_service.get_shops()
        if not stores:
            logger.error(f"❌ 未找到 Printify 店铺: external_system_id={external_system_id}")
            raise HTTPException(status_code=404, detail="No Printify stores found")
        
        # 同步商品
        total_synced = 0
        total_errors = 0
        
        for store in stores:
            try:
                logger.info(f"🔄 开始同步店铺商品: {store.get('title', store.get('name', 'Unknown Store'))}")
                
                # 获取店铺商品
                products = await printify_service.get_products(store['id'])
                
                if products:
                    # 如果指定了商品ID列表，只同步指定的商品
                    if request.product_ids:
                        products = [p for p in products if p.get('id') in request.product_ids]
                        logger.info(f"ℹ️ 只同步指定商品: {len(products)} 个")
                    
                    if products:
                        # 同步到本地数据库
                        product_service = PrintifyProductService(db)
                        result = await product_service.sync_products_from_api(
                            tenant_id=tenant.id,
                            external_system_id=external_system_id,
                            api_products=products
                        )
                        
                        total_synced += result['synced']
                        total_errors += result['errors']
                        
                        logger.info(f"✅ 店铺商品同步完成: {store.get('title', store.get('name', 'Unknown Store'))}", **result)
                    else:
                        logger.info(f"ℹ️ 没有找到指定的商品: {store.get('title', store.get('name', 'Unknown Store'))}")
                else:
                    logger.info(f"ℹ️ 店铺无商品: {store.get('title', store.get('name', 'Unknown Store'))}")
                    
            except Exception as e:
                logger.error(f"❌ 同步店铺商品失败: {store.get('title', store.get('name', 'Unknown Store'))}", error=str(e))
                total_errors += 1
        
        logger.info("✅ Printify 商品同步完成", 
                   total_synced=total_synced,
                   total_errors=total_errors)
        
        return SyncProductsResponse(
            message="Printify products synced successfully",
            total_synced=total_synced,
            total_errors=total_errors
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ 同步 Printify 商品失败: {str(e)}")
        import traceback
        logger.error(f"   异常堆栈: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Failed to sync Printify products: {str(e)}")


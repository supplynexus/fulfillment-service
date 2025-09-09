"""
Routing rules API endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_async_db
from app.core.tenant_auth_dependency import verify_tenant_auth
from app.models.tenant import Tenant
from app.models.user import User
from app.models.scm_order import RoutingRule
from app.schemas.scm_order import (
    RoutingRuleCreate,
    RoutingRuleResponse,
    RoutingRuleListResponse
)

router = APIRouter()


@router.get("/", response_model=RoutingRuleListResponse)
async def get_routing_rules(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(100, ge=1, le=1000, description="Number of records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    target_system_type: Optional[str] = Query(None, description="Filter by target system type"),
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> RoutingRuleListResponse:
    """
    获取路由规则列表
    """
    tenant, user = auth
    
    # 构建查询
    query = select(RoutingRule).where(RoutingRule.tenant_id == tenant.id)
    
    # 应用过滤器
    if is_active is not None:
        query = query.where(RoutingRule.is_active == is_active)
    if target_system_type:
        query = query.where(RoutingRule.target_system_type == target_system_type)
    
    # 获取总数
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # 分页查询
    query = query.order_by(RoutingRule.priority.asc(), RoutingRule.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    routing_rules = result.scalars().all()
    
    # 转换为响应格式
    routing_rule_responses = [
        RoutingRuleResponse.from_orm(rule) for rule in routing_rules
    ]
    
    return RoutingRuleListResponse(
        routing_rules=routing_rule_responses,
        total=total,
        skip=skip,
        limit=limit
    )


@router.get("/{rule_id}", response_model=RoutingRuleResponse)
async def get_routing_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> RoutingRuleResponse:
    """
    获取路由规则详情
    """
    tenant, user = auth
    
    result = await db.execute(
        select(RoutingRule).where(
            RoutingRule.id == rule_id,
            RoutingRule.tenant_id == tenant.id
        )
    )
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    
    return RoutingRuleResponse.from_orm(rule)


@router.post("/", response_model=RoutingRuleResponse)
async def create_routing_rule(
    rule_data: RoutingRuleCreate,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> RoutingRuleResponse:
    """
    创建路由规则
    """
    tenant, user = auth
    
    # 创建路由规则
    routing_rule = RoutingRule(
        tenant_id=tenant.id,
        name=rule_data.name,
        description=rule_data.description,
        conditions=rule_data.conditions,
        target_system_type=rule_data.target_system_type,
        target_system_id=rule_data.target_system_id,
        priority=rule_data.priority,
        is_active=rule_data.is_active
    )
    
    db.add(routing_rule)
    await db.commit()
    await db.refresh(routing_rule)
    
    return RoutingRuleResponse.from_orm(routing_rule)


@router.put("/{rule_id}", response_model=RoutingRuleResponse)
async def update_routing_rule(
    rule_id: int,
    name: Optional[str] = None,
    description: Optional[str] = None,
    conditions: Optional[dict] = None,
    target_system_type: Optional[str] = None,
    target_system_id: Optional[str] = None,
    priority: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
) -> RoutingRuleResponse:
    """
    更新路由规则
    """
    tenant, user = auth
    
    result = await db.execute(
        select(RoutingRule).where(
            RoutingRule.id == rule_id,
            RoutingRule.tenant_id == tenant.id
        )
    )
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    
    # 更新字段
    if name is not None:
        rule.name = name
    if description is not None:
        rule.description = description
    if conditions is not None:
        rule.conditions = conditions
    if target_system_type is not None:
        rule.target_system_type = target_system_type
    if target_system_id is not None:
        rule.target_system_id = target_system_id
    if priority is not None:
        rule.priority = priority
    if is_active is not None:
        rule.is_active = is_active
    
    await db.commit()
    await db.refresh(rule)
    
    return RoutingRuleResponse.from_orm(rule)


@router.delete("/{rule_id}")
async def delete_routing_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    删除路由规则
    """
    tenant, user = auth
    
    result = await db.execute(
        select(RoutingRule).where(
            RoutingRule.id == rule_id,
            RoutingRule.tenant_id == tenant.id
        )
    )
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    
    await db.delete(rule)
    await db.commit()
    
    return {"message": "Routing rule deleted successfully"}


@router.post("/{rule_id}/test")
async def test_routing_rule(
    rule_id: int,
    test_data: dict,
    db: AsyncSession = Depends(get_async_db),
    auth: tuple[Tenant, User] = Depends(verify_tenant_auth)
):
    """
    测试路由规则
    """
    tenant, user = auth
    
    result = await db.execute(
        select(RoutingRule).where(
            RoutingRule.id == rule_id,
            RoutingRule.tenant_id == tenant.id
        )
    )
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Routing rule not found")
    
    # 简单的规则测试逻辑
    test_results = []
    
    if "line_items" in test_data:
        for item in test_data["line_items"]:
            matches = _item_matches_rule(item, rule.conditions)
            test_results.append({
                "item": item,
                "matches": matches,
                "rule_conditions": rule.conditions
            })
    
    return {
        "rule_id": rule_id,
        "rule_name": rule.name,
        "test_results": test_results
    }


def _item_matches_rule(item: dict, conditions: dict) -> bool:
    """检查商品是否匹配规则条件"""
    # 产品类型匹配
    if "product_types" in conditions:
        item_type = item.get("product_type", "unknown")
        if item_type not in conditions["product_types"]:
            return False
    
    # 数量匹配
    if "max_quantity" in conditions:
        if item.get("quantity", 1) > conditions["max_quantity"]:
            return False
    
    # 供应商匹配
    if "vendors" in conditions:
        vendor = item.get("vendor", "")
        if vendor not in conditions["vendors"]:
            return False
    
    # SKU匹配
    if "skus" in conditions:
        sku = item.get("sku", "")
        if sku not in conditions["skus"]:
            return False
    
    return True

#!/usr/bin/env python3
"""
修复 SCM 订单的 routing_metadata，将 default_fulfillment 改为 PRINTIFY
"""
import sys
from pathlib import Path
import json

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, update
from app.core.database import get_sync_db
from app.models.scm_order import SCMOrder


def fix_scm_order_routing_metadata(scm_order_number: str = None, tenant_id: int = 1, dry_run: bool = True):
    """
    修复 SCM 订单的 routing_metadata
    
    Args:
        scm_order_number: 要修复的订单编号（如果为 None，则修复所有 default_fulfillment 订单）
        tenant_id: 租户ID
        dry_run: 如果为 True，只显示将要修改的内容，不实际修改
    """
    print("=" * 60)
    if scm_order_number:
        print(f"修复 SCM 订单: {scm_order_number}")
    else:
        print("修复所有 target_system_type='default_fulfillment' 的 SCM 订单")
    print(f"租户ID: {tenant_id}")
    print(f"模式: {'预览模式（不会实际修改）' if dry_run else '实际修改模式'}")
    print("=" * 60)
    print()
    
    db = next(get_sync_db())
    try:
        # 构建查询
        if scm_order_number:
            # 修复特定订单
            result = db.execute(
                select(SCMOrder).where(
                    SCMOrder.scm_order_number == scm_order_number,
                    SCMOrder.tenant_id == tenant_id
                )
            )
            scm_orders = result.scalars().all()
        else:
            # 修复所有 default_fulfillment 订单
            result = db.execute(
                select(SCMOrder).where(
                    SCMOrder.tenant_id == tenant_id,
                    SCMOrder.routing_metadata.isnot(None)
                )
            )
            all_orders = result.scalars().all()
            # 过滤出 target_system_type 为 default_fulfillment 的订单
            scm_orders = [
                order for order in all_orders
                if order.routing_metadata
                and order.routing_metadata.get("target_system_type") == "default_fulfillment"
            ]
        
        if not scm_orders:
            print("ℹ️ 没有找到需要修复的订单")
            return
        
        print(f"找到 {len(scm_orders)} 个需要修复的订单:")
        print("-" * 60)
        
        for order in scm_orders:
            old_metadata = order.routing_metadata.copy() if order.routing_metadata else {}
            old_target_system_type = old_metadata.get("target_system_type", "N/A")
            
            print(f"订单: {order.scm_order_number or order.id}")
            print(f"  当前 target_system_type: {old_target_system_type}")
            
            if old_target_system_type == "default_fulfillment":
                # 更新 routing_metadata
                new_metadata = old_metadata.copy()
                new_metadata["target_system_type"] = "PRINTIFY"
                
                print(f"  新 target_system_type: PRINTIFY")
                
                if not dry_run:
                    # 实际更新数据库
                    db.execute(
                        update(SCMOrder)
                        .where(SCMOrder.id == order.id)
                        .values(routing_metadata=new_metadata)
                    )
                    print(f"  ✅ 已更新")
                else:
                    print(f"  [预览] 将更新为: {json.dumps(new_metadata, indent=2, ensure_ascii=False)}")
            else:
                print(f"  ⚠️  跳过（target_system_type 不是 'default_fulfillment'）")
            
            print()
        
        if not dry_run:
            db.commit()
            print("=" * 60)
            print(f"✅ 成功修复 {len(scm_orders)} 个订单")
        else:
            print("=" * 60)
            print("ℹ️  这是预览模式，没有实际修改数据库")
            print("   要实际执行修改，请运行: python scripts/fix_scm_order_routing_metadata.py [订单编号] [租户ID] --execute")
        
    except Exception as e:
        if not dry_run:
            db.rollback()
        print(f"❌ 修复失败: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        db.close()


if __name__ == "__main__":
    scm_order_number = None
    tenant_id = 1
    dry_run = True
    
    if len(sys.argv) > 1:
        scm_order_number = sys.argv[1]
    if len(sys.argv) > 2:
        tenant_id = int(sys.argv[2])
    if "--execute" in sys.argv:
        dry_run = False
    
    fix_scm_order_routing_metadata(scm_order_number, tenant_id, dry_run)

#!/usr/bin/env python3
"""
检查SCM订单为什么没有创建Printify订单
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import select, text
from app.core.database import get_sync_db
from app.models.scm_order import SCMOrder
from app.models.printify_order import PrintifyOrder


def check_scm_order(scm_order_number: str, tenant_id: int = 1):
    """检查SCM订单的Printify创建条件"""
    print("=" * 60)
    print(f"检查 SCM 订单: {scm_order_number}")
    print("=" * 60)
    print()
    
    db = next(get_sync_db())
    try:
        # 查询SCM订单
        result = db.execute(
            select(SCMOrder).where(
                SCMOrder.scm_order_number == scm_order_number,
                SCMOrder.tenant_id == tenant_id
            )
        )
        scm_order = result.scalar_one_or_none()
        
        if not scm_order:
            print(f"❌ 未找到订单: {scm_order_number}")
            return
        
        print(f"✅ 找到订单: ID={scm_order.id}, 编号={scm_order.scm_order_number}")
        print()
        
        # 检查条件1: routing_metadata 是否存在
        print("📋 条件检查:")
        print("-" * 60)
        
        if scm_order.routing_metadata is None:
            print("❌ routing_metadata 为 NULL")
            print("   原因: 订单创建时没有设置路由元数据")
            print("   解决: 需要检查订单路由逻辑，确保 routing_metadata 被正确设置")
            return
        else:
            print(f"✅ routing_metadata 存在: {scm_order.routing_metadata}")
        
        # 检查条件2: target_system_type 是否为 PRINTIFY
        target_system_type = scm_order.routing_metadata.get("target_system_type")
        if not target_system_type:
            print("❌ routing_metadata 中没有 target_system_type 字段")
            print("   原因: 订单路由时没有设置目标系统类型")
            print("   解决: 需要检查订单路由逻辑，确保 target_system_type 被正确设置")
            return
        elif target_system_type.upper() != "PRINTIFY":
            print(f"❌ target_system_type = '{target_system_type}' (不是 'PRINTIFY')")
            print(f"   原因: 订单被路由到了其他系统，而不是 Printify")
            print(f"   解决: 检查路由规则或手动设置 target_system_type 为 'PRINTIFY'")
            return
        else:
            print(f"✅ target_system_type = '{target_system_type}'")
        
        # 检查条件3: auto_created_printify_order 标志
        if scm_order.auto_created_printify_order:
            print(f"⚠️  auto_created_printify_order = True (已标记为已处理)")
            print("   原因: 订单已经被自动任务处理过")
            print("   解决: 如果需要重新处理，可以手动重置标志或使用 ignore_flags=True")
        else:
            print(f"✅ auto_created_printify_order = False (未处理)")
        
        # 检查条件4: 是否已经有 Printify 订单
        printify_result = db.execute(
            select(PrintifyOrder).where(
                PrintifyOrder.scm_order_id == scm_order.id,
                PrintifyOrder.tenant_id == tenant_id
            )
        )
        printify_order = printify_result.scalar_one_or_none()
        
        if printify_order:
            print(f"⚠️  已存在 Printify 订单: ID={printify_order.id}, external_order_id={printify_order.external_order_id}")
            print("   原因: 订单已经创建过 Printify 订单")
        else:
            print("✅ 没有对应的 Printify 订单")
        
        print()
        print("=" * 60)
        print("总结")
        print("=" * 60)
        
        # 判断是否符合创建条件
        can_create = (
            scm_order.routing_metadata is not None
            and target_system_type and target_system_type.upper() == "PRINTIFY"
            and not scm_order.auto_created_printify_order
            and printify_order is None
        )
        
        if can_create:
            print("✅ 订单符合创建 Printify 订单的条件")
            print("   建议: 检查自动化任务是否正常运行，或手动触发创建")
        else:
            print("❌ 订单不符合创建 Printify 订单的条件")
            print("   原因:")
            if scm_order.routing_metadata is None:
                print("   - routing_metadata 为 NULL")
            elif not target_system_type or target_system_type.upper() != "PRINTIFY":
                print(f"   - target_system_type = '{target_system_type}' (不是 'PRINTIFY')")
            if scm_order.auto_created_printify_order:
                print("   - auto_created_printify_order = True (已处理)")
            if printify_order:
                print("   - 已存在 Printify 订单")
        
        print()
        print("📊 完整订单信息:")
        print("-" * 60)
        print(f"ID: {scm_order.id}")
        print(f"订单编号: {scm_order.scm_order_number}")
        print(f"状态: {scm_order.status}")
        print(f"路由策略: {scm_order.routing_strategy}")
        print(f"routing_metadata: {scm_order.routing_metadata}")
        print(f"auto_created_printify_order: {scm_order.auto_created_printify_order}")
        print(f"printify_order_id: {scm_order.printify_order_id}")
        print(f"创建时间: {scm_order.created_at}")
        print(f"更新时间: {scm_order.updated_at}")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        print(traceback.format_exc())
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/check_scm_order_printify.py <scm_order_number> [tenant_id]")
        print("Example: python scripts/check_scm_order_printify.py SCM-2025-004 1")
        sys.exit(1)
    
    scm_order_number = sys.argv[1]
    tenant_id = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    
    check_scm_order(scm_order_number, tenant_id)

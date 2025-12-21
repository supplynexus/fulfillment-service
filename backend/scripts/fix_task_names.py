#!/usr/bin/env python3
"""
修复数据库中的任务名称
将错误的任务名称更新为正确的名称
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_sync_db
from app.models.automation_step import AutomationStep

# 任务名称映射（旧名称 -> 新名称）
TASK_NAME_FIXES = {
    "app.tasks.shopify_tasks.sync_shopify_orders_1min_task": "sync_shopify_orders_1min",
    "app.tasks.shopify_tasks.sync_shopify_products_1min_task": "sync_shopify_products_1min",
    # 修复：将旧的Shopify特定任务改为通用任务
    "app.tasks.order_automation_tasks.process_new_shopify_orders": "app.tasks.order_automation_tasks.process_new_orders_to_scm",
}

# 按 step_key 的任务名称映射（用于特定步骤）
STEP_KEY_TASK_MAPPING = {
    "create_scm_orders": "app.tasks.order_automation_tasks.process_new_orders_to_scm",
    "create_printify_orders_from_scm": "app.tasks.order_automation_tasks.create_printify_orders_from_scm",
}

def fix_task_names():
    """修复数据库中的任务名称"""
    print("🔍 开始修复数据库中的任务名称...")
    print()
    
    db = next(get_sync_db())
    try:
        updated_count = 0
        
        for step in db.query(AutomationStep).all():
            old_name = step.celery_task_name
            new_name = None
            
            # 优先检查 step_key 特定的映射
            if step.step_key in STEP_KEY_TASK_MAPPING:
                new_name = STEP_KEY_TASK_MAPPING[step.step_key]
            # 然后检查通用任务名映射
            elif old_name in TASK_NAME_FIXES:
                new_name = TASK_NAME_FIXES[old_name]
            
            if new_name and new_name != old_name:
                print(f"   🔧 更新步骤: {step.step_key}")
                print(f"      旧名称: {old_name}")
                print(f"      新名称: {new_name}")
                step.celery_task_name = new_name
                updated_count += 1
            elif old_name:
                # 检查是否已经是正确的格式
                if old_name.startswith("app.tasks.") and old_name.endswith("_task"):
                    # 尝试从完整路径提取任务名
                    parts = old_name.split(".")
                    if len(parts) >= 3:
                        task_module = parts[-2]
                        task_func = parts[-1]
                        # 如果函数名以 _task 结尾，可能需要去掉
                        if task_func.endswith("_task"):
                            potential_name = task_func[:-5]  # 去掉 _task
                            print(f"   ⚠️  步骤 {step.step_key} 的任务名称可能需要手动检查: {old_name}")
                            print(f"      建议名称可能是: {potential_name}")
        
        if updated_count > 0:
            db.commit()
            print()
            print(f"✅ 已更新 {updated_count} 个步骤的任务名称")
            print()
            print("💡 请重启 Celery Beat 以使更改生效")
        else:
            print()
            print("ℹ️  没有需要更新的任务名称")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 修复失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_task_names()


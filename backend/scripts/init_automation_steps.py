"""
初始化自动化步骤种子数据
运行此脚本以创建系统预定义的自动化步骤和手动按钮
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.core.database import get_sync_db
from app.models.automation_step import AutomationStep
from app.models.automation_manual_button import AutomationManualButton


# 系统预定义的自动化步骤
AUTOMATION_STEPS_SEED = [
    {
        "step_key": "sync_external_orders",
        "name": "外部订单同步到本地表",
        "description": "从外部系统（如Shopify）同步订单到本地shopify_orders表",
        "category": "order_sync",
        "required_external_systems": ["SHOPIFY"],
        "celery_task_name": "sync_shopify_orders_1min",  # 使用装饰器中定义的 name
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    {
        "step_key": "sync_to_core_orders",
        "name": "外部订单同步到核心订单表",
        "description": "从shopify_orders表同步订单到核心orders表（含地址验证）",
        "category": "order_sync",
        "required_external_systems": ["SHOPIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.sync_shopify_orders_to_core",
        "default_schedule": "*/30 * * * *",
        "default_enabled": False,  # 默认关闭，需要手动启用
        "is_manual_only": False,
    },
    {
        "step_key": "create_scm_orders",
        "name": "从核心订单创建SCM订单",
        "description": "从核心订单选择商品创建SCM订单",
        "category": "order_processing",
        "required_external_systems": ["SHOPIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.process_new_orders_to_scm",
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    {
        "step_key": "create_printify_orders_from_scm",
        "name": "从SCM订单创建Printify订单",
        "description": "从SCM订单批量创建Printify订单",
        "category": "order_processing",
        "required_external_systems": ["PRINTIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.create_printify_orders_from_scm",
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    {
        "step_key": "sync_printify_orders_to_local",
        "name": "Printify订单同步到本地表",
        "description": "从Printify API同步订单到本地printify_orders表",
        "category": "order_sync",
        "required_external_systems": ["PRINTIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.sync_printify_orders_to_local",
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    {
        "step_key": "sync_fulfillment_status",
        "name": "履约订单状态同步到SCM",
        "description": "从printify_orders本地表同步发货信息到SCM订单",
        "category": "status_sync",
        "required_external_systems": ["PRINTIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.sync_printify_orders_status",
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    {
        "step_key": "sync_to_external_fulfillment",
        "name": "SCM状态同步到外部履约（如Shopify）",
        "description": "将SCM订单状态同步回外部履约系统（如Shopify履约信息）",
        "category": "status_sync",
        "required_external_systems": ["SHOPIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.sync_scm_to_shopify_fulfillment",
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    {
        "step_key": "sync_shopify_fulfillment_to_local",
        "name": "Shopify发货信息同步到本地表",
        "description": "从Shopify API同步发货信息到shopify_orders本地表",
        "category": "status_sync",
        "required_external_systems": ["SHOPIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.sync_shopify_fulfillment_to_local",
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    {
        "step_key": "sync_shopify_local_fulfillment_to_core",
        "name": "Shopify本地发货信息同步到核心订单",
        "description": "从shopify_orders本地表同步发货信息到核心订单表",
        "category": "status_sync",
        "required_external_systems": ["SHOPIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.sync_shopify_local_fulfillment_to_core",
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
]

# 手动按钮配置
MANUAL_BUTTONS_SEED = [
    # sync_external_orders 的按钮
    {
        "step_key": "sync_external_orders",
        "button_key": "sync_to_core",
        "button_label": "同步到核心订单",
        "button_action": "/api/v1/shopify-orders/{id}/sync-to-core",
        "http_method": "POST",
        "is_recommended": True,
        "is_deprecated": False,
        "page_path": "/external-systems/shopify/synced-orders",
        "order": 1,
    },
    {
        "step_key": "sync_external_orders",
        "button_key": "delete_order",
        "button_label": "删除订单",
        "button_action": "/api/v1/shopify-orders/{id}",
        "http_method": "DELETE",
        "is_recommended": False,
        "is_deprecated": False,
        "page_path": "/external-systems/shopify/synced-orders",
        "order": 2,
    },
    # sync_to_core_orders 的按钮（与上面相同，因为这是同一个操作）
    {
        "step_key": "sync_to_core_orders",
        "button_key": "sync_to_core",
        "button_label": "同步到核心订单",
        "button_action": "/api/v1/shopify-orders/{id}/sync-to-core",
        "http_method": "POST",
        "is_recommended": True,
        "is_deprecated": False,
        "page_path": "/external-systems/shopify/synced-orders",
        "order": 1,
    },
    # create_scm_orders 的按钮
    {
        "step_key": "create_scm_orders",
        "button_key": "create_scm_order",
        "button_label": "创建核心SCM订单",
        "button_action": "/api/v1/scm-orders",
        "http_method": "POST",
        "is_recommended": True,
        "is_deprecated": False,
        "page_path": "/orders/[id]",
        "order": 1,
    },
    # create_printify_orders_from_scm 的按钮
    {
        "step_key": "create_printify_orders_from_scm",
        "button_key": "generate_printify_order",
        "button_label": "生成Printify订单",
        "button_action": "/api/v1/scm-orders/{id}/create-printify-order",
        "http_method": "POST",
        "is_recommended": True,
        "is_deprecated": False,
        "page_path": "/scm-orders/[id]",
        "order": 1,
    },
    # sync_fulfillment_status 的按钮（无手动按钮，仅自动化）
    # sync_to_external_fulfillment 的按钮（无手动按钮，仅自动化）
]


def init_automation_steps(db: Session):
    """初始化自动化步骤"""
    print("🔍 开始初始化自动化步骤...")
    
    for step_data in AUTOMATION_STEPS_SEED:
        existing = db.query(AutomationStep).filter(
            AutomationStep.step_key == step_data["step_key"]
        ).first()
        
        if existing:
            print(f"  ⚠️  步骤已存在，跳过: {step_data['step_key']}")
            continue
        
        step = AutomationStep(**step_data)
        db.add(step)
        print(f"  ✅ 创建步骤: {step_data['name']} ({step_data['step_key']})")
    
    db.commit()
    print("✅ 自动化步骤初始化完成")


def init_manual_buttons(db: Session):
    """初始化手动按钮"""
    print("🔍 开始初始化手动按钮...")
    
    for button_data in MANUAL_BUTTONS_SEED:
        existing = db.query(AutomationManualButton).filter(
            AutomationManualButton.step_key == button_data["step_key"],
            AutomationManualButton.button_key == button_data["button_key"]
        ).first()
        
        if existing:
            print(f"  ⚠️  按钮已存在，跳过: {button_data['step_key']}.{button_data['button_key']}")
            continue
        
        button = AutomationManualButton(**button_data)
        db.add(button)
        status = "（废弃）" if button_data.get("is_deprecated") else ""
        print(f"  ✅ 创建按钮: {button_data['button_label']} {status}")
    
    db.commit()
    print("✅ 手动按钮初始化完成")


def main():
    """主函数"""
    print("=" * 60)
    print("初始化自动化步骤和手动按钮")
    print("=" * 60)
    
    db = next(get_sync_db())
    try:
        init_automation_steps(db)
        print()
        init_manual_buttons(db)
        print()
        print("=" * 60)
        print("✅ 初始化完成！")
        print("=" * 60)
    except Exception as e:
        db.rollback()
        print(f"❌ 初始化失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()





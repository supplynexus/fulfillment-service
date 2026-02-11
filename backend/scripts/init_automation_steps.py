"""
初始化自动化步骤种子数据
运行此脚本以创建/更新系统预定义的自动化步骤和手动按钮。

运行方式（须在 backend 目录下并激活 venv）:
  cd backend && source .venv/bin/activate && python scripts/init_automation_steps.py
  # Windows PowerShell:
  cd backend; .\\.venv\\Scripts\\Activate.ps1; python scripts/init_automation_steps.py
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
# category: order_sync=订单同步, order_processing=订单处理, status_sync=状态同步, product_sync=商品同步
AUTOMATION_STEPS_SEED = [
    # ----- 订单同步 -----
    {
        "step_key": "sync_external_orders",
        "name": "Shopify 订单同步到本地表",
        "description": "从 Shopify 拉取订单到本地 shopify_orders 表，供后续同步到核心订单使用",
        "category": "order_sync",
        "required_external_systems": ["SHOPIFY"],
        "celery_task_name": "sync_shopify_orders_1min",
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    {
        "step_key": "sync_to_core_orders",
        "name": "外部订单同步到核心订单表",
        "description": "把 shopify_orders 里未同步的订单写入核心 orders 表，并做地址验证",
        "category": "order_sync",
        "required_external_systems": ["SHOPIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.sync_shopify_orders_to_core",
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    {
        "step_key": "sync_printify_orders_to_local",
        "name": "Printify 订单同步到本地表",
        "description": "从 Printify API 拉取订单到本地 printify_orders 表",
        "category": "order_sync",
        "required_external_systems": ["PRINTIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.sync_printify_orders_to_local",
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    # ----- 商品同步 -----
    {
        "step_key": "sync_printify_products_to_local",
        "name": "Printify 商品同步到本地（core）",
        "description": "从 Printify API 全量同步商品到 printify_products 与 external_products，供「Printify 映射」使用。默认每日 2 次。",
        "category": "product_sync",
        "required_external_systems": ["PRINTIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.sync_printify_products_to_local",
        "default_schedule": "0 0,12 * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    {
        "step_key": "auto_bind_printify_by_shopify",
        "name": "Printify–Shopify 商品自动绑定",
        "description": "按 Printify raw_data.external.id 与核心商品 Shopify 映射匹配，为「有 Shopify、无 Printify」的核心商品自动创建商品级映射。建议在「Printify 商品同步到本地」之后运行，如每日 2 次。",
        "category": "product_sync",
        "required_external_systems": ["PRINTIFY", "SHOPIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.auto_bind_printify_by_shopify",
        "default_schedule": "5 0,12 * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    # ----- 订单处理 -----
    {
        "step_key": "create_scm_orders",
        "name": "从核心订单创建 SCM 订单",
        "description": "把核心订单中的商品生成 SCM 订单，用于后续发 Printify 等",
        "category": "order_processing",
        "required_external_systems": ["SHOPIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.process_new_orders_to_scm",
        "default_schedule": "*/30 * * * *",
        "default_enabled": False,
        "is_manual_only": False,
    },
    {
        "step_key": "create_printify_orders_from_scm",
        "name": "从 SCM 订单创建 Printify 订单",
        "description": "根据 SCM 订单在 Printify 侧批量创建生产订单",
        "category": "order_processing",
        "required_external_systems": ["PRINTIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.create_printify_orders_from_scm",
        "default_schedule": "*/30 * * * *",
        "default_enabled": False,
        "is_manual_only": False,
    },
    {
        "step_key": "auto_create_scm_from_unbound_printify_orders",
        "name": "未绑定 Printify 订单自动创建 SCM",
        "description": "对未绑定 SCM 的 Printify 同步订单自动创建 SCM 订单并绑定，补全「Printify→SCM」流程",
        "category": "order_processing",
        "required_external_systems": ["PRINTIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.auto_create_scm_from_unbound_printify_orders",
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    # ----- 状态同步 -----
    {
        "step_key": "sync_fulfillment_status",
        "name": "履约订单状态同步到 SCM",
        "description": "把 printify_orders 的发货/物流状态回写到 SCM 订单",
        "category": "status_sync",
        "required_external_systems": ["PRINTIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.sync_printify_orders_status",
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    {
        "step_key": "sync_to_external_fulfillment",
        "name": "SCM 状态同步到外部履约（如 Shopify）",
        "description": "把 SCM 的发货状态同步回 Shopify 履约信息",
        "category": "status_sync",
        "required_external_systems": ["SHOPIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.sync_scm_to_shopify_fulfillment",
        "default_schedule": "*/30 * * * *",
        "default_enabled": False,
        "is_manual_only": False,
    },
    {
        "step_key": "sync_shopify_fulfillment_to_local",
        "name": "Shopify 发货信息同步到本地表",
        "description": "从 Shopify API 拉取履约/物流信息到 shopify_orders",
        "category": "status_sync",
        "required_external_systems": ["SHOPIFY"],
        "celery_task_name": "app.tasks.order_automation_tasks.sync_shopify_fulfillment_to_local",
        "default_schedule": "*/30 * * * *",
        "default_enabled": True,
        "is_manual_only": False,
    },
    {
        "step_key": "sync_shopify_local_fulfillment_to_core",
        "name": "Shopify 本地发货信息同步到核心订单",
        "description": "把 shopify_orders 的物流信息写入核心 orders 表",
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
        "button_action": "/api/v1/scm-orders/{hashid}/generate-printify",
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
    """初始化自动化步骤；已存在的步骤会更新 name/description/category/default_schedule 以保持与种子一致"""
    print("🔍 开始初始化自动化步骤...")

    for step_data in AUTOMATION_STEPS_SEED:
        existing = db.query(AutomationStep).filter(
            AutomationStep.step_key == step_data["step_key"]
        ).first()

        if existing:
            existing.name = step_data["name"]
            existing.description = step_data["description"]
            existing.category = step_data["category"]
            existing.default_schedule = step_data["default_schedule"]
            existing.celery_task_name = step_data["celery_task_name"]
            existing.required_external_systems = step_data.get("required_external_systems")
            print(f"  📝 更新步骤: {step_data['name']} ({step_data['step_key']})")
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





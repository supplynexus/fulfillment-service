#!/usr/bin/env python3
"""
迁移自动化步骤配置
将 create_fulfillment_orders 更新为 create_printify_orders_from_scm
并统一所有步骤的调度时间为每30分钟
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_sync_db
from app.models.automation_step import AutomationStep
from app.models.tenant_automation_config import TenantAutomationConfig
from app.models.automation_manual_button import AutomationManualButton
from sqlalchemy import text


def migrate_automation_steps():
    """迁移自动化步骤"""
    print("=" * 60)
    print("开始迁移自动化步骤配置")
    print("=" * 60)
    print()
    
    db = next(get_sync_db())
    try:
        # 1. 更新或创建 automation_steps
        print("📝 步骤1: 更新自动化步骤表...")
        
        # 需要创建/更新的步骤列表
        steps_to_create = [
            {
                "step_key": "create_printify_orders_from_scm",
                "name": "从SCM订单创建Printify订单",
                "description": "从SCM订单批量创建Printify订单",
                "category": "order_processing",
                "required_external_systems": ["PRINTIFY"],
                "celery_task_name": "app.tasks.order_automation_tasks.create_printify_orders_from_scm",
                "default_schedule": "*/30 * * * *",
                "default_enabled": True,
                "is_manual_only": False
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
                "is_manual_only": False
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
                "is_manual_only": False
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
                "is_manual_only": False
            },
        ]
        
        # 检查是否存在旧的步骤 create_fulfillment_orders
        old_step = db.query(AutomationStep).filter(
            AutomationStep.step_key == "create_fulfillment_orders"
        ).first()
        
        if old_step:
            print(f"   🔧 找到旧步骤: {old_step.step_key}")
            print(f"      更新为: create_printify_orders_from_scm")
            
            # 更新步骤
            old_step.step_key = "create_printify_orders_from_scm"
            old_step.name = "从SCM订单创建Printify订单"
            old_step.description = "从SCM订单批量创建Printify订单"
            old_step.celery_task_name = "app.tasks.order_automation_tasks.create_printify_orders_from_scm"
            old_step.default_schedule = "*/30 * * * *"
            
            print(f"   ✅ 步骤已更新")
        
        # 创建或更新所有新步骤
        for step_data in steps_to_create:
            existing_step = db.query(AutomationStep).filter(
                AutomationStep.step_key == step_data["step_key"]
            ).first()
            
            if existing_step:
                # 更新现有步骤
                for key, value in step_data.items():
                    if hasattr(existing_step, key):
                        setattr(existing_step, key, value)
                print(f"   🔧 更新步骤: {step_data['step_key']}")
            else:
                # 创建新步骤
                new_step = AutomationStep(**step_data)
                db.add(new_step)
                print(f"   ➕ 创建新步骤: {step_data['step_key']}")
        
        print(f"   ✅ 步骤处理完成")
        
        # 统一所有步骤的默认调度为每30分钟
        print()
        print("📝 统一所有步骤的默认调度为每30分钟...")
        steps_to_update = db.query(AutomationStep).filter(
            (AutomationStep.default_schedule != "*/30 * * * *") |
            (AutomationStep.default_schedule.is_(None))
        ).all()
        
        if steps_to_update:
            for step in steps_to_update:
                print(f"   🔧 更新步骤 {step.step_key} 的调度时间")
                step.default_schedule = "*/30 * * * *"
            print(f"   ✅ 已更新 {len(steps_to_update)} 个步骤")
        else:
            print(f"   ℹ️  所有步骤的调度时间已正确")
        
        db.commit()
        print()
        
        # 2. 更新 tenant_automation_config
        print("📝 步骤2: 更新租户自动化配置表...")
        configs_to_update = db.query(TenantAutomationConfig).filter(
            TenantAutomationConfig.step_key == "create_fulfillment_orders"
        ).all()
        
        if configs_to_update:
            for config in configs_to_update:
                print(f"   🔧 更新租户 {config.tenant_id} 的配置")
                config.step_key = "create_printify_orders_from_scm"
                # 统一调度时间为30分钟（1800秒）
                if config.schedule_seconds is None or config.schedule_seconds != 1800:
                    config.schedule_seconds = 1800
                    print(f"      设置调度时间为 1800 秒（30分钟）")
            print(f"   ✅ 已更新 {len(configs_to_update)} 个租户配置")
        else:
            print(f"   ℹ️  没有需要更新的租户配置")
        
        # 统一所有配置的调度时间为30分钟
        print()
        print("📝 统一所有租户配置的调度时间为30分钟...")
        all_configs_to_update = db.query(TenantAutomationConfig).filter(
            (TenantAutomationConfig.schedule_seconds.is_(None)) |
            (TenantAutomationConfig.schedule_seconds != 1800)
        ).all()
        
        if all_configs_to_update:
            for config in all_configs_to_update:
                if config.schedule_seconds != 1800:
                    print(f"   🔧 更新租户 {config.tenant_id} 的步骤 {config.step_key} 调度时间")
                    config.schedule_seconds = 1800
            print(f"   ✅ 已更新 {len(all_configs_to_update)} 个配置")
        else:
            print(f"   ℹ️  所有配置的调度时间已正确")
        
        db.commit()
        print()
        
        # 3. 更新 automation_manual_buttons
        print("📝 步骤3: 更新手动按钮表...")
        buttons_to_update = db.query(AutomationManualButton).filter(
            AutomationManualButton.step_key == "create_fulfillment_orders"
        ).all()
        
        if buttons_to_update:
            for button in buttons_to_update:
                print(f"   🔧 更新按钮: {button.button_key}")
                button.step_key = "create_printify_orders_from_scm"
            print(f"   ✅ 已更新 {len(buttons_to_update)} 个按钮")
        else:
            print(f"   ℹ️  没有需要更新的按钮")
        
        db.commit()
        print()
        
        # 4. 验证结果
        print("=" * 60)
        print("验证迁移结果")
        print("=" * 60)
        print()
        
        # 检查步骤
        print("📋 自动化步骤:")
        step_keys_to_check = [
            "sync_external_orders",
            "sync_to_core_orders",
            "create_scm_orders",
            "create_printify_orders_from_scm",
            "sync_printify_orders_to_local",
            "sync_fulfillment_status",
            "sync_to_external_fulfillment",
            "sync_shopify_fulfillment_to_local",
            "sync_shopify_local_fulfillment_to_core",
        ]
        steps = db.query(AutomationStep).filter(
            AutomationStep.step_key.in_(step_keys_to_check)
        ).all()
        for step in steps:
            print(f"   - {step.step_key}: {step.name}")
            print(f"     任务: {step.celery_task_name}")
            print(f"     调度: {step.default_schedule}")
        print()
        
        # 检查租户配置
        print("📋 租户配置:")
        configs = db.query(TenantAutomationConfig).filter(
            TenantAutomationConfig.step_key.in_(step_keys_to_check)
        ).all()
        if configs:
            for config in configs:
                print(f"   - 租户 {config.tenant_id}: {config.step_key}")
                print(f"     启用: {config.is_enabled}, 激活: {config.is_active}")
                print(f"     调度: {config.schedule_seconds} 秒")
        else:
            print("   ℹ️  没有相关租户配置")
        print()
        
        # 检查按钮
        print("📋 手动按钮:")
        buttons = db.query(AutomationManualButton).filter(
            AutomationManualButton.step_key.in_(["create_printify_orders_from_scm", "create_fulfillment_orders"])
        ).all()
        if buttons:
            for button in buttons:
                print(f"   - {button.step_key}.{button.button_key}: {button.button_label}")
        else:
            print("   ℹ️  没有相关按钮")
        print()
        
        print("=" * 60)
        print("✅ 迁移完成！")
        print("=" * 60)
        print()
        print("💡 请重启 Celery Beat 服务以使更改生效")
        print()
        
    except Exception as e:
        db.rollback()
        print(f"❌ 迁移失败: {str(e)}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    migrate_automation_steps()

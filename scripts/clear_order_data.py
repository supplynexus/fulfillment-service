#!/usr/bin/env python3
"""
清理订单数据脚本
用于清空所有订单相关数据，重新测试订单自动化流程
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.core.database import get_sync_db
from app.core.logging import get_logger

logger = get_logger(__name__)


def clear_order_data():
    """清理所有订单相关数据"""
    try:
        logger.info("🧹 开始清理订单数据...")

        # 获取数据库连接
        db = next(get_sync_db())

        # 清理顺序：先清理依赖表，再清理主表
        tables_to_clear = [
            "routing_status",  # 路由状态表
            "scm_orders",  # SCM订单表
            "orders",  # 订单表
        ]

        for table in tables_to_clear:
            try:
                # 检查表是否存在
                result = db.execute(
                    text(
                        f"""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_schema = 'public' 
                        AND table_name = '{table}'
                    );
                """
                    )
                )

                table_exists = result.scalar()

                if table_exists:
                    # 清空表数据
                    db.execute(text(f"DELETE FROM {table};"))
                    logger.info(f"✅ 已清空表: {table}")
                else:
                    logger.warning(f"⚠️ 表不存在: {table}")

            except Exception as e:
                logger.error(f"❌ 清空表 {table} 失败: {str(e)}")
                continue

        # 重置自增ID序列
        try:
            # 重置orders表的ID序列
            db.execute(text("SELECT setval('orders_id_seq', 1, false);"))
            logger.info("✅ 已重置 orders 表ID序列")
        except Exception as e:
            logger.warning(f"⚠️ 重置 orders 表ID序列失败: {str(e)}")

        try:
            # 重置scm_orders表的ID序列
            db.execute(text("SELECT setval('scm_orders_id_seq', 1, false);"))
            logger.info("✅ 已重置 scm_orders 表ID序列")
        except Exception as e:
            logger.warning(f"⚠️ 重置 scm_orders 表ID序列失败: {str(e)}")

        try:
            # 重置routing_status表的ID序列
            db.execute(text("SELECT setval('routing_status_id_seq', 1, false);"))
            logger.info("✅ 已重置 routing_status 表ID序列")
        except Exception as e:
            logger.warning(f"⚠️ 重置 routing_status 表ID序列失败: {str(e)}")

        # 提交事务
        db.commit()

        logger.info("🎉 订单数据清理完成！")
        logger.info("📋 已清理的表:")
        for table in tables_to_clear:
            logger.info(f"  - {table}")

        return True

    except Exception as e:
        logger.error(f"❌ 清理订单数据失败: {str(e)}")
        if "db" in locals():
            db.rollback()
        return False

    finally:
        if "db" in locals():
            db.close()


def verify_cleanup():
    """验证清理结果"""
    try:
        logger.info("🔍 验证清理结果...")

        db = next(get_sync_db())

        # 检查各表记录数
        tables_to_check = ["orders", "scm_orders", "routing_status"]

        for table in tables_to_check:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table};"))
                count = result.scalar()
                logger.info(f"📊 {table} 表记录数: {count}")
            except Exception as e:
                logger.warning(f"⚠️ 检查表 {table} 失败: {str(e)}")

        db.close()

    except Exception as e:
        logger.error(f"❌ 验证清理结果失败: {str(e)}")


if __name__ == "__main__":
    print("🧹 订单数据清理工具")
    print("=" * 50)

    # 确认操作
    confirm = input("⚠️ 此操作将删除所有订单数据，是否继续？(y/N): ")
    if confirm.lower() != "y":
        print("❌ 操作已取消")
        sys.exit(0)

    # 执行清理
    success = clear_order_data()

    if success:
        # 验证清理结果
        verify_cleanup()
        print("\n✅ 订单数据清理完成！")
        print("🚀 现在可以重新测试订单自动化流程了")
    else:
        print("\n❌ 订单数据清理失败！")
        sys.exit(1)
